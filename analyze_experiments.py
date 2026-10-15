#!/usr/bin/env python3
"""Offline descriptive summaries of electronic ceramics CSV/TSV. No external packages."""
import argparse
import csv
import datetime
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

METRICS = {
    'relative_density_pct': '%', 'grain_size_um': 'µm',
    'epsilon_r': '1', 'tan_delta': '1',
    'resistivity_ohm_cm': 'Ω·cm', 'd33_pc_n': 'pC/N',
    'lattice_a_angstrom': 'Å', 'lattice_c_angstrom': 'Å',
}
FACTORS = ('dopant_mol_pct', 'firing_temp_c', 'hold_h', 'atmosphere')
EXPECTED = ('sample_id', 'material_system', 'measurement_freq_hz', 'measurement_temp_c')
MAX_SIZE = 10 * 1024 * 1024
MAX_ROWS = 100000


def read_rows(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_SIZE:
        raise ValueError('入力が存在しないか、10MBの上限を超えています')
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        sample = f.read(4096)
        f.seek(0)
        delimiter = '\t' if path.suffix.lower() == '.tsv' else ','
        if '\t' in sample and sample.count('\t') > sample.count(','):
            delimiter = '\t'
        reader = csv.DictReader(f, delimiter=delimiter)
        if not reader.fieldnames or 'sample_id' not in reader.fieldnames:
            raise ValueError('sample_id列が必要です')
        if len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError('列名が重複しています')
        rows = []
        for idx, row in enumerate(reader, 2):
            if idx > MAX_ROWS + 1:
                raise ValueError('100000行を超えています')
            if None in row:
                raise ValueError(f'{idx}行目に余分な区切りがあります')
            if not (row.get('sample_id') or '').strip():
                raise ValueError(f'{idx}行目のsample_idが空です')
            rows.append({k: (v or '').strip() for k, v in row.items()})
    if not rows:
        raise ValueError('データ行がありません')
    return rows, list(reader.fieldnames)


def number(raw):
    if not raw:
        return None
    try:
        x = float(raw)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def stats(values):
    if not values:
        return None
    s = {'n_rows': len(values), 'mean': round(statistics.mean(values), 8),
         'median': round(statistics.median(values), 8),
         'min': min(values), 'max': max(values)}
    if len(values) > 1:
        s['sample_sd'] = round(statistics.stdev(values), 8)
    return s


def pearson(pairs):
    xs, ys = zip(*pairs)
    if len(pairs) < 5 or len(set(xs)) < 3 or len(set(ys)) < 3:
        return None
    xm, ym = statistics.mean(xs), statistics.mean(ys)
    xx = sum((x - xm) ** 2 for x in xs)
    yy = sum((y - ym) ** 2 for y in ys)
    if xx <= 0 or yy <= 0:
        return None
    return round(sum((x - xm) * (y - ym) for x, y in pairs) / math.sqrt(xx * yy), 5)


def analyze(rows, fields):
    warnings = []
    for field in EXPECTED:
        if field not in fields:
            warnings.append(f'比較可能性確認用の列がありません: {field}')
    counts = Counter(r['sample_id'] for r in rows)
    if any(n > 1 for n in counts.values()):
        warnings.append('sample_idが重複: 同一試料の測定行は独立試料数として数えないでください')
    if 'batch_id' not in fields:
        warnings.append('batch_idがありません: 製造ロットによる交絡の確認が困難です')
    if 'material_system' in fields and len(set(r['material_system'] for r in rows)) > 1:
        warnings.append('異なる材料系が混在: 全体平均と全体相関の解釈に注意')
    for condition in ('measurement_freq_hz', 'measurement_temp_c'):
        if condition in fields:
            vals = set(r[condition] for r in rows if r[condition])
            if len(vals) > 1:
                warnings.append(f'{condition}が試料間で異なります: 電気特性をそのまま比較しないでください')
    metrics = {}
    for m, unit in METRICS.items():
        if m not in fields:
            continue
        raw_values = [r[m] for r in rows]
        invalid = sum(bool(s) and number(s) is None for s in raw_values)
        if invalid:
            warnings.append(f'{m}に数値として読めない値が{invalid}件あります')
        vals = [number(s) for s in raw_values]
        metrics[m] = {'unit': unit, 'missing_or_invalid_rows': sum(v is None for v in vals),
                      'overall': stats([v for v in vals if v is not None])}
    factors = {}
    for factor in FACTORS:
        if factor not in fields:
            continue
        groups = defaultdict(list)
        for r in rows:
            label = r[factor] or '(missing)'
            groups[label].append(r)
        per_group = {}
        for label, subset in sorted(groups.items(), key=lambda x: x[0]):
            per_group[label] = {'n_rows': len(subset), 'n_unique_sample_ids': len({r['sample_id'] for r in subset}),
                                'metrics': {m: stats([n for r in subset if (n := number(r[m])) is not None])
                                            for m in metrics}}
        factors[factor] = per_group
    associations = []
    for factor in ('dopant_mol_pct', 'firing_temp_c', 'hold_h'):
        if factor not in fields:
            continue
        for metric in metrics:
            pairs = [(a, b) for r in rows if (a := number(r[factor])) is not None
                     and (b := number(r[metric])) is not None]
            p = pearson(pairs)
            if p is not None and len({r['sample_id'] for r in rows}) == len(rows):
                associations.append({'factor': factor, 'metric': metric, 'pearson_r_descriptive': p,
                                     'n_rows': len(pairs), 'caution': '交絡未調整・探索的相関。因果・有意差を意味しない'})
    if len(rows) < 6:
        warnings.append('少数行: 記述統計の代表性が低いため統計的結論を出さない')
    return {
        'analysis_type': 'descriptive_only', 'n_rows': len(rows),
        'n_unique_sample_ids': len(counts), 'n_batches': len({r.get('batch_id', '') for r in rows if r.get('batch_id')}),
        'input_columns': fields, 'warnings': warnings, 'metrics': metrics,
        'factor_groups': factors, 'associations_exploratory': associations,
        'interpretation_guardrail': '統計的有意差、因果関係、機構をこのCLIは判定しない。測定条件を揃えた研究者の確認が必要。',
    }


def markdown(result, source):
    out = [f'# 実験データの一次解析（{source}）', '',
           f"- データ行数: {result['n_rows']}",
           f"- 異なるsample_id数: {result['n_unique_sample_ids']}",
           f"- ロット数（記録あり）: {result['n_batches']}",
           '', '## データ品質上の注意']
    out += [f'- {w}' for w in result['warnings']] or ['- 明確な警告なし（妥当性の証明ではない）']
    out += ['', '## 記述統計（全体・比較条件の混在に注意）',
            '| 特性 | 単位 | 有効行数 | 平均 | 標本SD |', '|---|---|---:|---:|---:|']
    for metric, entry in result['metrics'].items():
        s = entry['overall'] or {}
        out.append(f"| {metric} | {entry['unit']} | {s.get('n_rows', 0)} | {s.get('mean', '—')} | {s.get('sample_sd', '—')} |")
    out.extend(['', '## 組成・条件別の概観', ''])
    for factor, groups in result['factor_groups'].items():
        out.append(f'### {factor}')
        for level, value in groups.items():
            out.append(f"- {level}: {value['n_rows']}行、独立sample_id {value['n_unique_sample_ids']}個")
            for metric, s in value['metrics'].items():
                if s:
                    out.append(f"  - {metric}: 平均{s['mean']}（有効行{s['n_rows']}）")
    out += ['', '## 注意', result['interpretation_guardrail'], '']
    return '\n'.join(out)


def main():
    parser = argparse.ArgumentParser(description='CSV/TSVのオフライン記述統計')
    parser.add_argument('--input', required=True)
    parser.add_argument('--out-dir', required=True)
    a = parser.parse_args()
    src, out = Path(a.input).resolve(), Path(a.out_dir).resolve()
    if src == out or src == out / src.name or out.is_relative_to(src):
        parser.error('原本を出力先に指定できません')
    try:
        rows, fields = read_rows(src)
        result = analyze(rows, fields)
        result['input_file'] = src.name
        result['generated_at_local'] = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
        out.mkdir(parents=True, exist_ok=True)
        (out / 'eda_summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        (out / 'eda_summary.md').write_text(markdown(result, src.name), encoding='utf-8')
        print(f'OK: {out / "eda_summary.json"} / eda_summary.md')
        for warning in result['warnings']:
            print('注意:', warning)
    except (OSError, ValueError, csv.Error) as exc:
        parser.exit(2, f'ERROR: {exc}\n')


if __name__ == '__main__':
    main()
