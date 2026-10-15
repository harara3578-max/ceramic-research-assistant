#!/usr/bin/env python3
"""Validate structured hypothesis records. Scientific validity is NOT evaluated."""
import argparse
import json
from pathlib import Path

H_STRING = ('id', 'claim', 'mechanism', 'missing_evidence', 'distinguishing_prediction',
            'falsification_condition', 'proposed_test', 'limitations')
H_ARRAY = ('supporting_observation_ids', 'contradicting_observation_ids', 'alternative_explanations')


def validate(record):
    issues = []
    if not isinstance(record, dict):
        return ['最上位はJSONオブジェクトが必要']
    if not isinstance(record.get('study_id'), str) or not record['study_id'].strip():
        issues.append('study_idがありません')
    obs = record.get('observations')
    hyp = record.get('hypotheses')
    if not isinstance(obs, list) or not obs:
        issues.append('observationsは1件以上の配列が必要')
        obs = []
    if not isinstance(hyp, list) or not hyp:
        issues.append('hypothesesは1件以上の配列が必要')
        hyp = []
    obs_ids = set()
    for i, o in enumerate(obs):
        if not isinstance(o, dict):
            issues.append(f'observations[{i}]はオブジェクトが必要')
            continue
        for k in ('id', 'statement', 'source'):
            if not isinstance(o.get(k), str) or not o[k].strip():
                issues.append(f'observations[{i}].{k}が空欄')
        if not isinstance(o.get('sample_ids'), list) or not o['sample_ids'] or not all(isinstance(s, str) and s.strip() for s in o['sample_ids']):
            issues.append(f'observations[{i}].sample_idsが不正')
        if isinstance(o.get('id'), str):
            if o['id'] in obs_ids:
                issues.append(f'観察IDの重複: {o["id"]}')
            obs_ids.add(o['id'])
    hyp_ids = set()
    for i, h in enumerate(hyp):
        if not isinstance(h, dict):
            issues.append(f'hypotheses[{i}]はオブジェクトが必要')
            continue
        for k in H_STRING:
            if not isinstance(h.get(k), str) or not h[k].strip():
                issues.append(f'hypotheses[{i}].{k}が空欄')
        for k in H_ARRAY:
            v = h.get(k)
            if not isinstance(v, list) or (k == 'alternative_explanations' and not v) or not all(isinstance(s, str) and s.strip() for s in v):
                issues.append(f'hypotheses[{i}].{k}が不正')
        if isinstance(h.get('id'), str):
            if h['id'] in hyp_ids:
                issues.append(f'仮説IDの重複: {h["id"]}')
            hyp_ids.add(h['id'])
        for k in ('supporting_observation_ids', 'contradicting_observation_ids'):
            if isinstance(h.get(k), list):
                for val in h[k]:
                    if isinstance(val, str) and val not in obs_ids:
                        issues.append(f'hypotheses[{i}]に未知の観察ID: {val}')
    if not isinstance(record.get('overall_limitations'), str) or not record['overall_limitations'].strip():
        issues.append('overall_limitationsが空欄')
    if len(hyp) < 3:
        issues.append('警告: 競合仮説は原則3つ以上を推奨（少数でも科学的に不適切とは限らない）')
    return issues


def main():
    parser = argparse.ArgumentParser(description='仮説レコードの形式監査（科学的真偽の検証ではない）')
    parser.add_argument('--input', required=True)
    a = parser.parse_args()
    try:
        source = Path(a.input)
        if source.stat().st_size > 5 * 1024 * 1024:
            raise ValueError('入力は5MB以下にしてください')
        record = json.loads(source.read_text(encoding='utf-8-sig'))
        errors = validate(record)
        if errors:
            for item in errors:
                print('CHECK:', item)
            parser.exit(1, f'FAIL: {len(errors)}件の確認事項があります\n')
        print(f'PASS: {len(record["observations"])}観察、{len(record["hypotheses"])}仮説の必須形式を確認（内容の正しさは未検証）')
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(2, f'ERROR: {exc}\n')


if __name__ == '__main__':
    main()
