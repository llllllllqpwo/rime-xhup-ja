--[[
  zh_simplify.lua —— 中文候选简体化（xhup_ja 专用）
  ==================================================================
  为什么不用标准 simplifier 过滤器:
    simplifier 会把【所有】候选一并繁→简，包括日语候选——
    東京会被写成「东京」、頑張って 会变成「顽张って」，对日语是错字。
    本过滤器只转换中文候选；日语候选的注释带 U+200B 零宽标记，原样放行。

  数据文件（随方案分发，源自 OpenCC，Apache-2.0）:
    TSCharacters.txt  单字繁→简映射
    TSPhrases.txt     词组繁→简映射（先行匹配，保证「後面→后面」级精度）

  开关: 方案开关 zh_simp（默认开）。关闭后输出繁体。
--]]

local char_map, phrase_map

local function load_map(path)
  local m = {}
  local f = io.open(path, 'r')
  if not f then return nil end
  for line in f:lines() do
    if line:sub(1, 1) ~= '#' then
      local k, v = line:match('^(%S+)[\t ]+(%S+)')
      if k and not m[k] then m[k] = v end
    end
  end
  f:close()
  return m
end

local function init()
  if char_map then return end
  local dir = rime_api.get_user_data_dir()
  char_map = load_map(dir .. '/TSCharacters.txt') or {}
  phrase_map = load_map(dir .. '/TSPhrases.txt') or {}
end

local function chars(s)
  local t = {}
  for _, cp in utf8.codes(s) do t[#t + 1] = utf8.char(cp) end
  return t
end

-- 繁→简: 先词组(4→2字)最长匹配, 再单字
local function t2s(text)
  local cs = chars(text)
  local out, i, n = {}, 1, #cs
  while i <= n do
    local matched = false
    for L = 4, 2, -1 do
      if i + L - 1 <= n then
        local seg = table.concat(cs, '', i, i + L - 1)
        local v = phrase_map[seg]
        if v then
          out[#out + 1] = v
          i = i + L
          matched = true
          break
        end
      end
    end
    if not matched then
      out[#out + 1] = char_map[cs[i]] or cs[i]
      i = i + 1
    end
  end
  return table.concat(out)
end

-- 含 CJK 汉字才做转换（假名/ ASCII 直通）
local function has_han(s)
  for _, cp in utf8.codes(s) do
    if cp >= 0x3400 and cp <= 0x9FFF then return true end
  end
  return false
end

-- 日语候选的注释里带 U+200B 零宽空格标记（显示不可见）
local JP_ZWSP = '\u{200B}'
-- 兼容旧的可见标记，方便别人改过 comment_format 也能用
local JP_LEGACY = { '⟨JP⟩' }

local function is_jp(cand)
  local c = cand.comment
  if c == nil then return false end
  if c:find(JP_ZWSP, 1, true) then return true end
  for _, m in ipairs(JP_LEGACY) do
    if c:find(m, 1, true) then return true end
  end
  return false
end

local function filter(input, env)
  init()
  local on = env.engine.context:get_option('zh_simp')
  for cand in input:iter() do
    if on and is_jp(cand) then
      -- 日语候选: 原样放行（保留日语汉字形，東京 不能变 东京）
      yield(cand)
    elseif on and has_han(cand.text) then
      local t = t2s(cand.text)
      if t ~= cand.text then
        yield(Candidate(cand.type, cand.start, cand._end, t, cand.comment))
      else
        yield(cand)
      end
    else
      yield(cand)
    end
  end
end

return filter
