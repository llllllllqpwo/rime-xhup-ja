#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compare_short.py —— 短码中日候选对比（离线，不需要部署）
=================================================================
把「中文小鹤双拼」和「日语罗马字」在**同一输入串**下的候选都算出来，
按权重合并排序，用来判断短码上谁排在前面。

用途：检查「单键/两键输入时中文高频字会不会被日语假名挤掉」。

用法:
    python3 tools/compare_short.py                # 检查全部 1~2 键组合
    python3 tools/compare_short.py r l d b m w    # 只查指定输入
    python3 tools/compare_short.py --max-len 3
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)

from gen_ja_dict import kana_section  # noqa: E402
from check_overlap import xiaohe, load_ja  # noqa: E402

# 小鹤双拼：声母键与韵母键
INITIALS = 'bpmfdtnlgkhjqxzcsrywv'
FINALS = 'aoeiuv' + 'qwrtyuiopsdfghjklzxcvbnm'


def pinyin_codes(syllables):
    """拼音音节列表 -> 小鹤编码；任一步失败返回 None"""
    out = []
    for s in syllables:
        c = xiaohe(s)
        if c is None:
            return None
        out.append(c)
    return ''.join(out)


def load_zh(paths, min_weight=0):
    """-> {小鹤编码: [(词, 权重)]}"""
    table = {}
    for path in paths:
        if not os.path.exists(path):
            continue
        started = False
        for line in open(path, encoding='utf-8'):
            line = line.rstrip('\n')
            if line == '...':
                started = True
                continue
            if not started or not line or line.startswith('#'):
                continue
            p = line.split('\t')
            if len(p) < 2:
                continue
            word, pinyin = p[0], p[1]
            w = int(p[2]) if len(p) > 2 and p[2].isdigit() else 1
            if w < min_weight:
                continue
            syls = pinyin.split()
            if not syls or len(syls) > 6:
                continue
            code = pinyin_codes(syls)
            if code is None:
                continue
            table.setdefault(code, []).append((word, w))
    for k in table:
        table[k].sort(key=lambda x: -x[1])
    return table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('queries', nargs='*')
    ap.add_argument('--max-len', type=int, default=2)
    ap.add_argument('--top', type=int, default=8)
    ap.add_argument('--page', type=int, default=6, help='候选页大小（决定前几个最关键）')
    args = ap.parse_args()

    ja = {}
    for text, code, w in load_ja(os.path.join(ROOT, 'ja_romaji.dict.yaml')):
        key = code.replace(' ', '')
        ja.setdefault(key, []).append((text, w))
    for k in ja:
        ja[k].sort(key=lambda x: -x[1])

    zh_paths = [os.path.expandvars(r'%APPDATA%\Rime\cn_dicts\%s') % f
                for f in ('8105.dict.yaml', 'base.dict.yaml', 'ext.dict.yaml', 'tencent.dict.yaml')]
    zh = load_zh(zh_paths)
    print(f'日语编码 {len(ja)} 个 / 中文编码 {len(zh)} 个（已合并 rime-ice 词库）\n')

    if args.queries:
        queries = args.queries
    else:
        letters = 'zyxwvutsrqponmlkjihgfedcba'
        queries = list(letters)
        if args.max_len >= 2:
            # 只列声母+韵母的常见两键组合，避免刷屏
            queries += [a + b for a in 'bpmfdtnlgkhjqxzcsryw' for b in 'aeiou']

    for q in queries:
        jl = ja.get(q, [])
        zl = zh.get(q, [])
        merged = [(t, w, '日') for t, w in jl] + [(t, w, '中') for t, w in zl]
        merged.sort(key=lambda x: -x[1])
        head = ' | '.join(f'{t}({w},{s})' for t, w, s in merged[:args.top])
        first_page = merged[:args.page]
        n_zh = sum(1 for _, _, s in first_page if s == '中')
        flag = '' if not first_page else ('  ← 首页无中文' if n_zh == 0 else '')
        print(f'[{q}] 日{len(jl)} 中{len(zl)}')
        print(f'    {head}{flag}')


if __name__ == '__main__':
    main()
