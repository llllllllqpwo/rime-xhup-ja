#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_overlap.py —— 中日候选冲突体检（不需部署，纯离线分析）
=================================================================
作用:
  1. 用主方案的小鹤双拼 algebra 把 luna_pinyin 词库的中文编码算出来；
  2. 用日语棱镜规则把 ja_romaji 词库的罗马字编码读出来；
  3. 报告两者编码重叠的情况，并按「日语词权重 vs 中文最高权重」排序，
     用来判断扩词后中文侧是否被挤掉（方案原本的取舍是：中文单字优先）。

用法:
    python3 tools/check_overlap.py [--top 40] [--min-zh 1000]
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))

# ---- 小鹤双拼键位（与 xhup_ja.schema.yaml 的 algebra 一致）----
XLIT = str.maketrans('ⓆⓌⓇⓉⓎⓊⒾⓄⓅⓈⒹⒻⒼⒽⒿⓀⓁⓏⓍⒸⓋⒷⓃⓂ',
                     'qwrtyuiopsdfghjklzxcvbnm')
XH_RULES = [
    (re.compile(r'^([jqxy])u$'), r'\1v'),
    (re.compile(r'^([aoe])([ioun])$'), r'\1\1\2'),
    (re.compile(r'^([aoe])(ng)?$'), r'\1\1\2'),
    (re.compile(r'iu$'), 'Ⓠ'),
    (re.compile(r'(.)ei$'), r'\1Ⓦ'),
    (re.compile(r'uan$'), 'Ⓡ'),
    (re.compile(r'[uv]e$'), 'Ⓣ'),
    (re.compile(r'un$'), 'Ⓨ'),
    (re.compile(r'^sh'), 'Ⓤ'),
    (re.compile(r'^ch'), 'Ⓘ'),
    (re.compile(r'^zh'), 'Ⓥ'),
    (re.compile(r'uo$'), 'Ⓞ'),
    (re.compile(r'ie$'), 'Ⓟ'),
    (re.compile(r'(.)i?ong$'), r'\1Ⓢ'),
    (re.compile(r'ing$|uai$'), 'Ⓚ'),
    (re.compile(r'(.)ai$'), r'\1Ⓓ'),
    (re.compile(r'(.)en$'), r'\1Ⓕ'),
    (re.compile(r'(.)eng$'), r'\1Ⓖ'),
    (re.compile(r'[iu]ang$'), 'Ⓛ'),
    (re.compile(r'(.)ang$'), r'\1Ⓗ'),
    (re.compile(r'ian$'), 'Ⓜ'),
    (re.compile(r'(.)an$'), r'\1Ⓙ'),
    (re.compile(r'(.)ou$'), r'\1Ⓩ'),
    (re.compile(r'[iu]a$'), 'Ⓧ'),
    (re.compile(r'iao$'), 'Ⓝ'),
    (re.compile(r'(.)ao$'), r'\1Ⓒ'),
    (re.compile(r'ui$'), 'Ⓥ'),
    (re.compile(r'in$'), 'Ⓑ'),
]


def xiaohe(syllable):
    """一个拼音音节 -> 小鹤双拼键

    注意：scheme 里的 algebra 规则是**按顺序逐条应用**的（前一条的输出作为后一条的输入），
    不是「匹配一条就停」。例：`a` 先被 xform/^([aoe])(ng)?$/$1$1$2/ 变成 `aa`，
    再被 xform/(^|[ '])aa/$1a/ 这类规则加工，最终落回单键 `a`。
    写成「命中即返回」会得到错误的 `aa`（本文件早期版本就踩过这个坑）。
    """
    if not syllable:
        return None
    s = syllable
    if s == 'xx':
        return None
    for pat, rep in XH_RULES:
        s = pat.sub(rep, s)          # 全部规则依次应用，不提前退出
    return s.translate(XLIT)


def load_ja(path):
    rows = []
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
            if len(p) >= 3:
                rows.append((p[0], p[1], int(p[2])))
    return rows


def load_zh(dict_paths):
    rows = []
    for path in dict_paths:
        if not os.path.exists(path):
            continue
        with open(path, encoding='utf-8') as f:
            started = False
            for line in f:
                line = line.rstrip('\n')
                if line == '...':
                    started = True
                    continue
                if not started or not line or line.startswith('#'):
                    continue
                p = line.split('\t')
                if len(p) >= 2:
                    rows.append((p[0], p[1], int(p[2]) if len(p) > 2 and p[2].isdigit() else 1))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--top', type=int, default=40)
    ap.add_argument('--min-zh', type=int, default=1000, help='只统计权重不低于该值的中文候选')
    ap.add_argument('--ja', default=os.path.join(ROOT, 'ja_romaji.dict.yaml'))
    ap.add_argument('--zh', default=None, help='luna_pinyin 词库路径（可多次用逗号分隔）')
    args = ap.parse_args()

    ja = load_ja(args.ja)
    ja_code = {}
    for text, code, w in ja:
        key = code.replace(' ', '')
        if w > ja_code.get(key, (None, 0))[1]:
            ja_code[key] = (text, w)
    print(f'日语: {len(ja)} 条  ->  唯一编码 {len(ja_code)}')

    zh_paths = []
    if args.zh:
        zh_paths = args.zh.split(',')
    else:
        cand = [
            os.path.expandvars(r'%APPDATA%\Rime\cn_dicts\base.dict.yaml'),
            os.path.expandvars(r'%APPDATA%\Rime\cn_dicts\ext.dict.yaml'),
            os.path.expandvars(r'%APPDATA%\Rime\cn_dicts\tencent.dict.yaml'),
            os.path.expandvars(r'%APPDATA%\Rime\cn_dicts\8105.dict.yaml'),
        ]
        zh_paths = [p for p in cand if os.path.exists(p)]
    if not zh_paths:
        print('未找到中文词库；用 --zh 指定 luna_pinyin.dict.yaml 路径')
        return 1

    zh = load_zh(zh_paths)
    zh_code = {}
    n_parsed = 0
    for text, pinyin, w in zh:
        if w < args.min_zh:
            continue
        syls = pinyin.split()
        if not syls or len(syls) > 8:
            continue
        codes = [xiaohe(s) for s in syls]
        if any(c is None for c in codes):
            continue
        code = ''.join(codes)
        n_parsed += 1
        cur = zh_code.get(code)
        if cur is None or w > cur[1]:
            zh_code[code] = (text, w)
    print(f'中文: 解析 {n_parsed} 条（权重>={args.min_zh}） -> 唯一编码 {len(zh_code)}')

    shared = set(ja_code) & set(zh_code)
    print(f'编码重叠: {len(shared)} 个\n')

    # 日语词压过中文最高权重的编码（= 中文可能被抢位的点）
    beats = [(c, ja_code[c], zh_code[c]) for c in shared if ja_code[c][1] > zh_code[c][1]]
    beats.sort(key=lambda x: -(x[1][1] - x[2][1]))
    print(f'日语权重大于中文最高权重者: {len(beats)} 个（这些码上日语候选会排在中文之前）')
    for c, (jt, jw), (zt, zw) in beats[:args.top]:
        print(f'  {c:<10} 日 {jt}({jw})  >  中 {zt}({zw})')

    # 短码统计：1~3 键的碰撞最影响手感
    print('\n按输入长度统计碰撞（日语权重 > 中文权重）:')
    for n in range(1, 5):
        sub = [c for c, _, _ in beats if len(c) == n]
        tot = [c for c in shared if len(c) == n]
        print(f'  {n} 键: {len(sub)}/{len(tot)}')

    # 精选词/常用日语词是否被中文压住（信息性）
    lost = [(c, ja_code[c], zh_code[c]) for c in shared if ja_code[c][1] < zh_code[c][1]]
    lost.sort(key=lambda x: x[2][1] - x[1][1], reverse=True)
    print(f'\n中文权重更高者: {len(lost)} 个（方案本来就让中文单字优先）')
    for c, (jt, jw), (zt, zw) in lost[:15]:
        print(f'  {c:<10} 中 {zt}({zw})  >  日 {jt}({jw})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
