-- punct_priority.lua —— 标点直出处理器（xhup_ja 专用）
-- ==================================================================
-- 作用：中文模式下按常用标点键，直接上屏中日文通用的全角标点，
--       既不必再按空格确认，也不会退回半角。
--
-- 为什么需要：
--   librime 默认让部分标点经过「分段→翻译→过滤」链路，任一步不顺就会
--   滞留在输入框、只能按空格上屏（且上屏的是半角字符）；librime 1.13
--   起还有「数字分隔符」会把紧接数字的 , . : ' 当作半角分隔符塞进输入框。
--   本处理器排在 punctuator 之前，直接认领这些键并 commit，返回 kAccepted。
--
-- 处理策略：
--   FULL        → 直接上屏对应全角标点（! $ ( ) , : ; < > ? [ \ ] ^ _ { }）
--   HALF_DIRECT → 直接上屏半角原字符（/ @ # & + = -），不进候选框
--   PAIRS       → ' 与 " 连按在「左/右」引号间轮换
--   句点 .      → 紧接数字时作小数点「.」，否则「。」
--   其余按键    → kNoop，交回原流程
--
-- 不处理的场合：抬键 / 含 Ctrl·Alt·Super、正在输入(is_composing)、
--   ASCII 模式、以及 ascii_punct 开启时（HALF_DIRECT 例外，它只看 ascii_mode）。
--
-- librime-lua processor 返回值：0=kRejected / 1=kAccepted / 2=kNoop。
-- ==================================================================

local M = {}

-- 固定全角映射：半角键的 keycode → 直接上屏的全角标点
local FULL = {
  [0x21] = '！',   -- !
  [0x24] = '￥',   -- $
  [0x28] = '（',   -- (
  [0x29] = '）',   -- )
  [0x2C] = '，',   -- ,
  [0x3A] = '：',   -- :
  [0x3B] = '；',   -- ;
  [0x3C] = '《',   -- <
  [0x3E] = '》',   -- >
  [0x3F] = '？',   -- ?
  [0x5B] = '「',   -- [
  [0x5C] = '、',   -- \
  [0x5D] = '」',   -- ]
  [0x5E] = '……',  -- ^
  [0x5F] = '——',  -- _ (Shift+-) 破折号
  [0x7B] = '『',   -- {
  [0x7D] = '』',   -- }
}

-- 成对符号：连续按键时在「左/右」之间轮换
local PAIRS = {
  [0x27] = { '‘', '’' },   -- '
  [0x22] = { '“', '”' },   -- "
}

-- 半角直接上屏：这些键在中文模式下直接 commit 半角原字符，不进候选框。
-- （默认 punctuation 的 half_shape 里它们多是「裸字符串」，会走候选框、需按空格；
--  这里抢在 punctuator 之前直接上屏。`/` 原本会落到全角，现固定为半角斜杠。）
local HALF_DIRECT = {
  [0x2F] = '/',   -- /
  [0x40] = '@',   -- @
  [0x23] = '#',   -- #
  [0x26] = '&',   -- &
  [0x2B] = '+',   -- +
  [0x3D] = '=',   -- =
  [0x2D] = '-',   -- -
}

local KEY_PERIOD = 0x2E   -- .

-- 取「最近一次上屏的文本」，任何异常都安全退化为空串
local function latest_commit(ctx)
  local hist = ctx.commit_history
  if hist then
    local ok, text = pcall(function() return hist:latest_text() end)
    if ok and type(text) == "string" then
      return text
    end
    -- 退一步：取最后一条 CommitRecord
    ok, text = pcall(function()
      local rec = hist:back()
      return rec and rec.text or ""
    end)
    if ok and type(text) == "string" then
      return text
    end
  end
  return ""
end

function M.func(key, env)
  local code = key.keycode

  local full = FULL[code]
  local pair = PAIRS[code]
  local half = HALF_DIRECT[code]

  -- 不关心的按键：交回原有流程
  if not full and not pair and not half and code ~= KEY_PERIOD then
    return 2 -- kNoop
  end

  -- 抬键 / 组合键不处理。
  -- 注意：! ? ( ) 等由 Shift+数字/符号产生，Shift 本身是“正常输入”，
  -- 因此不能用 key:shift() 把它们排除掉。
  if key:release() or key:ctrl() or key:alt() or key:super() then
    return 2 -- kNoop
  end

  local ctx = env.engine.context

  -- 正在输入（有候选）：交回默认流程
  if ctx:is_composing() then
    return 2 -- kNoop
  end

  -- 半角直接上屏：非 ASCII 模式时直接 commit 半角原字符
  -- （ASCII 模式由 ascii_composer 先行处理，不会走到这里；ascii_punct 不影响本分支）
  if half then
    if ctx:get_option("ascii_mode") then
      return 2 -- kNoop
    end
    env.engine:commit_text(half)
    return 1 -- kAccepted
  end

  -- 英文模式、或切到 ASCII 标点时，全角标点交回默认流程
  if ctx:get_option("ascii_mode") or ctx:get_option("ascii_punct") then
    return 2 -- kNoop
  end

  if code == KEY_PERIOD then
    -- 句号：紧接数字时作小数点，否则全角句号
    if latest_commit(ctx):match("%d$") then
      env.engine:commit_text(".")
    else
      env.engine:commit_text("。")
    end
  elseif pair then
    -- 成对引号：紧接上屏左侧引号时出右侧，否则出左侧
    -- （用 commit_history 判断，无持久状态，跨输入串自然复位）
    local side = (latest_commit(ctx) == pair[1]) and 2 or 1
    env.engine:commit_text(pair[side])
  else
    env.engine:commit_text(full)
  end

  return 1 -- kAccepted
end

return M
