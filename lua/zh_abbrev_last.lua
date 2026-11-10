-- zh_abbrev_last.lua —— 逐个音节判定「简写」，要求非最后音节必须完整
local M = {}
local ZWSP = '\u{200B}'

-- 本身就是完整拼写的音节（即使只有 1~2 个字母也不当成简写）
local GENUINE = { a=true, e=true, o=true, n=true, m=true, ng=true, er=true, hm=true, hng=true }
-- u/i/v 简写经 preedit_format 反显后变成 sh/ch/zh，也属于「简写」
local ABBR2 = { sh=true, zh=true, ch=true }

local function is_jp(c)
  local cm = c.comment
  return cm ~= nil and cm:find(ZWSP, 1, true) ~= nil
end

local function tokens(s)
  local t = {}
  for tok in s:gmatch('%S+') do t[#t + 1] = tok end
  return t
end

local function is_abbrev_tok(t)
  if GENUINE[t] then return false end
  return #t == 1 or ABBR2[t] == true
end

local function has_nonlast_abbrev(c)
  local sp = c.preedit
  if not sp or sp == '' then return false end
  local tk = tokens(sp)
  if #tk < 2 then return false end
  for i = 1, #tk - 1 do
    if is_abbrev_tok(tk[i]) then return true end
  end
  return false
end

function M.func(input, env)
  for cand in input:iter() do
    if is_jp(cand) or not has_nonlast_abbrev(cand) then
      yield(cand)
    end
  end
end

return M