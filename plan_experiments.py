#!/usr/bin/env python3
"""Local small factorial candidate list; never interfaces with lab equipment."""
import argparse
import csv
import itertools
import json
import random
from pathlib import Path


def plan(spec):
    if not isinstance(spec, dict):
        raise ValueError('JSONオブジェクトが必要')
    factors = spec.get('factors')
    if not isinstance(factors, dict) or not 1 <= len(factors) <= 5:
        raise ValueError('factorsは1〜5種類の因子を指定')
    names = list(factors)
    if any(not isinstance(k, str) or not k.strip() or k in ('run', 'replicate', 'run_id') for k in names):
        raise ValueError('因子名が不正')
    levels = []
    for name, values in factors.items():
        if not isinstance(values, list) or not 2 <= len(values) <= 8 or any(isinstance(v, (dict, list)) or v is None for v in values):
            raise ValueError(f'{name}: 2〜8個の単純な水準が必要')
        if len({str(v) for v in values}) != len(values):
            raise ValueError(f'{name}: 水準が重複')
        levels.append(values)
    replicates = spec.get('independent_replicates', 2)
    seed = spec.get('seed', 17)
    if type(replicates) is not int or not 1 <= replicates <= 8:
        raise ValueError('independent_replicatesは1〜8の整数')
    if type(seed) is not int:
        raise ValueError('seedは整数')
    if not spec.get('human_approval_required', False):
        raise ValueError('human_approval_required: true が必要')
    products = list(itertools.product(*levels))
    if len(products) * replicates > 150:
        raise ValueError('150実験を超える設計は禁止')
    runs = []
    for replicate in range(1, replicates+1):
        for combo in products:
            row = {'replicate': replicate}
            row.update(zip(names, combo))
            runs.append(row)
    random.Random(seed).shuffle(runs)
    for idx, row in enumerate(runs, 1):
        row['run'] = idx
        row['run_id'] = f'EXP{idx:03}'
    return runs, ['run', 'run_id', 'replicate', *names]


def main():
    p = argparse.ArgumentParser(description='全因子試験候補を作成（実験は実行しません）')
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    src, out = Path(a.input).resolve(), Path(a.output).resolve()
    if src == out:
        p.error('原本を上書きできません')
    try:
        if src.stat().st_size > 100000:
            raise ValueError('設計JSONが100KBを超えています')
        spec = json.loads(src.read_text(encoding='utf-8-sig'))
        runs, fields = plan(spec)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open('w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(runs)
        print(f'OK: {len(runs)}実験候補 -> {out} （研究者の承認が必要）')
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        p.exit(2, f'ERROR: {exc}\n')


if __name__ == '__main__':
    main()
