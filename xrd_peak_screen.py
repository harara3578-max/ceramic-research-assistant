#!/usr/bin/env python3
"""Simple local peak screening. NOT phase identification / Rietveld / indexing."""
import argparse
import csv
import math
from pathlib import Path

MAX_SIZE = 12 * 1024 * 1024


def load_data(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_SIZE:
        raise ValueError('ファイルが存在しないか、12MB上限を超えています')
    with path.open('r', encoding='utf-8-sig', newline='') as file:
        head = file.readline()
        file.seek(0)
        delim = '\t' if ('\t' in head and ',' not in head) else ','
        reader = csv.reader(file, delimiter=delim)
        arr = []
        for line, row in enumerate(reader, 1):
            if not row or not any(s.strip() for s in row):
                continue
            if len(row) < 2:
                raise ValueError(f'{line}行目に2列必要')
            try:
                x, y = float(row[0]), float(row[1])
            except ValueError:
                if line == 1:
                    continue
                raise ValueError(f'{line}行目に数値以外があります')
            if not (math.isfinite(x) and math.isfinite(y) and 0 < x < 180 and y >= 0):
                raise ValueError(f'{line}行目に不正な角度または強度があります')
            if arr and x <= arr[-1][0]:
                raise ValueError('2thetaは厳密に昇順である必要があります')
            arr.append((x, y))
            if len(arr) > 200000:
                raise ValueError('200000点を超えています')
    if len(arr) < 7:
        raise ValueError('7点以上必要')
    return arr


def screen(arr, min_prominence_fraction=0.05, min_separation_deg=0.25, window=9):
    if window < 3 or window % 2 == 0:
        raise ValueError('windowは3以上の奇数')
    raw = [y for _, y in arr]
    radius = window // 2
    smooth = [sum(raw[max(0, i-radius):min(len(raw), i+radius+1)]) /
              len(raw[max(0, i-radius):min(len(raw), i+radius+1)])
              for i in range(len(raw))]
    dynamic = max(smooth) - min(smooth)
    if dynamic == 0:
        return []
    minima = min(smooth)
    threshold = dynamic * min_prominence_fraction
    candidates = []
    for i in range(1, len(smooth)-1):
        if smooth[i] <= smooth[i-1] or smooth[i] < smooth[i+1]:
            continue
        left = max(0, i-3 * window)
        right = min(len(smooth), i+3 * window+1)
        prominence = smooth[i] - max(min(smooth[left:i+1]), min(smooth[i:right]))
        if prominence >= threshold and smooth[i] >= minima + threshold:
            candidates.append({'two_theta_deg': round(arr[i][0], 5),
                               'smoothed_intensity': round(smooth[i], 4),
                               'local_prominence_approx': round(prominence, 4)})
    candidates.sort(key=lambda p: p['smoothed_intensity'], reverse=True)
    kept = []
    for candidate in candidates:
        if all(abs(p['two_theta_deg'] - candidate['two_theta_deg']) >= min_separation_deg for p in kept):
            kept.append(candidate)
    return sorted(kept, key=lambda p: p['two_theta_deg'])


def main():
    p = argparse.ArgumentParser(description='オフライン簡易XRDピーク検出（相同定ではありません）')
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--prominence-fraction', type=float, default=0.05)
    p.add_argument('--min-separation-deg', type=float, default=0.25)
    p.add_argument('--window', type=int, default=9)
    a = p.parse_args()
    src, out = Path(a.input).resolve(), Path(a.output).resolve()
    if src == out:
        p.error('原本を上書きできません')
    if not (0 < a.prominence_fraction <= 1) or a.min_separation_deg <= 0:
        p.error('閾値の指定が不正です')
    try:
        peaks = screen(load_data(src), a.prominence_fraction, a.min_separation_deg, a.window)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open('w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=('two_theta_deg', 'smoothed_intensity', 'local_prominence_approx'))
            writer.writeheader()
            writer.writerows(peaks)
        print(f'OK: {len(peaks)}個のピーク候補 -> {out}')
        print('注: 予備ピーク抽出のみ。波長補正、相同定、指数付け、精密化は行いません。')
    except (OSError, ValueError, csv.Error) as exc:
        p.exit(2, f'ERROR: {exc}\n')


if __name__ == '__main__':
    main()
