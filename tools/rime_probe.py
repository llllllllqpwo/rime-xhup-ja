#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rime_probe.py —— 用真实 librime 引擎测候选（不需要手动打字）
=================================================================
原理：加载小狼毫自带的 rime.dll（librime 的 C API），
在**指定的用户目录**里部署方案，然后模拟按键并打印候选列表。

这样改完 schema 不必反复部署、手打、肉眼比对——直接看到引擎的真实输出。

用法:
    # 在工作区副本上测（安全，不动正在用的目录）
    python3 tools/rime_probe.py --user-dir ../rime-test-user ufm ufme "ni hao"

    # 测多个输入
    python3 tools/rime_probe.py --user-dir ../rime-test-user --schema xhup_ja ufm

注意:
  * 请勿指向正在被小狼毫使用的用户目录（%APPDATA%\\Rime），
    两边同时部署会互相干扰。用副本。
  * 首次运行会编译词库（rime-ice 约 58 MB），需要几分钟；之后有缓存。
"""
import argparse
import ctypes
import os
import sys
from ctypes import POINTER, Structure, c_char_p, c_int, c_size_t, c_uint32, c_void_p


# ---------------------------------------------------------------- librime 结构体
class RimeTraits(Structure):
    _fields_ = [
        ('data_size', c_int),
        ('shared_data_dir', c_char_p),
        ('user_data_dir', c_char_p),
        ('distribution_name', c_char_p),
        ('distribution_code_name', c_char_p),
        ('distribution_version', c_char_p),
        ('app_name', c_char_p),
        ('modules', POINTER(c_char_p)),
        ('min_log_level', c_int),
        ('log_dir', c_char_p),
        ('prebuilt_data_dir', c_char_p),
        ('staging_dir', c_char_p),
    ]


class RimeCandidate(Structure):
    _fields_ = [
        ('text', c_char_p),
        ('comment', c_char_p),
        ('reserved', c_void_p),
    ]


# RimeCandidate 真实布局（librime src/rime_api.h）：
#   struct RimeCandidate {
#     char* text; char* comment; void* reserved;
#     char* preedit; char* type; int quality;   // 后三个不公开，但 Lua 的 cand.* 读它们
#   };
# 之前按 text/comment/preedit/type/quality 顺序解，漏了 reserved，结果全是乱码。
class RimeCandidateFull(Structure):
    _fields_ = [
        ('text', c_char_p),
        ('comment', c_char_p),
        ('reserved', c_void_p),
        ('preedit', c_char_p),
        ('type', c_char_p),
        ('quality', c_int),
    ]


class RimeMenu(Structure):
    _fields_ = [
        ('page_size', c_int),
        ('page_no', c_int),
        ('is_last_page', c_int),
        ('highlighted_candidate_index', c_int),
        ('num_candidates', c_int),
        ('candidates', POINTER(RimeCandidate)),
        ('select_keys', c_char_p),
    ]


class RimeComposition(Structure):
    _fields_ = [
        ('length', c_int),
        ('cursor_pos', c_int),
        ('sel_start', c_int),
        ('sel_end', c_int),
        ('preedit', c_char_p),
    ]


class RimeContext(Structure):
    _fields_ = [
        ('data_size', c_int),
        ('composition', RimeComposition),
        ('menu', RimeMenu),
        ('commit_text_preview', c_char_p),
        ('select_labels', POINTER(c_char_p)),
    ]


def find_rime_dll():
    cands = [
        r'C:\Program Files\Rime\weasel-0.17.0\rime.dll',
        r'C:\Program Files (x86)\Rime\weasel-0.17.0\rime.dll',
    ]
    for c in cands:
        if os.path.exists(c):
            return c
    raise SystemExit('找不到 rime.dll，请用 --dll 指定')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inputs', nargs='*', help='要模拟的按键序列（字符串按字符逐个发送）')
    ap.add_argument('--dll', default=None)
    ap.add_argument('--user-dir', required=True, help='用户目录（用副本，勿指向正在使用的）')
    ap.add_argument('--shared-dir', default=r'C:\Program Files\Rime\weasel-0.17.0\data',
                    help='共享数据目录（含默认方案与 essay.txt）')
    ap.add_argument('--schema', default='xhup_ja')
    ap.add_argument('--top', type=int, default=12)
    ap.add_argument('--no-deploy', action='store_true', help='跳过部署（已有编译缓存时用）')
    ap.add_argument('--show-type', action='store_true',
                    help='打印每个候选的 type/quality/preedit（用于判断候选来自哪个翻译器）')
    args = ap.parse_args()

    user_dir = os.path.abspath(args.user_dir)
    if not os.path.isdir(user_dir):
        raise SystemExit(f'用户目录不存在: {user_dir}')
    if 'AppData\\Roaming\\Rime' in user_dir or 'AppData/Roaming/Rime' in user_dir:
        raise SystemExit('拒绝在正在使用的用户目录上运行，请用副本（--user-dir）')

    rime = ctypes.CDLL(args.dll or find_rime_dll())

    rime.RimeSetup.argtypes = [POINTER(RimeTraits)]
    rime.RimeInitialize.argtypes = [POINTER(RimeTraits)]
    rime.RimeDeployerInitialize.argtypes = [POINTER(RimeTraits)]
    rime.RimeStartMaintenance.argtypes = [ctypes.c_bool]
    rime.RimeJoinMaintenanceThread.argtypes = []
    rime.RimeCreateSession.argtypes = []
    rime.RimeCreateSession.restype = c_void_p
    rime.RimeSimulateKeySequence.argtypes = [c_void_p, c_char_p]
    rime.RimeSimulateKeySequence.restype = ctypes.c_bool
    rime.RimeGetContext.argtypes = [c_void_p, POINTER(RimeContext)]
    rime.RimeGetContext.restype = ctypes.c_bool
    rime.RimeFreeContext.argtypes = [POINTER(RimeContext)]
    rime.RimeGetCurrentSchema.argtypes = [c_void_p, c_char_p, POINTER(c_size_t)]
    rime.RimeGetCurrentSchema.restype = ctypes.c_bool
    rime.RimeCleanupAllSessions.argtypes = []
    rime.RimeFinalize.argtypes = []

    traits = RimeTraits()
    ctypes.memset(ctypes.byref(traits), 0, ctypes.sizeof(traits))
    traits.data_size = ctypes.sizeof(traits)
    traits.shared_data_dir = args.shared_dir.encode()
    traits.user_data_dir = user_dir.encode()
    traits.distribution_name = b'Rime'
    traits.distribution_code_name = b'rime-probe'
    traits.distribution_version = b'1.0'
    traits.app_name = b'rime.probe'
    traits.min_log_level = 2

    rime.RimeSetup(ctypes.byref(traits))
    rime.RimeInitialize(ctypes.byref(traits))

    if not args.no_deploy:
        print(f'部署中（首次要编译词库，请耐心）…  {user_dir}', flush=True)
        rime.RimeStartMaintenance(ctypes.c_bool(True))
        rime.RimeJoinMaintenanceThread()
        print('部署完成', flush=True)

    # 注意: RimeGetCurrentSchema 在 weasel 0.17 自带的 rime.dll 上调用即崩
    # （签名/缓冲区约定不匹配，实测 access violation）。探查候选用不到它，跳过。
    session = rime.RimeCreateSession()
    if not session:
        raise SystemExit('创建会话失败')
    print(f'会话已建立，开始测试 {len(args.inputs)} 个输入\n', flush=True)

    bksp = b'{BackSpace}'
    for keys in args.inputs:
        ctx = RimeContext()
        ctypes.memset(ctypes.byref(ctx), 0, ctypes.sizeof(ctx))
        ctx.data_size = ctypes.sizeof(ctx)
        ok = rime.RimeSimulateKeySequence(session, keys.encode('utf-8'))
        got = rime.RimeGetContext(session, ctypes.byref(ctx))
        print(f'=== 输入 {keys!r}  (simulate={ok}, context={got}) ===')
        if got:
            pre = ctx.composition.preedit.decode(errors='replace') if ctx.composition.preedit else ''
            print(f'  preedit: {pre!r}')
            print(f'  候选 {ctx.menu.num_candidates} 个:')
            base = ctypes.cast(ctx.menu.candidates, ctypes.POINTER(RimeCandidateFull))
            for i in range(min(ctx.menu.num_candidates, args.top)):
                c = ctx.menu.candidates[i]
                text = c.text.decode(errors='replace') if c.text else ''
                cmt = c.comment.decode(errors='replace') if c.comment else ''
                mark = ' *' if i == ctx.menu.highlighted_candidate_index else '  '
                extra = ''
                if args.show_type:
                    f = base[i]
                    t = f.type.decode(errors='replace') if f.type else ''
                    pre = f.preedit.decode(errors='replace') if f.preedit else ''
                    extra = f'  [type={t!r} q={f.quality} preedit={pre!r}]'
                print(f'   {mark}{i+1}. {text}' + (f'  〔{cmt}〕' if cmt else '') + extra)
        rime.RimeFreeContext(ctypes.byref(ctx))
        # 清空输入
        for _ in range(len(keys) + 8):
            rime.RimeSimulateKeySequence(session, bksp)
            rime.RimeSimulateKeySequence(session, b'{Escape}')
        print()

    rime.RimeCleanupAllSessions()
    rime.RimeFinalize()
    return 0


if __name__ == '__main__':
    sys.exit(main())
