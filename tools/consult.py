#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
consult.py —— 离线查词：输入罗马字，看日语侧的候选与权重
=================================================================
模拟 script_translator 的「音节切分 + 查表」过程，用来在部署前确认
某个输入能出哪些日语候选、排在第几。比反复重新部署快得多。

用法:
    python3 tools/consult.py nihongo konnichiwa ganbatte
    python3 tools/consult.py watashinonamaeha
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from gen_ja_dict import kana_section  # noqa: E402


def load_dict(path):
    """-> {code_no_space: [(text, weight), ...]}"""
    table = {}
    with open(path, encoding='utf-8') as f:
        started = False
        for line in f:
            line = line.rstrip('\n')
            if line == '...':
                started = True
                continue
            if not started or not line:
                continue
            p = line.split('\t')
            if len(p) < 3:
                continue
            key = p[1].replace(' ', '')
            table.setdefault(key, []).append((p[0], int(p[2])))
    for k in table:
        table[k].sort(key=lambda x: -x[1])
    return table


def segment(prism_syllables, query, limit=6):
    """把查询串切成音节（贪心最长匹配，模拟 prism 切分），返回切分方案列表"""
    results = []
    maxlen = max((len(s) for s in prism_syllables), default=1)

    def walk(pos, acc):
        if len(results) >= limit:
            return
        if pos == len(query):
            results.append(list(acc))
            return
        for n in range(min(maxlen, len(query) - pos), 0, -1):
            piece = query[pos:pos + n]
            if piece in prism_syllables:
                acc.append(piece)
                walk(pos + n, acc)
                acc.pop()

    walk(0, [])
    return results


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    dict_path = os.path.join(ROOT, 'ja_romaji.dict.yaml')
    table = load_dict(dict_path)
    prism = set()
    for code in table:
        # 已知编码按音节表反推所有可能音节（这里用音节表本身作 prism 近似）
        pass
    syllabary = {c.replace(' ', '') for _, c, _ in kana_section()}
    # prism 还包含派生变体（si/sya/nn...），这里补上常用容错形式
    syllabary |= {'si', 'ti', 'tu', 'hu', 'zi', 'sya', 'syu', 'syo', 'tya', 'tyu',
                  'tyo', 'jya', 'jyu', 'jyo', 'zya', 'zyu', 'zyo', 'nn', 'm', 'wa',
                  'e', 'o', 'xtu', 'ltu', 'xa', 'la'}

    print(f'词典: {dict_path}')
    print(f'音节数: {len(syllabary)}\n')
    for query in args:
        q = query.lower().replace(' ', '').replace("'", '')
        print(f'=== {query} ===')
        plans = segment(syllabary, q)
        if not plans:
            print('  （无法切成合法音节）\n')
            continue
        for plan in plans[:4]:
            joined = ''.join(plan)
            cands = table.get(joined, [])
            if not cands:
                continue
            shown = ', '.join(f'{t}({w})' for t, w in cands[:8])
            print(f'  切分 {"|".join(plan)}: {shown}')
        # 整串未收录时的头部雅音节候选
        if q not in table:
            plan = plans[0]
            print('  —— 逐音节首候选:', ', '.join(
                (table.get(s, [('<无>', 0)])[0][0] + f'({table.get(s, [("<无>", 0)])[0][1]})')
                for s in plan[:6]))
        print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
