#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bench_coverage.py —— 用第三方日语词频表当裁判，测谁漏得多
=================================================================
思路：拿一份**双方都没参与构建**的日语高频词表，
分别检查本项目和对照词库能覆盖多少。这才是覆盖面的客观测试，
而不是比较「谁条目多」——条目多也可能是把语料切碎的噪音。

裁判数据：hermitdave/FrequencyWords 2016 ja_50k（MIT，字幕/口语语料），
以及 _compare 里的 jmnedict（若有）。

用法:
    python3 tools/bench_coverage.py
"""
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from compare_dicts import load_ours, load_rime_pairs  # noqa: E402
import gen_ja_dict as g  # noqa: E402


def load_freq_words(path, limit):
    """词频表 -> [(词, 排名)]，跳过纯假名的碎片与单字"""
    out, rank = [], 0
    for line in open(path, encoding='utf-8', errors='replace'):
        parts = line.split()
        if len(parts) != 2 or not parts[1].isdigit():
            continue
        rank += 1
        w = parts[0]
        if len(w) < 2:            # 单字多半是切碎的音节
            continue
        if not re.search(r'[一-鿿ァ-ヺ]', w):   # 纯平假名多为活用碎片
            continue
        out.append((w, rank))
        if len(out) >= limit:
            break
    return out


def main():
    ours = load_ours(os.path.join(ROOT, 'ja_romaji.dict.yaml'))
    ours_surf = Counter()
    for s, _r in ours:
        ours_surf[s] += 1

    other_surf = Counter()
    for n in ('gkovacs.mozc.dict.yaml', 'gkovacs.jmdict.dict.yaml'):
        p = os.path.join(ROOT, '_compare', n)
        if os.path.exists(p):
            for s, _r in load_rime_pairs(p):
                other_surf[s] += 1

    freq_path = os.path.join(ROOT, '_cache', 'ja_50k.txt')
    if not os.path.exists(freq_path):
        print('缺少词频表 _cache/ja_50k.txt')
        return 1
    words = load_freq_words(freq_path, 30000)
    print(f'裁判词表: {len(words):,} 个高频词（已剔除单字与纯平假名碎片）')
    print(f'本项目表记 {len(ours_surf):,} / 对照表记 {len(other_surf):,}\n')

    # 覆盖统计
    buckets = [(0, 1000), (1000, 3000), (3000, 10000), (10000, 30000)]
    print(f'{"词频区间":<16}{"词数":>7}{"本项目覆盖":>12}{"对照覆盖":>12}{"仅本项目":>10}{"仅对照":>9}')
    tot = Counter()
    miss_ours, miss_other, only_ours = [], [], []
    for lo, hi in buckets:
        seg = [(w, r) for w, r in words if lo < r <= hi]
        a = sum(1 for w, _ in seg if w in ours_surf)
        b = sum(1 for w, _ in seg if w in other_surf)
        oo = sum(1 for w, _ in seg if w in ours_surf and w not in other_surf)
        ob = sum(1 for w, _ in seg if w not in ours_surf and w in other_surf)
        n = len(seg) or 1
        print(f'{lo+1:>6}-{hi:<9}{len(seg):>7}{a:>8} ({a/n*100:4.1f}%){b:>8} ({b/n*100:4.1f}%){oo:>10}{ob:>9}')
        tot['a'] += a; tot['b'] += b; tot['oo'] += oo; tot['ob'] += ob
        for w, r in seg:
            if w not in ours_surf and w in other_surf: miss_ours.append((w, r))
            if w in ours_surf and w not in other_surf: only_ours.append((w, r))
    n = len(words)
    print(f'{"合计":<16}{n:>7}{tot["a"]:>8} ({tot["a"]/n*100:4.1f}%){tot["b"]:>8} ({tot["b"]/n*100:4.1f}%)'
          f'{tot["oo"]:>10}{tot["ob"]:>9}')

    print()
    print('=== 对照有、本项目没有的高频词（按词频排序，前 50）—— 这些才是真缺口 ===')
    miss_ours.sort(key=lambda x: x[1])
    for w, r in miss_ours[:50]:
        print(f'    #{r:<6} {w}')

    print()
    print('=== 本项目有、对照没有的高频词（前 25）—— 说明对照也有漏 ===')
    only_ours.sort(key=lambda x: x[1])
    for w, r in only_ours[:25]:
        print(f'    #{r:<6} {w}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
