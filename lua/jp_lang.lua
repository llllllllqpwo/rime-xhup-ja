-- jp_lang.lua —— 中日候选语言隔离（xhup_ja 专用）
-- ================================================================
-- 用途：在中日混输时按语言筛分候选，避免日语候选挤占中文候选。
--
-- 背景（实测确认）：
--   中文与日语是两个独立的 prism（中文 xhup_ja_zh、日语 ja_romaji），
--   同一串按键会被两个翻译器各自解析，候选合并进同一列表。
--   日文词库里每个假名都带罗马字编码（か=ka、きゃ=kya…），
--   于是 shi/chi/tsu 这类串会命中日语；ka 这类双拼与罗马字同形的串
--   还会同时命中中日两侧。speller/algebra 按音节统一处理、无法只对某个
--   translator 生效，所以只能在**候选层**做语言判定。
--
--   注意：本方案的「简拼(abbrev)」只存在于中文 prism（主方案 algebra），
--   日语 prism 由 ja_romaji 依赖方案构建、不含简拼；也就是说日语侧根本
--   没有简拼，这里也就无需、且不存在任何针对「日文简拼」的限制。
--
-- 判定依据：日文候选的注释里带一个 U+200B 零宽空格标记
--   （见 xhup_ja.schema.yaml 的 japanese/comment_format），
--   显示上完全看不见，中文候选没有该标记。
--   为什么不靠猜文字：日语候选里也有汉字（東京/日本語），中文候选里也可能有假名，
--   用「注释里有没有标记」判断最可靠。
--
-- 规则（按「用户从不混写中日」的设定）：
--   1. 罗马字没打完（末尾是辅音，如打 watashi 打到 watas 的 s）→ 暂不显示日文候选；
--      末尾是元音 a/e/i/o/u 或拨音 n 才算一个完整罗马字，才显示日文
--   2. 其余情况不动，交给权重排序（保持中日混输的既有行为）
--
-- 单键（k/a…）说明：日语侧只会命中「罗马字本身就是单键」的假名
--   （あ=a い=i う=u え=e お=o ん=n）；か=ka 在单键 k 下本就不命中日语，
--   单键辅音则由规则 1 挡掉，故无需额外的单键特判。
--
-- 想调整行为，改下面的 JP_TAIL 即可。
-- ================================================================

local M = {}

-- 「完整的罗马字结尾」：元音 a e i o u 或拨音 n。
-- 末尾是其它辅音（b c d f g h j k l m p q r s t v w x y z …）
-- 说明这个罗马字音节/词还没打完，此时不显示日文候选。
local JP_TAIL = {
  a = true, e = true, i = true, o = true, u = true, n = true,
}

local function romaji_tail_ok(s)
  if s == nil or s == '' then return false end
  return JP_TAIL[s:sub(-1)] == true
end

-- 日语候选的注释里带一个 U+200B 零宽空格做标记（显示上看不见）。
-- 这样注释对用户只显示罗马字本身，而过滤器仍能判断语言。
-- 旧格式 ⟨JP⟩ 也一并兼容，方便别人改过 comment_format 也能用。
local MARKS = { '\u{200B}', '⟨JP⟩' }

local function is_jp(cand)
  local c = cand.comment
  if c == nil then return false end
  for _, m in ipairs(MARKS) do
    if c:find(m, 1, true) then return true end
  end
  return false
end

-- ===== 平假名/片假名 一次性模式用的转换 =====
-- 平假名 → 片假名（U+3041–U+3096 加 0x60）
local function to_kata(s)
  local t = {}
  for _, cp in utf8.codes(s) do
    if cp >= 0x3041 and cp <= 0x3096 then cp = cp + 0x60 end
    t[#t + 1] = utf8.char(cp)
  end
  return table.concat(t)
end

-- ===== 罗马字 → 假名 转换器（H/K 模式专用）=====
-- 直接把整串罗马字转成平假名/片假名，不依赖翻译器候选系统。
-- 保证 H/K 模式下候选框始终只有一个候选，按一次空格即上屏整串。
-- Hepburn 罗马字，兼容 si/ti/tu 等变体。
local HIRA_TABLE = {
  a='あ',i='い',u='う',e='え',o='お',
  ka='か',ki='き',ku='く',ke='け',ko='こ',
  sa='さ',shi='し',su='す',se='せ',so='そ',
  ta='た',chi='ち',tsu='つ',te='て',to='と',
  na='な',ni='に',nu='ぬ',ne='ね',no='の',
  ha='は',hi='ひ',fu='ふ',he='へ',ho='ほ',
  ma='ま',mi='み',mu='む',me='め',mo='も',
  ya='や',yu='ゆ',yo='よ',
  ra='ら',ri='り',ru='る',re='れ',ro='ろ',
  wa='わ',wo='を',n='ん',
  ga='が',gi='ぎ',gu='ぐ',ge='げ',go='ご',
  za='ざ',ji='じ',zu='ず',ze='ぜ',zo='ぞ',
  da='だ',de='で',['do']='ど',
  ba='ば',bi='び',bu='ぶ',be='べ',bo='ぼ',
  pa='ぱ',pi='ぴ',pu='ぷ',pe='ぺ',po='ぽ',
  kya='きゃ',kyu='きゅ',kyo='きょ',
  sha='しゃ',shu='しゅ',sho='しょ',
  cha='ちゃ',chu='ちゅ',cho='ちょ',
  nya='にゃ',nyu='にゅ',nyo='にょ',
  hya='ひゃ',hyu='ひゅ',hyo='ひょ',
  mya='みゃ',myu='みゅ',myo='みょ',
  rya='りゃ',ryu='りゅ',ryo='りょ',
  gya='ぎゃ',gyu='ぎゅ',gyo='ぎょ',
  ja='じゃ',ju='じゅ',jo='じょ',
  bya='びゃ',byu='びゅ',byo='びょ',
  pya='ぴゃ',pyu='ぴゅ',pyo='ぴょ',
  -- 变体写法
  si='し',ti='ち',tu='つ',zi='じ',hu='ふ',
  sya='しゃ',syu='しゅ',syo='しょ',
  tya='ちゃ',tyu='ちゅ',tyo='ちょ',
  wi='ゐ',we='ゑ',
}
-- 片假名表由平假名表自动生成（码点 +0x60）
local KATA_TABLE = {}
for _k, _v in pairs(HIRA_TABLE) do KATA_TABLE[_k] = to_kata(_v) end

-- 促音双辅音: kk/ss/tt/pp → っ + 单辅音
local GEMINATE = { k=true, s=true, t=true, p=true }
-- m 在这些辅音前变 ん (Hepburn: b/p/m)
local LABIAL = { b=true, p=true, m=true }

local function is_vowel(c)
  return c=='a' or c=='e' or c=='i' or c=='o' or c=='u'
end

-- 罗马字 → 假名（mode: 'hira' 或 'kata'）
local function romaji_to_kana(s, mode)
  if not s or s == '' then return '' end
  local T = (mode == 'kata') and KATA_TABLE or HIRA_TABLE
  local small = (mode == 'kata') and 'ッ' or 'っ'
  local n_ch = (mode == 'kata') and 'ン' or 'ん'
  local out = {}
  local i = 1
  local len = #s
  while i <= len do
    local c = s:sub(i, i)
    local n1 = s:sub(i+1, i+1)
    local n2 = s:sub(i+2, i+2)
    if GEMINATE[c] and n1 == c then
      -- 促音: kk/ss/tt/pp → っ + 单辅音
      out[#out+1] = small; i = i + 1
    elseif c == 't' and (s:sub(i+1,i+3) == 'cha' or s:sub(i+1,i+3) == 'chu' or s:sub(i+1,i+3) == 'cho') then
      -- tcha/tchu/tcho → っちゃ/っちゅ/っちょ
      out[#out+1] = small; out[#out+1] = T[s:sub(i+1, i+3)]; i = i + 4
    elseif c == 'n' and n1 == 'n' and not is_vowel(n2) and n2 ~= 'y' then
      -- nn（非元音前）→ ん，消费两个 n
      out[#out+1] = n_ch; i = i + 2
    elseif c == 'n' and (n1 == '' or (not is_vowel(n1) and n1 ~= 'y')) then
      -- n 在辅音前或末尾 → ん
      out[#out+1] = n_ch; i = i + 1
    elseif c == 'm' and LABIAL[n1] then
      -- m 在 b/p/m 前 → ん (Hepburn)
      out[#out+1] = n_ch; i = i + 1
    else
      -- 正常匹配: 3字母、2字母、1字母
      local matched = false
      for n = math.min(3, len-i+1), 1, -1 do
        local kana = T[s:sub(i, i+n-1)]
        if kana then out[#out+1] = kana; i = i + n; matched = true; break end
      end
      if not matched then out[#out+1] = c; i = i + 1 end
    end
  end
  return table.concat(out)
end

function M.init(env)
  -- 无需要初始化：语言标记定义在模块常量 MARKS 中。
end

function M.func(input, env)
  local ctx = env.engine.context
  local preedit = ctx.input or ''
  -- 罗马字是否已到一个完整音节结尾：末尾是 a/e/i/o/u/n。
  local jp_tail_ok = romaji_tail_ok(preedit)

  -- ===== 平假名/片假名 一次性模式（Shift+h / Shift+k）=====
  -- 由 kana_mode.lua(processor) 设置 context 属性 kana_mode：
  --   'hira' → 只出平假名；'kata' → 只出片假名。
  -- 规则：用内置罗马字→假名转换器直接转 ctx.input（整串罗马字），
  --       作为唯一候选输出，注释标〔平〕/〔片〕作模式反馈。
  --       不依赖翻译器候选，保证候选框始终只有一个候选，
  --       按一次空格即上屏整串假名。
  -- 该分支直接 return，跳过下面的规则 1。
  local kmode = ctx:get_property('kana_mode') or ''
  if kmode == 'hira' or kmode == 'kata' then
    local romaji = ctx.input or ''
    local kana = romaji_to_kana(romaji, kmode)
    if kana ~= '' then
      local tag = (kmode == 'hira') and '〔平〕' or '〔片〕'
      yield(Candidate('kana', 0, #romaji, kana, tag))
    end
    return
  end

  for cand in input:iter() do
    local jp = is_jp(cand)
    local drop = false

    if jp and not jp_tail_ok then
      -- 罗马字还没打完（末尾是辅音）→ 先不出日文候选，只留中文
      drop = true
    end

    if not drop then yield(cand) end
  end
end

return M
