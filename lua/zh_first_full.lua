-- zh_first_full.lua —— 中文简拼「首音节必须完整」（xhup_ja 专用）
-- ------------------------------------------------------------------
-- 背景：小鹤简拼(abbrev)是逐音节展开的，任何音节都能被简写成单字母，
-- 于是多音节词首音节简写会和「首音节完整」的读法撞码。典型：
--     rrj  →  软件/软禁(ruan + j)   与   仍然/冉冉/若然(r + ran)
-- 本过滤器：只要同一输入里存在「首音节完整」的中文读法，就丢弃「首音节
-- 单字母简写」的读法，从而只保留首音节完整的读法。
--   · 对 2 字词 = 「首字全码，只末字可简写」，正好消掉 rrj→仍然；
--   · 没有「完整首音节」可选时不丢（保证 rj、wm 等纯两字简拼照常可用）；
--   · 单音节词不动；日语候选（注释含 U+200B）完全不干预。
--
-- 说明：Rime 层拿不到「原始键入码」，只能依据候选拼写(cand.preedit)判断，
-- 因此对 3 字及以上词，仅能保证「首」音节完整，中间音节是否简写无法逐一拦截。
-- ------------------------------------------------------------------

local M = {}

local ZWSP = '\u{200B}'

-- 本身就是单字母的完整音节（a/e/o/n…），不当作「简写」
local GENUINE = { a = true, e = true, o = true, n = true, m = true, ng = true, hm = true, hng = true }

local function is_jp(cand)
  local cm = cand.comment
  return cm ~= nil and cm:find(ZWSP, 1, true) ~= nil
end

local function tokens(s)
  local t = {}
  for tok in s:gmatch('%S+') do t[#t + 1] = tok end
  return t
end

-- 首音节为「完整拼写」：拼写 ≥2 字母
local function first_full(cand)
  local sp = cand.preedit
  if not sp or sp == '' then return false end
  local tk = tokens(sp)
  if #tk < 2 then return false end
  return #tk[1] >= 2
end

-- 首音节为「单字母简写」
local function first_abbrev(cand)
  local sp = cand.preedit
  if not sp or sp == '' then return false end
  local tk = tokens(sp)
  if #tk < 2 then return false end
  local t1 = tk[1]
  return #t1 == 1 and not GENUINE[t1]
end

function M.func(input, env)
  local list = {}
  local has_full = false
  for cand in input:iter() do
    list[#list + 1] = cand
    if not is_jp(cand) and first_full(cand) then has_full = true end
  end

  for _, cand in ipairs(list) do
    local drop = has_full and not is_jp(cand) and first_abbrev(cand)
    if not drop then yield(cand) end
  end
end

return M