#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compare_dicts.py —— 与市面日文 Rime 词库做覆盖/臃肿对比
=================================================================
对照对象（默认读 _compare/ 下的文件）:
  gkovacs/rime-japanese  japanese.mozc.dict.yaml  + japanese.jmdict.dict.yaml
    —— 最主流的 Rime 日文方案（★404），同样是 Mozc + JMdict 双词典，
       格式为「表记 <TAB> 读音」，与本项目的罗马字编码可直接互转比较。

用法:
    python3 tools/compare_dicts.py
    python3 tools/compare_dicts.py --other path/a.yaml,path/b.yaml
"""
import argparse
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from gen_ja_dict import kana_section  # noqa: E402

KATA = 'ァ-ヺ'


def to_hira(s):
    out = []
    for c in s:
        o = ord(c)
        if 0x30A1 <= o <= 0x30F6:
            out.append(chr(o - 0x60))
        elif c == 'ヷ':
            out.append('わ')
        elif c == 'ヸ':
            out.append('ゐ')
        elif c == 'ヹ':
            out.append('ゑ')
        elif c == 'ヺ':
            out.append('を')
        elif c == 'ヴ':
            out.append('ゔ')
        else:
            out.append(c)
    return ''.join(out)


def load_rime_pairs(path):
    """读 Rime 日文词库 -> {(表记, 规范化罗马字读音): 权重}

    市面上的日文 Rime 词库（gkovacs/rime-japanese 等）第二列是**罗马字**
    （如 明白<TAB>meihaku），不是假名。所以这里不做假名校验，
    直接保留原样，再统一规范化以便与我们的编码对齐。
    """
    out = {}
    started = False
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n')
            if line == '...':
                started = True
                continue
            if not started or not line or line.startswith('#'):
                continue
            p = line.split('\t')
            if len(p) < 2:
                continue
            surface, reading = p[0], p[1].strip()
            if not surface or not reading:
                continue
            w = 0
            if len(p) >= 3 and p[2].strip().isdigit():
                w = int(p[2])
            key = (surface, norm_reading(reading))
            if key not in out or w > out[key]:
                out[key] = w
    return out


def norm_reading(reading):
    """把各种写法的读音规范化成「无空格罗马字」，便于跨词典比较。

    处理三种输入:
      - 罗马字（市面词库）: meihaku / me i ha ku   -> meihaku
      - 平假名（本项目的 ja_words_local 等）: めいはく -> mei ha ku -> meihaku
      - 片假名: メイハク -> 同上
    """
    s = reading.strip()
    if not s:
        return s
    # 含假名 -> 先转成我们的罗马字编码
    if re.search(r'[ぁ-ゖ' + KATA + r'ー]', s):
        from gen_ja_dict import romaji_code
        code = romaji_code(s)
        s = code if code else s
    # 去掉空格、长音符与常见分隔符
    s = s.replace(' ', '').replace('-', '').replace('＝', '').replace('=', '')
    return s.lower()


def load_ours(path):
    """读本项目词典 -> {(表记, 规范化罗马字读音): 权重}"""
    out = {}
    started = False
    with open(path, encoding='utf-8') as f:
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
            out[(p[0], norm_reading(p[1].replace(' ', '')))] = int(p[2])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--other', default=None,
                    help='对照词库路径，逗号分隔（默认用 _compare/ 下的 gkovacs 两本）')
    ap.add_argument('--core-sample', type=int, default=0,
                    help='额外打印 N 个「我们有、对方没有」的样本')
    args = ap.parse_args()

    ours = load_ours(os.path.join(ROOT, 'ja_romaji.dict.yaml'))

    # 我们的表记集合（同一表记可能多个读音，这里用 表记+读音 对比较）
    ours_pairs = set(ours)

    if args.other:
        others = [(os.path.basename(p), load_rime_pairs(p)) for p in args.other.split(',')]
    else:
        cand = [
            ('gkovacs mozc', os.path.join(ROOT, '_compare', 'gkovacs.mozc.dict.yaml')),
            ('gkovacs jmdict', os.path.join(ROOT, '_compare', 'gkovacs.jmdict.dict.yaml')),
        ]
        others = [(n, load_rime_pairs(p)) for n, p in cand if os.path.exists(p)]

    if not others:
        print('没有找到对照词库，先跑 tools/_getjp.mjs')
        return 1

    print('=' * 74)
    print(f'本项目    : {len(ours):>9,} 条 (表记+读音对 {len(ours_pairs):,})')
    for n, d in others:
        print(f'{n:<14}: {len(d):>9,} 条')
    print('=' * 74)
    print('（读音已统一规范化成罗马字，双方可直接比较）')

    union_other = {}
    for n, d in others:
        union_other.update(d)
    other_pairs = set(union_other)

    inter = ours_pairs & other_pairs
    only_ours = ours_pairs - other_pairs
    only_other = other_pairs - ours_pairs

    print()
    print('【1】条目级重合（表记+读音 完全一致才算重合）')
    print(f'  双方都有 : {len(inter):>9,}')
    print(f'  仅我们有 : {len(only_ours):>9,}  ({len(only_ours)/len(ours_pairs)*100:.1f}% of ours)')
    print(f'  仅对方有 : {len(only_other):>9,}  ({len(only_other)/len(other_pairs)*100:.1f}% of theirs)')

    # 表记级（忽略读音差异）
    ours_surf = {s for s, _ in ours_pairs}
    other_surf = {s for s, _ in other_pairs}
    print()
    print('【2】表记级重合（只看写法，忽略读音）')
    print(f'  我们表记 : {len(ours_surf):,}')
    print(f'  对方表记 : {len(other_surf):,}')
    print(f'  交集     : {len(ours_surf & other_surf):,}')
    print(f'  仅我们   : {len(ours_surf - other_surf):,}')
    print(f'  仅对方   : {len(other_surf - ours_surf):,}  ← 对方有而我们完全没有的写法')

    # 「仅对方有」里的样本：这是真正的覆盖缺口
    print()
    print('【3】对方有、我们没有的样本（按对方文件顺序取前 40）')
    miss = [k for k in union_other if k not in ours_pairs]
    for s, r in miss[:40]:
        print(f'    {s}  ({r})')
    print(f'    … 共 {len(miss):,} 条')

    # 「仅我们有」构成分析：判断是否臃肿
    print()
    print('【4】仅我们有的条目构成（判断是否臃肿）')
    c = Counter()
    for s, r in only_ours:
        if len(s) == 1:
            c['单字'] += 1
        elif len(s) >= 6:
            c['长词(6字以上)'] += 1
        elif s == r:
            c['假名写法(表记=读音)'] += 1
        elif re.search(r'[一-鿿]', s) and re.search(r'[ぁ-ゖ]', s):
            c['汉字+送假名'] += 1
        elif re.search(r'[一-鿿]', s):
            c['纯汉字词'] += 1
        elif re.search('[' + KATA + ']', s):
            c['片假名词'] += 1
        else:
            c['其他'] += 1
    for k, v in c.most_common():
        print(f'    {k:<16} {v:>9,}')

    # 长度分布对比
    print()
    print('【5】表记长度分布对比（看长尾是否失控）')
    def dist(d):
        cc = Counter(min(len(s), 9) for s, _ in d)
        return cc
    dc, oc = dist(ours_pairs), dist(other_pairs)
    print(f'    {"长度":<6}{"我们":>12}{"对方":>12}{"占比我们":>12}{"占比对方":>12}')
    for L in range(1, 10):
        label = f'{L}' if L < 9 else '9+'
        a, b = dc.get(L, 0), oc.get(L, 0)
        print(f'    {label:<6}{a:>12,}{b:>12,}{a/len(ours_pairs)*100:>11.1f}%{b/len(other_pairs)*100:>11.1f}%')

    # 同一读音下的平均候选数（候选页拥挤度）
    print()
    print('【6】同音候选密度（每个读音平均多少写法）')
    for name, d in [('我们', ours_pairs)] + [(n, set(x)) for n, x in others]:
        byr = defaultdict(int)
        for s, r in d:
            byr[r] += 1
        avg = sum(byr.values()) / max(1, len(byr))
        mx = max(byr.values()) if byr else 0
        print(f'    {name:<14} 读音数 {len(byr):>8,}  平均候选 {avg:>6.2f}  最多 {mx}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
