-- kana_mode.lua —— 平假名/片假名 一次性模式（Shift+h / Shift+k）
-- ==================================================================
-- 用途：按 Shift+h 进入平假名模式、Shift+k 进入片假名模式，
--       当前这一段输入只出平假名/片假名，上屏后自动关闭（一次性）。
--
-- 实现：本处理器排在 processors 最前（抢在 ascii_composer 之前），
--       吞掉 H/K 键，用 context 属性 kana_mode 记录状态：
--         ''           未激活
--         'hira_armed' 刚按 Shift+h，等第一个小写字母落键
--         'kata_armed' 刚按 Shift+k，等第一个小写字母落键
--         'hira'       已进入平假名模式（正在打 romaji）
--         'kata'       已进入片假名模式
--       jp_lang.lua 的过滤器读同一属性，对候选做假名过滤/转换。
--
-- 一次性：上屏后输入框变空、属性残留为 hira/kata；下一次按键若非 H/K，
--        在「输入框空 + 非 armed」分支里清空属性，回到普通混输。
--
-- librime-lua processor 约定：返回 0=kRejected / 1=kAccepted / 2=kNoop。
-- ==================================================================

local M = {}

local PROP   = 'kana_mode'
local CODE_H = 0x48   -- 'H'
local CODE_K = 0x4B   -- 'K'

local function get_mode(ctx)
  return ctx:get_property(PROP) or ''
end

local function set_mode(ctx, v)
  ctx:set_property(PROP, v)
end

function M.func(key, env)
  if key:release() or key:ctrl() or key:alt() or key:super() then
    return 2 -- kNoop
  end

  local ctx = env.engine.context

  -- ASCII 模式下不拦截，并清掉残留模式
  if ctx:get_option('ascii_mode') then
    if get_mode(ctx) ~= '' then set_mode(ctx, '') end
    return 2
  end

  local code = key.keycode
  local mode = get_mode(ctx)
  local input_empty = (ctx.input == '' and not ctx:is_composing())

  -- armed：刚按过 H/K，等第一个小写字母落键（此时输入框仍空）
  if (mode == 'hira_armed' or mode == 'kata_armed') and input_empty then
    if code >= 0x61 and code <= 0x7A then
      -- 小写字母：正式进入模式，交给 speller 正常进串
      set_mode(ctx, mode == 'hira_armed' and 'hira' or 'kata')
      return 2 -- kNoop
    else
      -- 非小写：取消 arming
      set_mode(ctx, '')
      return 2
    end
  end

  -- 输入框空（非 armed）：新输入的起点
  if input_empty then
    if key:shift() and code == CODE_H then
      set_mode(ctx, 'hira_armed')
      return 1 -- kAccepted（吞键，不上屏不入串）
    end
    if key:shift() and code == CODE_K then
      set_mode(ctx, 'kata_armed')
      return 1 -- kAccepted
    end
    -- 非 H/K 的新输入：若上次残留 hira/kata（已上屏），清空回到普通模式
    if mode == 'hira' or mode == 'kata' then
      set_mode(ctx, '')
    end
    return 2
  end

  -- 输入非空：不干预（speller / 编辑器处理）
  return 2
end

return M
