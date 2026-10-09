# 小鹤双拼 · 日语罗马字混输 (xhup_ja)

中文用**小鹤双拼**、日语用**罗马字**——在同一个 Rime 方案里直接混输：

> **无需切换模式 · 无需前缀引导 · 无需方案切换**

```
打 nihc        → 你好              打 nihongo          → 日本語
打 vsgo        → 中国              打 watashi          → 私
打 woxlxtxi    → 我想学习          打 konnichiwa       → こんにちは
打 ka          → 1.卡  2.か        打 ganbatte         → 頑張って
打 kyouha      → 今日は            打 arigatougozaimasu → ありがとうございます
```

**日语词库规模**：约 **68.6 万词条**（22 MB），其中
Mozc 开源词库 65.6 万 + JMdict 常用词 + jmnedict 专有名词 + 手工专名表。
覆盖普通词汇、常见姓氏名、地名、ACG 作品名与角色名——这些以前打不出来：

```
打 ichinose      → 一ノ瀬      打 sakuraayane   → 佐倉綾音
打 kimetsu       → 鬼滅        打 jujutsukaisen → 呪術廻戦
打 hatsunemiku   → 初音ミク     打 kamado        → 竈門
```

# 安装

把本目录**全部文件**复制进 Rime 用户目录，重新部署即可：

| 平台 | 前端 | 用户目录 |
|---|---|---|
| Windows | 小狼毫 Weasel | `%APPDATA%\Rime` |
| macOS | 鼠须管 Squirrel | `~/Library/Rime` |
| Linux | fcitx5-rime | `~/.local/share/fcitx5/rime` |
| Linux | ibus-rime | `~/.config/ibus/rime` |

需要复制的内容：

```
xhup_ja.schema.yaml      主方案（小鹤双拼+日语混输）
ja_romaji.schema.yaml    日语棱镜构建方案（依赖，必须一起安装）
ja_romaji.dict.yaml      日语词典（68.6 万条 / 22 MB，自带，无需再生成）
rime_ice.dict.yaml       中文词库索引（完整版自带）
cn_dicts/                中文词库正文 44 MB（完整版自带）
lua/zh_simplify.lua      中文简体化过滤器
TSCharacters.txt         OpenCC 单字表（lua 用，Apache-2.0）
TSPhrases.txt            OpenCC 词组表（lua 用，Apache-2.0）
default.custom.yaml      方案注册（如已有请合并 schema_list）
ja_words_local.tsv       手工专名表（ACG 作品名/艺名，加词改这里）
README.md                本文件
LICENSE-EDRDG.txt        EDRDG / Mozc 数据来源与许可
LICENSE-rime-ice.txt     rime-ice 的 GPL-3.0 许可全文（重建分发必须保留）
README-rime-ice.md       rime-ice 上游说明
tools/                   词库生成/体检脚本（运行时不需要，改词库才用到）
```

> 目录结构要对齐：`cn_dicts/` 要和 `rime_ice.dict.yaml` 放在同一层，
> 因为 `rime_ice.dict.yaml` 里用 `import_tables: cn_dicts/...` 引用它。

## 两个包版本

| 版本 | 大小 | 内含 | 适用 |
|---|---|---|---|
| **完整版** | 26 MB | 本方案 + rime-ice 中文词库（44 MB） | 想一步到位，不用另外下东西 |
| **轻量版** | 12 MB | 只有本方案 | 已经装过 rime-ice，或想自己控制 |

两者的 `ja_romaji.dict.yaml` 完全相同，只是轻量版不含 `cn_dicts/`。

## 依赖

| 依赖 | 完整版 | 轻量版 | 说明 |
|---|---|---|---|
| **rime-ice** | 已含 | **需自装** | 中文词库（`translator/dictionary: rime_ice`） |
| `essay.txt` | 发行版自带 | 发行版自带 | 八股文，影响整句连打 |
| `librime-lua` | 发行版自带 | 发行版自带 | `lua/zh_simplify.lua` 简繁过滤用 |

本方案的中文侧挂 **rime-ice** 词库（约 44 MB / 28 万条），比 Rime 自带的
`luna_pinyin` 词库更大、词频更新。**用轻量版**的话需要自己装，任选其一：

```bash
# 方式一：只取词库（推荐，体积小）
#   从 https://github.com/iDvel/rime-ice 下载后，把 rime_ice.dict.yaml 与
#   整个 cn_dicts/ 目录复制进 Rime 用户目录
# 方式二：整包安装
git clone https://github.com/iDvel/rime-ice
#   然后把 rime_ice.dict.yaml、cn_dicts/ 复制进 Rime 用户目录
```

放好后的目录结构：

```
%APPDATA%\Rime\
├── rime_ice.dict.yaml     ← import_tables 索引
├── cn_dicts\              ← 8105 / base / ext / tencent / others
├── xhup_ja.schema.yaml
└── ja_romaji.dict.yaml
```

**没装 rime-ice 会怎样**：中文侧找不到词库，只出日语候选。
若想用回发行版自带的轻量词库，把 `xhup_ja.schema.yaml` 里的
`dictionary: rime_ice` 改回 `luna_pinyin` 即可（中文候选会明显变少）。

**首次部署较慢**：rime-ice 要编译约 58 MB 的 `rime_ice.table.bin`，
视机器可能要几分钟，之后不再重复编译。

重新部署：小狼毫/鼠须管点托盘菜单「重新部署」；fcitx5-rime 执行 `rime_deployer --build` 或重启。

# 用法

## 中文（小鹤双拼）

键位与 [rime-ice](https://github.com/iDvel/rime-ice) 小鹤双拼完全一致：
zh→`v`、ch→`i`、sh→`u`、韵母各键见小鹤官方。例：`nihc`=你好、`vsgo`=中国、`vv`=追。

### 单键输入：`あいうえおん` 优先，缩写噪音被清掉

单键（`a`/`i`/`u`/`e`/`o`/`n`）现在第一页就是对应的假名：

```
a → 1.あ 2.ア 3.啊 4.按 …      i → 1.い 2.イ 3.成 …      u → 1.う 2.ウ 3.是 …
e → 1.え 2.エ 3.嗯 …           o → 1.お 2.オ 3.哦 …      n → 1.ん 2.ン 3.那 …
w → 1.我 2.为 3.无 …            k → 1.看 2.开 3.口 …      d → 1.的 2.到 3.大 …
```

中文侧的单键条目来自 rime-ice 词库本身，本方案不额外提供。

> **历史坑（已修）**：本方案曾在日文词库里塞过 26 条**中文**单键条目
> （`w`=我、`u`=是、`f`=发、`m`=吗…）。后果是日语翻译器把它们当音节节点，
> 打入 `ufm` 被切成 `u+f+m`，组出一条带日语注释的「是发吗」并排在首位。
> **候选层过滤器拦不住**，因为问题出在「切成音节」那一步就成立了。
> 现在生成器有硬约束：**任何编码长度 ≤1 的词条一律不入库**。

### 缩写噪音的处理（`kana_only` 模式）

简拼规则会给日语音节也生成单键缩写码（`wa`→`w`、`kya`→`k`），
于是单键会冒出 `は`/`きゃ` 这类并非"单键假名"的候选。`lua/jp_lang.lua` 用
**注释里的罗马字长度**区分：

| 候选 | 注释 | 单键时 |
|---|---|---|
| `あ` | `a`（1 字符） | 保留 |
| `は` | `ha`（缩写自 ha） | 丢掉 |
| `きゃ` | `kya` | 丢掉 |

模式开关在 `lua/jp_lang.lua` 顶部：

```lua
local SINGLE_KEY_MODE = 'kana_only'   -- 'keep' 全留 / 'kana_only' 只留真单键假名 / 'drop' 全丢
```

### 为什么不能删掉 `あ`/`え`/`い`/`ん`/`お`/`う`

它们也是单字母码（`あ`=a、`ん`=n），但**不能删**——它们是音节表的成员，
而 `ingest()` 用音节表做校验：删掉 `a`/`n` 会让所有含这些音节的词
（`na ze`、`a ri ga to u`…）整批判为非法。

实测删掉的后果：**词条从 726,013 掉到 220,088**（丢 51 万条，属自伤）。
现在它们的权重是 **1000**（与普通假名同级，片假名同伴 960），
所以能正常出现在第一页。

### 音节级简拼（词尾没打完也出整词）

每个音节**额外**生成一个「取首字母」的短码，于是不打完最后一个音节也能命中整词：

```
什么 = ufme  →  简拼 ufm      （u=sh、f=en、m=me 的首字母）
你好 = nihc  →  简拼 nh
中国 = vsgo  →  简拼 vg
```

实测（librime 引擎，非推测）：

```
输入 ufm   →  1.什么  2.神秘  3.申明  4.审美  5.神庙  6.神明
输入 ufme  →  1.什么  2.是发め …
输入 nihongo → 1.日本語  2.にほんご …
```

只影响「词尾没打完」这类输入，完整码行为不变。

**为什么需要单独加**：rime-ice 的小鹤方案里这条规则是**注释掉的**，原注释写着
「首字母简拼，开启后会导致 3 个字母时 `kj'x` 变成 `k'jx` 的问题」。所以本方案
同时补了 `speller/initials`（限定起头键）来避免那个副作用。
如果你依赖 `kj'x` 这种手动分隔写法，把 `xhup_ja.schema.yaml` 里
`- abbrev/^(.).+$/$1/` 这行注释掉即可关闭简拼。

### 单键表与简拼的相互作用（实测记录）

这两个特性会互相影响，改之前必须知道：

| 配置 | `ufm` 首位 | 单键 `w` | `ufme` 第 2 项 |
|---|---|---|---|
| 单键表 on + 简拼 on（默认） | 什么 | 我 | 是发め |
| 单键表 on + 简拼 **off** | **是发你** | 我 | — |
| 单键表 **off** + 简拼 on | 什么 | は | 神 |
| 单键表 on + 简拼 on + 中文组句 off | 什么 | 我 | 是发め |

三条结论：

1. **`ufm` → 什么 完全由简拼规则提供**，与单键表无关。
   关掉简拼立刻退回「是发你」——这正是没有简拼时的原始症状。
2. **单键出假名（`w`→は、`d`→だ）也来自简拼规则**，不是单键表。
   简拼对每个音节取首字母，于是 `wa`→`w`、`da`→`d`、`ha`→`h`，
   单键自然就命中了这些缩写码。**删单键表不能消除它**。
3. **单键表只负责一件事**：单键优先出中文（`w`→我）。删掉它，单键就交给
   简拼生成的假名缩写码。`ufme` 的第 2 项会从「是发め」变成「神」。

所以「不要单键出假名」和「`ufm` 出什么」**在同一个 speller algebra 下互斥**：
简拼是中国缩写的实现方式，但它对日语侧同样生效（librime 的 algebra 是按音节统一处理的，
无法只对某个 translator 生效）。想两者都要，需要另写 Lua 过滤器在候选层做区分。

关闭简拼：把 `xhup_ja.schema.yaml` 里 `- abbrev/^(.)..$/$1/` 那行注释掉。
不写单键表：`python3 tools/gen_ja_dict.py --no-shengmu -o ja_romaji.dict.yaml`。

### 语言隔离过滤器（lua/jp_lang.lua）

（本节保留作为候选层的第二道防线。经删净单键词条后，主要问题已由生成器硬约束解决，过滤器用于兜住两键以上的中日混排。）
**这不是简拼造成的**——关掉简拼一样存在，根因是日文词典里每个假名都有罗马字编码
（`か`=ka、`だ`=da、`きゃ`=kya），首字母正好等于单键，于是单键命中了它们。
speller/algebra 是按音节统一处理的，**无法只对某个 translator 生效**，
所以只能在候选层判定语言。

做法：`comment_format` 把语言标记换成 **U+200B 零宽字符**，
两边的 `⟨` `⟩` 保留可见，所以注释显示成 `⟨a sa⟩`：

```yaml
comment_format:
  - xform/^/⟨\u200b/     # 显示 ⟨，零宽字符供 lua 判语言
  - xform/$/⟩/
```

> 走过的弯路：一开始把整个 `⟨JP⟩` 换成零宽字符，结果**开括号也被藏掉了**，
> 显示成 `a sa⟩`（缺 `⟨`）。只让「JP」这两个字母不可见才对。
>
> 另一个坑：`lua/jp_lang.lua` 的 `romaji_of()` 当时只剥标记不剥括号，
> `⟨a⟩` 剥完是 `a⟩`（长度 2），被 `kana_only` 误判成缩写丢掉——单键假名就这样消失过。
> 现在它会剥掉标记 **和** 两边括号。

想改行为，编辑 `lua/jp_lang.lua` 顶部两个开关：

```lua
local KEEP_SINGLE_KEY_JP = false   -- 单键是否保留日语候选
local KEEP_KANA_MIXED    = false   -- 假名输入是否保留中文候选
```

注意：`⟨JP⟩` 标记同时被 `lua/zh_simplify.lua` 用来跳过简繁转换
（否则 東京→东京）。**改 `comment_format` 必须同时改这两个 lua。**

## 日语（Hepburn 罗马字）

- 假名全集可直接打：`ka`→か、`kya`→きゃ、`sha`→しゃ、`tsu`→つ
- **罗马字容错**：`si`=し、`ti`=ち、`tu`=つ、`hu`=ふ、`zi`=じ、`jya/zya`=じゃ
- **促音**双写辅音：`ganbatte`→頑張って、`kitte`→切手
- **长音**按罗马字写：`toukyou`→東京、`koohii`→コーヒー（`-` 也支持 `n/nn`、`ha/he/wo` 助词按 `wa/e/o` 打：`konnichiwa`）
- **ん** 只用 `n`（或 `nn`），**不支持 `m`**：请打 `shinbun` 而不是 `shimbun`
- 小假名：`la/xa`→ぁ、`ltu/xtu`→っ、`lya`→ゃ
- 汉字转换：68.6 万词条覆盖日常/商务/人名/ACG 用词；未收录词自动退回假名
- 候选带 `〔罗马字〕` 注释的都是日语候选

常用词效果示例：

```
nihongo   → 日本語      toukyou  → 東京        gakkou  → 学校
tabemasu  → 食べます    oishii   → 美味しい     daijoubu → 大丈夫
densha    → 電車        kitte    → 切手         koohii  → コーヒー
sakura    → 桜          inu      → 犬           neko    → 猫
ichinose  → 一ノ瀬      ayane    → 綾音         kimetsu → 鬼滅
```

## 标点（中日两用）

> **中文模式下，常用标点「一步到位」直接上屏全角，不需要再按空格确认。**
>
> | 按键 | 上屏 | 按键 | 上屏 | 按键 | 上屏 |
> |---|---|---|---|---|---|
> | `,` | `，` | `.` | `。`＊ | `!` | `！` |
> | `?` | `？` | `;` | `；` | `:` | `：` |
> | `(` | `（` | `)` | `）` | `<` | `《` |
> | `>` | `》` | `[` | `「` | `]` | `」` |
> | `{` | `『` | `}` | `』` | `^` | `……` |
> | `_` | `——` | `$` | `￥` | `\` | `、` |
> | `/` | `・` | `'` | `‘`/`’`＊ | `"` | `“`/`”`＊ |
>
> ＊`.` 仅在「紧接数字」时作小数点（如 `3.14`），其余一律 `。`；
> ＊`'` `"` 是成对引号，连续按会在「左 / 右」之间轮换。
>
> 其余符号（`@ # % & * - + = ~ |` 及空格）保持半角。
> 需要输入真正的半角 / 英文标点时：按 `Shift` 切到英文（`Ａ`）模式，或打开 `ascii_punct` 开关。

实现：由 `lua/punct_priority.lua`（标点优先处理器，排在 `punctuator` 之前）直接 `commit` 全角结果，
配合 schema 里的 `punctuator/digit_separators: ""`。起因是 librime 1.13+ 的「数字分隔符」特性
把 `,` `.` `:` `'` 半角化，且标点经「分段→翻译→过滤器」链路后可能滞留在输入框（只能按空格上屏半角）；
本处理器抢在 `punctuator` 之前直接上屏，彻底绕开这两个坑。

## 开关

- `zh_simp`：中文简/繁输出（默认简；Ctrl+` 进入方案选单后以热键切换）
- `Shift`：中/英（临时大写直接上屏字母，Rime 默认行为）

# 调参

## 常用开关

| 位置 | 作用 |
|---|---|
| `japanese/initial_quality` | 日语整体权重（调大→日语候选更靠前） |
| `translator/enable_completion` | 中文前缀补全（默认关，防生僻字噪音） |
| `japanese/enable_user_dict` | 日语学习词库 |
| `menu/page_size` | 候选页大小 |

## 日语词库怎么来的

`ja_romaji.dict.yaml` 由四层合成，**由脚本生成，请勿手工编辑**：

| 层 | 规模 | 权重 | 来源 |
|---|---|---|---|
| 假名音节表 | 461 | 1000 / 拗音 1200 / 助词 1200 | `tools/gen_ja_dict.py` 内置 |
| 精选词 | 776 | 300~999（手工调过，**锁定**） | `gen_ja_dict.py` 的 `WORDS` |
| 手工专名 | 32 | 450~600（**锁定**） | `ja_words_local.tsv` |
| 批量词库 | 732752 | 300~470 | `ja_words_extra.tsv`（Mozc + JMdict + jmnedict + kanjidic2 + 片假名层） |

词典合计 **726110 条 / 22.2 MB**，唯一编码 52.5 万个。

批量词库的数据源与各自作用：

| 来源 | 贡献 | 许可 |
|---|---|---|
| **Mozc 开源词库** | 65.6 万条，含人名/地名/专名；**读音块内的表记顺序 = 该读音下的转换优先级** | BSD-3（Google / IPAdic） |
| **JMdict** `-common` | 2.3 万常用词，带 ichi1/news1 等常用度标签 | CC-BY-SA 4.0 |
| **jmnedict** | 74 万专有名词（姓/名/地名/作品名） | CC-BY-SA 4.0 |
| **kanjidic2** | 常用漢字音训读，补 JMdict 未收录的单字 | CC-BY-SA 4.0 |
| **FrequencyWords** | ①判断表记是否可信；②**提供片假名层**（见下） | MIT |

详见 [LICENSE-EDRDG.txt](LICENSE-EDRDG.txt)。

### 片假名层（重要）

Mozc 与 JMdict 对常用外来语**几乎不给片假名表记**：`ダメ` 在 Mozc 里是
「だめ → 駄目」、`ジョン` 只有「じょん → 鄭」、`ドル` 是「どる → 取る/弗」。
于是词典里几乎没有片假名层——实测常用片假名词缺 **500+ 个**
（`ダメ`/`バカ`/`マジ`/`オレ`/`クソ` 以及大批西洋人名 `ジョン`/`ピーター`/`マイケル`…）。

补法：词频表保存的是**真实文本形态**（`ダメ`、`バカ`、`ゾンビ`），
直接取其中的纯片假名条目当表记，读音即表记本身，权重按词频名次给（≤455）。
另外修了一个假名文字不匹配的问题：**片假名表记必须配片假名读音**
（`ゾンビ` + `ゾンビ`，而非 `ゾンビ` + `ぞんび`），否则读音栏对不上、这个词打不出来。

修正后覆盖提升（用第三方词频表当裁判，见下）：

| 词频区间 | 修正前 | 修正后 |
|---|---|---|
| 前 1000 | 93.4% | **97.7%** |
| 1001–3000 | 84.7% | **98.1%** |
| 3001–10000 | 72.5% | **96.2%** |

## 与市面日文 Rime 词库的对比

用户提出过「自己拼的词典会不会覆盖不足或臃肿」，这里给出可复现的答案。
对照对象选 **[gkovacs/rime-japanese](https://github.com/gkovacs/rime-japanese)**
（★404，最主流的 Rime 日文方案），它同样是 **Mozc + JMdict** 双词典，
数据源与本项目高度重合，可比性最好：

| | 本项目 | gkovacs |
|---|---|---|
| 条目 | 690,075 | 1,364,459（mozc 1,098,785 + jmdict 265,674）|
| 数据版本 | Mozc/JMdict **2026-09** | Mozc **2018-04**、JMdict **2018-07**、`version: v0.2-20180411` |
| 表记长度 ≥9 字 | 459 (0.1%) | 127,771 (**10.3%**) |
| 纯片假名表记 | 16,333 | — |

**它条目更多，但多出来的部分是噪音**。抽查「对方有我们没有」的 2 万条样本：

```
通过音节校验（即格式上合法）  77.4%
表记超过 8 字                 9.8%
表记含拉丁/数字/半角符号       8.5%
读音不是合法罗马字             4.2%
```

通过校验的那 77.4% 看样本就露馅了——`カバーに`、`トレーに`、`ボールと`、
`お勧めブランド`、`くるっと`、`明日ぱる`、`愛ハート`、`アイアンと`。
这是**把网页语料切碎后按片段入库**的产物，不是词表。

所以判断标准不能是「谁条目多」，而是**用双方都没参与构建的第三方词频表测覆盖**：

```bash
python3 tools/bench_coverage.py     # 用 FrequencyWords ja_50k 当裁判
python3 tools/compare_dicts.py      # 条目级/表记级重合、长度分布、同音密度
python3 tools/judge_missing.py      # 判定对方独有条目是缺口还是噪音
```

测试结果（`ja_50k` 前 3 万个高频词，已剔除单字与纯平假名碎片）：

| 词频区间 | 本项目 | gkovacs |
|---|---|---|
| 前 1000 | 97.7% | 98.9% |
| 1001–3000 | 98.1% | 98.5% |
| 3001–10000 | 96.2% | 96.1% |
| 10001–30000 | 73.3% | 86.0% |
| 合计 | 63.5% | 70.4% |

**结论**：前 1 万高频词双方打平（本项目在 3001–10000 档还略高），
说明覆盖面没有实质差距；差距全在 1 万–3 万名的长尾，
而那一段的「缺词」主要是**活用形被切碎的词干**（`分か`、`起こ`、`変わ`、`見つか`
——这些不是词典条目）以及低频专名。用不到三分之二的体积换掉大量噪音，是划算的。

反过来说，本项目的短板也正是长尾低频专名。如果你发现某个具体词打不出来，
两个办法：加进 `ja_words_local.tsv`，或调大
`tools/fetch_ja_words.mjs` 里的 `NAMES_BUDGET` / `MOZC_MAX_RANK` 重新生成。

## 专名预算已饱和（别再加了）

`tools/budget_gain.py` 用同一套裁判词表量化了「放宽专名预算」的边际收益：

```
   汉字预算   假名预算   新增表记   裁判词命中   增量
  190,000    40,000   157,540    24,302    +700
  400,000    80,000   355,292    24,302    +700   ← 多塞 19.8 万条，命中数不变
  657,694    75,294   600,632    24,302    +700   ← 全收也没有增量
```

**结论：专名预算在 190k/40k 时已经饱和。**
调到 400k 只会让词典 +6.5 MB、多出 20 万条不会被用到的长尾名字，
常用词覆盖**零提升**。所以不要去设 `DSH_NAMES_BUDGET=400000`。

### 那 Mozc UT 系辞书（jawiki / neologd / 人名 / 地名）值得加吗

[utuhiro78/merge-ut-dictionaries](https://github.com/utuhiro78/merge-ut-dictionaries) 不提供现成词库，
它是构建脚本（本地合并 jawiki/neologd/人名/地名/SudachiDict 再编译 Mozc），
且自标 **License: Mixed**——分发的许可麻烦。

它的数据源可以单独取来评估。实测两个与专名最相关的：

```
mozcdic-ut-personal-names  84,133 条 → 词频前 30000 中只补到 46 条
mozcdic-ut-place-names    166,136 条 → 词频前 30000 中只补到  2 条
```

即 **25 万条人名地名里只有 48 条落在常用范围**，其余全是长尾。
理由和上面的预算结论是同一条：常用专名早已被词频表和 Mozc 覆盖，
剩下的都是"输入法里存着但一辈子不会打"的名字。
（评估脚本：`tools/assess_ut.py`，原始数据从对应仓库的 `*.txt.bz2` 取。）

所以本项目的短板（长尾低频专名）**不是加数据能解决的**——
它由「真实使用频率分布」决定。真要补某个具体词，用 `ja_words_local.tsv` 最省事。

## 关于「词频」的实话

你听到的说法是对的，但方向要拆开看：

- **JMdict 没有词频**，只有 `ichi1/news1/spec1/gai1` 这种 4 档粗标签。
  所以纯 JMdict 方案里，同档词之间的先后是**推断**出来的，不是实测的。
- **Mozc 提供的是「同一读音下哪个表记优先」**，这是转换优先级的排序信息，
  不是词频。本方案现在就用它当排序依据——`さくら` 下 桜 在 佐倉 之前、
  `たのしい` 下 楽しい 在 娯しい 之前，都来自 Mozc 的位次。
- **但 Mozc 开源版 ≠ Google 日语输入法**：它基于 IPAdic，**不含** Google 的
  Web 语料大词库，所以作品名、艺名这类流行专名它也没有（`佐倉綾音`、`花澤香菜` 都不收录）。
  这部分只能手工补，就是 `ja_words_local.tsv` 的用途。
- 结论：**换 Mozc 是对的，但不能只换**。JMdict 补常用度标签、jmnedict 补姓名、
  Mozc 补优选顺序、手工表补流行专名，四者叠起来才够用。

## 单键「只打声母」是怎么做的（以及为什么这么做）

这里有个绕不开的冲突：**日语里 `a/i/u/e/o/n` 本身就是单键编码**（あいうえおん），
而中文侧原本没有单键条目，所以只按一个键时候选**全是日语**。

要按你要的效果（打中文单键出中文、打日文 `ra` 仍出 `ら`），只能两边同时调：

| 改动 | 位置 | 效果 |
|---|---|---|
| 新增 26 条单键条目，权重 1140~1500 | `gen_ja_dict.py` 的 `SHENG_MU` | 单键优先出中文高频字 |
| 日语单键假名权重 1000 → 520 | `SINGLE_KANA_WEIGHT` | 让位给中文，但仍能打出（排后面） |
| 两键以上假名权重不动 | —— | `ra`/`ka`/`shi`/`no` 完全不受影响 |

两点说明：

- 这些单键条目**放在 `ja_romaji.dict.yaml` 里**，只是为了部署时少一个文件；
  它们是中文缩写，不是日语词。文件头部有醒目注释。
- `n` 比较特殊：中文侧 `你`(1450) 在前，日语 `ん`(1200) 紧随其后，
  都不受影响（`ん` 也可以按 `nn` 打）。

想改成「日语单键优先」或干脆不要单键表：调 `SINGLE_KANA_WEIGHT`，
或把 `SHENG_MU` 清空后重新生成。

## 加日语词 / 调频

**加专名（最常用）**：编辑 `ja_words_local.tsv`，一行一条
`表记 <TAB> 假名读音 <TAB> 权重`（权重可省略，默认 600），然后：

```bash
python3 tools/gen_ja_dict.py -o ja_romaji.dict.yaml
```

**手工补普通词**：编辑 `tools/gen_ja_dict.py` 的 `WORDS` 列表。
它的权重与手工专名一样是**锁定值**，批量词库不会顶掉。

**刷新批量词库**（上游更新后，需要 Node 18+）：

```bash
node tools/fetch_ja_words.mjs        # 重新抓取 → ja_words_extra.tsv
python3 tools/gen_ja_dict.py -o ja_romaji.dict.yaml
```

`gen_ja_dict.py` 常用参数：

```bash
python3 tools/gen_ja_dict.py --extra none        # 只用精选词+手工专名（约 1750 条）
python3 tools/gen_ja_dict.py --variant-min 0     # 给所有词生成假名变体（体积翻倍）
python3 tools/gen_ja_dict.py --extra-cap 340     # 批量词库压得更低（中文更优先）
```

罗马字编码由假名读数**自动推导**（含拗音/促音/长音），无需手写；
读音无法转码、或音节不在音节表内的词条会被自动丢弃并计数。

## 体检：中日会不会抢位

```bash
python3 tools/check_overlap.py          # 需要本机装有 rime-ice 词库（cn_dicts/）
python3 tools/compare_short.py          # 短码逐键对比：中日谁排在前面
python3 tools/consult.py nihongo kitte  # 离线查某个输入会出哪些日语候选
python3 tools/rime_probe.py --user-dir ../rime-test-user ufm   # 真实引擎实测候选
```

### 最重要：`rime_probe.py`（真实 librime 引擎）

`check_overlap.py` / `compare_short.py` / `consult.py` 都是**我自己的近似实现**
（例如不模拟 algebra 派生、不模拟整句组句），只能作参考。
要确认某个输入到底出什么，用 `rime_probe.py`——它加载小狼毫自带的 `rime.dll`，
在**指定用户目录**上部署后模拟按键并打印真实候选：

```bash
# 1) 先在工作区建一份副本（别指向正在用的 %APPDATA%\Rime，两边同时部署会互相干扰）
#    需要: 各 schema、ja_romaji.dict.yaml、rime_ice.dict.yaml、cn_dicts/、lua/、TS*.txt
# 2) 实测
python3 tools/rime_probe.py --user-dir ../rime-test-user ufm ufme nihongo
```

输出示例：

```
=== 输入 'ufm'  ===
  preedit: 'shen m'
  候选 6 个:
    *1. 什么
     2. 神秘
```

注意：`rime.dll` 上的 `RimeGetCurrentSchema` 调用即崩（签名/缓冲区约定不符），
脚本已跳过该调用，不影响结果。

`check_overlap.py` 把两边编码都算出来做碰撞分析。当前版本（72.6 万条，
中文侧用的是**本机 rime-ice 全量 44 MB 词库**）：

```
日语: 685791 条 -> 唯一编码 493350
中文: 解析 281320 条（权重>=500）-> 唯一编码 222648
编码重叠: 902 个
日语权重大于中文最高权重者: 0 个
  → 扩了 11 倍词量，中文候选位置一个都没被抢
```

`compare_short.py` 专门看短码上的中日次序，改完单键表后拿它复核：

```bash
python3 tools/compare_short.py w l d b n a i u e o   # 单键应出中文
python3 tools/compare_short.py ra ri ka shi no       # 两键假名不该被影响
```

`consult.py` 用于改词后确认某个输入的首选是否正确，不必反复重新部署。
（它不模拟 schema 的 algebra 派生，所以 `nn`→ん、`konnichiwa`→こんにちは
这类靠派生才成立的输入查不出来，属正常。）

## 中文词库（已固定为 rime-ice）

`xhup_ja.schema.yaml` 里是 `translator/dictionary: rime_ice`，即本方案默认使用
[rime-ice](https://github.com/iDvel/rime-ice) 词库，安装方法见上面「依赖」一节。

说明几点：

- **简体由本方案的 `lua/zh_simplify.lua` 处理**，不依赖 rime-ice 的 simplifier，
  所以只装词库（`rime_ice.dict.yaml` + `cn_dicts/`）就够了，不必装它的 schema。
- rime-ice 的 `essay.txt` 会让整句连打更准，装了更好，可选。
- 想换回发行版自带的轻量词库：把 `dictionary:` 改成 `luna_pinyin` 重新部署即可。

# 技术原理

1. **双翻译器竞争**：`script_translator`（中文·小鹤 algebra）与 `script_translator@japanese`（日语·纯罗马字）同时解析同一输入串，按权重竞争候选。
2. **独立棱镜**：librime 部署时只编译各方案的主 `translator`；日语翻译器的 prism 由依赖方案 `ja_romaji` 以纯罗马字规则预构建，不经过小鹤 algebra（已读 librime 1.13 源码验证）。
3. **天然键位分离**：小鹤把 zh/ch/sh 压缩为单键，`shi/chi/tsu/kya/cha` 等串在中文侧无解析路径，天然让位日语。
4. **翻译器顺序决胜**：句子候选 quality 恒为 0，同覆盖长度时按注册顺序决胜，故日语翻译器置于中文之前（`kyouha`→今日は 压过 困偶哈）。
5. **简体化隔离**：标准 simplifier 会把日语汉字一起简化（東京→东京），本方案改用 `lua/zh_simplify.lua` 只转换中文候选，日语候选按 `〔〕` 注释标记跳过。

# 词库扩充踩过的坑（已处理）

扩词不是「把词库倒进去」那么简单。以下每条都是实测踩出来后修的，
写在这里是因为它们对最终手感的影响最大：

1. **同音异形**：同一读音常有多个表记，`さくら` 既有 桜 也有 **偽客**，
   `たのしい` 既有 楽しい 也有 **娯しい**。若一视同仁，生僻写法会跟常用词并排。
   现在按「Mozc 位次是否为 0/1、JMdict 是否标 common、词频是否前 3000」判定可信度，
   不可信的打折（本轮 7 万条被下调）。
2. **冷门读音**：`七` 有 しち/なな，也有 なあ/ひち；读音同样按 common 标记减半。
3. **精选词不许被顶掉**：精选词权重是手工调过的（`ない`=800、`から`=800、
   `七`=400 这类「低分但高频」），所以批量词库整体压在 450 以下，
   精选词与手工专名以**锁定值**写入，任何批量词都不得覆盖。
4. **不能用「总条数」截断预算**：Mozc 位次 0 的候选有 49 万，
   按条数一截就会让后半段读音**连首选表记都进不来**。改为按「保留到哪个位次」控制。
5. **同音表记过多时不能一刀切**：`さくら` 有 17 个同音表记（桜/佐倉/咲良/櫻…），
   只取首位会把排在第 3 的 **佐倉** 整条丢掉。阈值现在放到 40。
6. **假名变体要限量**：给 68 万条都生成假名变体，词典会从 22 MB 涨到 42 MB。
   现在只给高频词生成（`--variant-min`），但精选词的变体一律保留——
   否则 `がんばって`(280) 这类手调过的低分高频词会被阈值误伤。

# 已知取舍

- 两字母输入中日共享码表：`ka`首选卡（中文优先），`か`居次位。若想日语优先，调大 `japanese/initial_quality`。
- `si`/`tu` 等与常用汉字同形的罗马字（死/图）首选中文。
- `nn` 首选「鸟」（小鹤 n+iao），`ん` 居第三；长句内 ん 由词组匹配覆盖。
- 单字输入（如 `ka`→か）仍以假名音节表为准；词条主要改善**多音节词**。
- **词典 22 MB / 68.6 万条，首次部署要多花几秒**编译 `ja_romaji.table.bin`；
  内存占用也随之上升。嫌重可以 `gen_ja_dict.py --extra none` 回到 1750 词的轻量版。
- 词条多必然带来长尾候选：生僻写法已被压到 300 权重，排在假名之后；
  但同码候选总数确实变多了（如 `sakura` 有 6 个），靠权重排序区分。
- 假名变体只为高频词生成（`--variant-min`，默认 470）：`がんばって` 能直接打，
  但 `いちのせ` 这类专名的假名写法不在词库里，用汉字打即可。

# 致谢

- [rime-ice](https://github.com/iDvel/rime-ice)（Dvel）——小鹤双拼 algebra 与调权思路
- [swiftol/Rime_Config](https://github.com/swiftol/Rime_Config)——独立 prism 混输架构参考
- [iamcheyan/rime_sbzrjp](https://github.com/iamcheyan/rime_sbzrjp)（jaroomaji）——罗马字容错规则
- [snomiao/rime-snomiao](https://github.com/snomiao/rime-snomiao)——多语混输思路
- [Mozc](https://github.com/google/mozc)（Google，BSD-3）——词条与读音内优选顺序；
  文本版来自 [rwpersson/mado-ja-dict-data](https://github.com/rwpersson/mado-ja-dict-data)
- [JMdict / jmnedict / kanjidic2](https://www.edrdg.org/)（EDRDG，CC-BY-SA 4.0）——常用词、专有名词与读音
- [scriptin/jmdict-simplified](https://github.com/scriptin/jmdict-simplified)——EDRDG 数据的 JSON 版
- [FrequencyWords](https://github.com/hermitdave/FrequencyWords)（MIT）——表记可信度判据
- [OpenCC](https://github.com/BYVoid/OpenCC)——简繁转换数据（Apache-2.0）
- Rime / librime 全体开发者

方案在 librime 1.13.1 上经部署与逐键测试验证。
