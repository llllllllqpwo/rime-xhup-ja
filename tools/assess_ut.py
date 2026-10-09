#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
assess_ut.py —— 评估 Mozc UT 系辞书能带来多少真实增益
=========================================================
回答两个问题：
  1. 这些辞书里有多少是「词频表前 N 名」里我们缺的词（= 真增益）
  2. 有多少是我们已有的（= 纯冗余，加进去只是臃肿）

对象: _ut/*.txt.bz2（Mozc 格式: 读音 lid rid cost 表记）
对照: _cache/ja_50k.txt 词频表（真实文本形态）
"""
import bz2
import os
import re
import sys
from collections import Counter

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import gen_ja_dict as g  # noqa: E402

KATA_RE = re.compile(r'[ァ-ヺー]')


def load_ours():
    surf, pairs = set(), set()
    started = False
    for line in open(os.path.join(ROOT, 'ja_romaji.dict.yaml'), encoding='utf-8'):
        line = line.rstrip('\n')
        if line == '...':
            started = True
            continue
        if not started or not line:
            continue
        p = line.split('\t')
        if len(p) < 3:
            continue
        surf.add(p[0])
        pairs.add((p[0], p[1].replace(' ', '')))
    return surf, pairs


def to_kata(s):
    out = []
    for c in s:
        o = ord(c)
        if 0x3041 <= o <= 0x3096:
            out.append(chr(o + 0x60))
        else:
            out.append(c)
    return ''.join(out)


def main():
    ours_surf, _ = load_ours()
    print(f'本项目词典表记: {len(ours_surf):,}')

    freq = []
    for line in open(os.path.join(ROOT, '_cache', 'ja_50k.txt'), encoding='utf-8'):
        parts = line.split()
        if len(parts) == 2 and parts[1].isdigit():
            freq.append(parts[0])
    for N in (3000, 10000, 30000):
        pass

    d = os.path.join(ROOT, '_ut')
    files = sorted(f for f in os.listdir(d) if f.endswith('.txt.bz2')) if os.path.isdir(d) else []
    if not files:
        print('_ut 下没有 .txt.bz2，先跑抓取')
        return 1

    for f in files:
        raw = bz2.decompress(open(os.path.join(d, f), 'rb').read()).decode('utf-8', errors='replace')
        rows = []
        bad_reading = 0
        for line in raw.split('\n'):
            if not line.strip():
                continue
            p = line.split('\t')
            if len(p) < 5:
                continue
            reading, surface = p[0], p[4]
            if not reading or not surface:
                continue
            # 读音必须是纯假名，且能转码
            if not g.romaji_code(reading):
                bad_reading += 1
                continue
            if len(surface) > 8 or not re.fullmatch(r'[ぁ-ゖァ-ヺー一-鿿々〆ヶ〇]+', surface):
                continue
            rows.append((reading, surface))

        new_surf = [s for _, s in rows if s not in ours_surf]
        print()
        print(f'===== {f} =====')
        print(f'  条目 {len(rows):,}（读音无法转码跳过 {bad_reading:,}）')
        print(f'  表记我们已有: {len(rows) - len(new_surf):,}')
        print(f'  表记我们没有: {len(new_surf):,}')
        newset = set(new_surf)
        for N in (3000, 10000, 30000, 50000):
            top = set(freq[:N])
            hit = newset & top
            total_top = len(top)
            ours_top = len(top & ours_surf)
            print(f'    词频前 {N:>5}: 我们已有 {ours_top:>5} 条，UT 可补 {len(hit):>4} 条'
                  f'  (补后覆盖 {ours_top + len(hit)}/{total_top} = {(ours_top + len(hit))/max(1,total_top)*100:.1f}%)')
        # 样例
        top30 = set(freq[:30000])
        samp = sorted(newset & top30)
        print(f'    可补样例(前30k内): {samp[:24]}')
        # 长度分布（判断是否长尾）
        c = Counter(len(s) for s in newset)
        print(f'    新表记长度分布: {dict(sorted(c.items()))}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
