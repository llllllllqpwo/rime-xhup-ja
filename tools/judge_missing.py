#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
judge_missing.py —— 判定「对方有我们没有」的条目是真缺口还是垃圾
=================================================================
做法：把对方词库的罗马字读音**反解成假名**，再走一遍本项目的入库校验
（gen_ja_dict 的 moras / romaji_code / 音节表）。能通过的才可能是真缺口，
通不过的说明对方词典里混了本项目会丢弃的噪音。

用法:
    python3 tools/judge_missing.py [--sample 300]
"""
import argparse
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import gen_ja_dict as g  # noqa: E402
from compare_dicts import load_ours, load_rime_pairs, norm_reading  # noqa: E402

# 罗马字 -> 假名 反查表（用音节表的逆映射）
CODE2KANA = {}
for text, code, _w in g.kana_section():
    c = code.replace(' ', '')
    # 只保留「表记本身就是假名」的条目，避免汉字混进来
    if all(ch in g.BASE or ch in g.KATA or ch in 'ゃゅょぁぃぅぇぉゎッャュョァィゥェォー' for ch in text):
        CODE2KANA.setdefault(c, text)


def romaji_to_kana(code):
    """贪心最长匹配把无空格罗马字还原成假名；失败返回 None"""
    if not code:
        return None
    out, i, n = [], 0, len(code)
    maxlen = max((len(k) for k in CODE2KANA), default=1)
    while i < n:
        for L in range(min(maxlen, n - i), 0, -1):
            piece = code[i:i + L]
            if piece in CODE2KANA:
                out.append(CODE2KANA[piece])
                i += L
                break
        else:
            return None
    return ''.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sample', type=int, default=0, help='随机抽样条数（0 = 全量）')
    args = ap.parse_args()

    ours = load_ours(os.path.join(ROOT, 'ja_romaji.dict.yaml'))
    ours_pairs = set(ours)

    other = {}
    for n in ('gkovacs.mozc.dict.yaml', 'gkovacs.jmdict.dict.yaml'):
        p = os.path.join(ROOT, '_compare', n)
        if os.path.exists(p):
            other.update(load_rime_pairs(p))
    print(f'本项目 {len(ours_pairs):,} 条 / 对照 {len(other):,} 条')

    missing = [(s, r) for (s, r) in other if (s, r) not in ours_pairs]
    print(f'对方有我们没有: {len(missing):,} 条\n')

    syl = {c.replace(' ', '') for _, c, _ in g.kana_section()}
    verd = Counter()
    bad_samples = {k: [] for k in ('无法反解', '音节不在表内', '表记非法', '读音过长')}
    ok_samples = []

    items = missing
    if args.sample and args.sample < len(missing):
        step = max(1, len(missing) // args.sample)
        items = missing[::step][:args.sample]

    for surface, code in items:
        # 1) 罗马字反解成假名
        kana = romaji_to_kana(code)
        if kana is None:
            verd['无法反解(不是合法罗马字读音)'] += 1
            if len(bad_samples['无法反解']) < 12:
                bad_samples['无法反解'].append((surface, code))
            continue
        # 2) 表记合法性（与构建脚本同一套正则）
        if not g.is_kana_only(surface) and not re.fullmatch(r'[ぁ-ゖァ-ヺー一-鿿々〆ヶ〇]+', surface):
            verd['表记非法'] += 1
            if len(bad_samples['表记非法']) < 12:
                bad_samples['表记非法'].append((surface, code))
            continue
        if len(surface) > 8:
            verd['表记过长(>8字)'] += 1
            continue
        # 3) 编码能否被本项目音节表接受
        rc = g.romaji_code(kana)
        if rc is None or any(x not in syl for x in rc.split()):
            verd['音节不在音节表内'] += 1
            if len(bad_samples['音节不在表内']) < 12:
                bad_samples['音节不在表内'].append((surface, code))
            continue
        verd['通过校验（可能是真缺口）'] += 1
        if len(ok_samples) < 40:
            ok_samples.append((surface, kana, code))

    total = sum(verd.values())
    print('=== 判定结果 ===')
    for k, v in verd.most_common():
        print(f'  {k:<28} {v:>9,}  ({v/total*100:5.1f}%)')

    print()
    print('=== 被判定为噪音的样本 ===')
    for k, samples in bad_samples.items():
        if not samples:
            continue
        print(f'  [{k}]')
        for s, c in samples[:8]:
            print(f'     {s}  ({c})')

    print()
    print('=== 通过校验的样本（值得考虑补进去的） ===')
    for s, kana, code in ok_samples[:40]:
        print(f'     {s}  ({kana} / {code})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
