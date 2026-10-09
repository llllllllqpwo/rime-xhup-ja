#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
budget_gain.py —— 量化「放宽专名预算」的边际增益
=================================================================
口径与 bench_coverage.py 一致（剔除单字与纯平假名碎片），
避免出现「22532 vs 3597」那种拿不同词表比的笑话。

结论用一句话概括：专名预算在 190k 时已经饱和，再放宽对常用词覆盖零增益，
只是把不会被用到的长尾名字塞进词典。
"""
import json
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import gen_ja_dict as g  # noqa: E402

OK_SURFACE = re.compile(r'[ぁ-ゖァ-ヺー一-鿿々〆ヶ〇]+')
# 与 bench_coverage.load_freq_words 完全相同的过滤
HAS_KANJI_KATA = re.compile(r'[一-鿿ァ-ヺ]')


def main():
    ours = set()
    started = False
    for line in open(os.path.join(ROOT, 'ja_romaji.dict.yaml'), encoding='utf-8'):
        line = line.rstrip('\n')
        if line == '...':
            started = True
            continue
        if not started or not line:
            continue
        p = line.split('\t')
        if len(p) >= 3:
            ours.add(p[0])

    # 词频表：按 bench_coverage 的口径取前 30000
    judge = []
    rank_all = {}
    for i, line in enumerate(open(os.path.join(ROOT, '_cache', 'ja_50k.txt'), encoding='utf-8')):
        parts = line.split()
        if len(parts) != 2 or not parts[1].isdigit():
            continue
        w = parts[0]
        if w not in rank_all:
            rank_all[w] = i + 1
        if len(w) < 2 or not HAS_KANJI_KATA.search(w):
            continue
        judge.append(w)
        if len(judge) >= 30000:
            break
    judge_set = set(judge)
    base_hit = len(judge_set & ours)
    print(f'裁判词表 {len(judge_set):,} 词（剔除单字与纯平假名），现有词典命中 {base_hit:,}')

    # jmnedict 候选，按构建脚本同样的排序
    raw = open(os.path.join(ROOT, '_cache', 'jmnedict.json'), encoding='utf-8', errors='replace').read()
    j = json.loads(raw[:raw.rfind('}') + 1])
    kanji_c, kana_c = [], []
    for e in j['words']:
        ks = [k['text'] for k in (e.get('kanji') or [])]
        rs = [k['text'] for k in (e.get('kana') or [])]
        ks = [s for s in ks if OK_SURFACE.fullmatch(s) and len(s) <= 8]
        rs = [s for s in rs if g.romaji_code(s)]
        if not rs:
            continue
        if ks:
            for s in ks:
                for r in rs:
                    kanji_c.append((s, rank_all.get(s, 0)))
        else:
            for r in rs:
                if 2 <= len(r) <= 8:
                    kana_c.append((r, rank_all.get(r, 0)))
    key = lambda x: (x[1] if x[1] else 10 ** 9, len(x[0]), x[0])
    kanji_c.sort(key=key)
    kana_c.sort(key=key)

    print()
    print(f'{"汉字预算":>9} {"假名预算":>9} {"新增表记":>10} {"裁判词命中":>11} {"相对现有增量":>13}')
    for kb, nb in [(190000, 40000), (250000, 50000), (300000, 60000), (400000, 80000), (len(kanji_c), len(kana_c))]:
        got = set(ours)
        add = {s for s, _ in kanji_c[:kb]} | {s for s, _ in kana_c[:nb]}
        got |= add
        hit = len(judge_set & got)
        print(f'{kb:>9,} {nb:>9,} {len(add):>10,} {hit:>11,} {hit - base_hit:>+13}')
    print()
    print('说明：最后一行的预算 = 全收，用来证明「再放宽也没有增量」。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
