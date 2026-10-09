#!/usr/bin/env node
/**
 * fetch_ja_words.mjs —— 抓取开源日语数据，生成 ja_words_extra.tsv
 * =====================================================================
 * 用法:
 *     node tools/fetch_ja_words.mjs                # 抓取全部来源并生成 TSV
 *     node tools/fetch_ja_words.mjs --offline      # 只用 _cache/ 里的缓存
 *     node tools/fetch_ja_words.mjs --skip-common  # 跳过 JMdict 常用词
 *     node tools/fetch_ja_words.mjs --skip-names   # 跳过 jmnedict 专有名词
 *     node tools/fetch_ja_words.mjs --skip-mozc    # 跳过 Mozc 词库
 *     node tools/fetch_ja_words.mjs --proxy 127.0.0.1:7897
 *
 * 数据来源（均为开源许可，详见 LICENSE-EDRDG.txt）:
 *   1. JMdict (EDRDG, CC-BY-SA 4.0) —— jmdict-eng-common
 *      约 2.3 万「常用」词条，含 ichi1/news1 等常用度标签与假名读音。
 *   2. Mozc 开源词库 (Google, BSD-3；内含 IPAdic / NAIST, BSD)
 *      约 78 万个「读音 + 多个表记」组合，覆盖大量人名、地名、专有名词。
 *      关键价值：文件按读音排序，同一读音块内的表记顺序即该读音下的
 *      转换优先级——这正是 JMdict 缺的排序信息。
 *   3. jmnedict (EDRDG, CC-BY-SA 4.0) —— 74 万条专有名词（姓/名/地名/作品名）
 *   4. kanjidic2 (EDRDG, CC-BY-SA 4.0) —— 常用漢字音训读，补 JMdict 未收录的单字
 *   5. FrequencyWords 2016 ja_50k (MIT) —— 仅用于判断某个表记是否可信
 *
 * 输出: ja_words_extra.tsv
 *     表记 <TAB> 假名读音 <TAB> 权重(300~999)
 *   300 以下留给占位、1000 以上留给假名音节表与助词，日语词一律不越过 1000，
 *   以维持方案原本的中日同权（中文侧靠 luna_pinyin 自带的高权重取胜）。
 *
 * 关于「词频」: JMdict 只有 common 标签、没有词频，词条间的相对频率是推断的。
 * Mozc / jmnedict 提供的是各自词库内的转换优先级。本脚本把二者叠起来用
 * （Mozc 读音块内的表记顺序 = 该读音下的优选顺序），而不是假装存在统一词频。
 */

import https from 'node:https';
import http from 'node:http';
import tls from 'node:tls';
import zlib from 'node:zlib';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const CACHE = path.join(ROOT, '_cache');
const OUT = path.join(ROOT, 'ja_words_extra.tsv');

const argv = process.argv.slice(2);
const OFFLINE = argv.includes('--offline');
const SKIP_COMMON = argv.includes('--skip-common');
const SKIP_NAMES = argv.includes('--skip-names');
const SKIP_MOZC = argv.includes('--skip-mozc');
const PROXY = (() => {
  const i = argv.indexOf('--proxy');
  return i > -1 ? argv[i + 1] : (process.env.DSH_FETCH_PROXY || null);
})();

const JMDICT_TAG = '3.6.2+20260928191014';
const REL = (name) =>
  `https://github.com/scriptin/jmdict-simplified/releases/download/${encodeURIComponent(JMDICT_TAG)}/${name}`;
const JSDR = (name) =>
  `https://gcore.jsdelivr.net/gh/scriptin/jmdict-simplified@${JMDICT_TAG}/${name}`;

const SOURCES = {
  jmdict: {
    file: 'jmdict-eng-common.json',
    urls: [REL(`jmdict-eng-common-${JMDICT_TAG}.json.tgz`), JSDR(`jmdict-eng-common-${JMDICT_TAG}.json.tgz`)],
    gzip: true, tar: true,
  },
  kanjidic: {
    file: 'kanjidic2-en.json',
    urls: [REL(`kanjidic2-en-${JMDICT_TAG}.json.tgz`), JSDR(`kanjidic2-en-${JMDICT_TAG}.json.tgz`)],
    gzip: true, tar: true,
  },
  jmnedict: {
    file: 'jmnedict.json',
    urls: [REL(`jmnedict-all-${JMDICT_TAG}.json.tgz`), JSDR(`jmnedict-all-${JMDICT_TAG}.json.tgz`)],
    gzip: true, tar: true,
  },
  mozc: {
    file: 'mado-ja-dict.txt',
    urls: [
      'https://github.com/rwpersson/mado-ja-dict-data/releases/download/v1/mado-ja-dict.txt',
      'https://raw.githack.com/rwpersson/mado-ja-dict-data/master/mado-ja-dict.txt',
    ],
    gzip: false, tar: false,
  },
  freq: {
    file: 'ja_50k.txt',
    urls: ['https://gcore.jsdelivr.net/gh/hermitdave/FrequencyWords@master/content/2016/ja/ja_50k.txt'],
    gzip: false, tar: false,
  },
};

const log = (m) => process.stderr.write(m + '\n');

// ---------------------------------------------------------------- 网络
function fetchDirect(url, depth = 0) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const req = https.get({
      hostname: parsed.hostname, port: parsed.port || 443,
      path: parsed.pathname + parsed.search,
      headers: { 'User-Agent': 'rime-xhup-ja/1.0', Accept: '*/*' },
      timeout: 300000,
    }, (res) => {
      if ([301, 302, 303, 307, 308].includes(res.statusCode)) {
        res.resume();
        if (depth > 6) return reject(new Error('too many redirects'));
        return fetchDirect(res.headers.location, depth + 1).then(resolve, reject);
      }
      if (res.statusCode !== 200) { res.resume(); return reject(new Error('HTTP ' + res.statusCode)); }
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => resolve(Buffer.concat(chunks)));
      res.on('error', reject);
    });
    req.on('error', reject);
    req.on('timeout', () => req.destroy(new Error('timeout')));
  });
}

/** 经 HTTP 代理（CONNECT 隧道）下载；返回原始响应体（含可能的 chunked 编码） */
function fetchViaProxy(url, proxy, depth = 0) {
  const [ph, pp] = proxy.split(':');
  const parsed = new URL(url);
  return new Promise((resolve, reject) => {
    const req = http.request({
      host: ph, port: Number(pp), method: 'CONNECT',
      path: `${parsed.hostname}:${parsed.port || 443}`, timeout: 60000,
    });
    req.on('connect', (res, socket) => {
      if (res.statusCode !== 200) return reject(new Error('CONNECT ' + res.statusCode));
      const s = tls.connect({ socket, servername: parsed.hostname }, () => {
        s.write(
          `GET ${parsed.pathname}${parsed.search} HTTP/1.1\r\n` +
          `Host: ${parsed.hostname}\r\nUser-Agent: rime-xhup-ja/1.0\r\n` +
          `Accept: */*\r\nAccept-Encoding: identity\r\nConnection: close\r\n\r\n`
        );
      });
      const chunks = [];
      let header = null;
      let pending = Buffer.alloc(0);
      let bodyStart = 0;
      s.on('data', (d) => {
        if (header === null) {
          pending = Buffer.concat([pending, d]);
          const i = pending.indexOf('\r\n\r\n');
          if (i < 0) return;
          header = pending.subarray(0, i).toString('latin1');
          const status = Number(header.split(' ')[1]);
          if ([301, 302, 303, 307, 308].includes(status)) {
            const loc = /location: *([^\r\n]+)/i.exec(header);
            s.destroy();
            if (!loc) return reject(new Error('redirect without location'));
            if (depth > 6) return reject(new Error('too many redirects'));
            return fetchViaProxy(loc[1].trim(), proxy, depth + 1).then(resolve, reject);
          }
          if (status !== 200) { s.destroy(); return reject(new Error('HTTP ' + status)); }
          const rest = pending.subarray(i + 4);
          pending = Buffer.alloc(0);
          chunks.push(rest);
          return;
        }
        chunks.push(d);
      });
      s.on('end', () => {
        if (header === null) return reject(new Error('empty response'));
        resolve({ head: header, body: Buffer.concat(chunks) });
      });
      s.on('error', reject);
    });
    req.on('error', reject);
    req.on('timeout', () => req.destroy(new Error('proxy timeout')));
    req.end();
  });
}

/** 去掉 chunked 传输编码（非 chunked 时原样返回） */
function dechunk(buf) {
  const firstLine = buf.subarray(0, 16).toString('latin1').split('\r\n')[0];
  if (!/^[0-9a-fA-F]+$/.test(firstLine)) return buf;
  const parts = [];
  let pos = 0;
  while (pos < buf.length) {
    const eol = buf.indexOf('\r\n', pos, 'latin1');
    if (eol < 0) break;
    const size = parseInt(buf.subarray(pos, eol).toString('latin1'), 16);
    if (!Number.isFinite(size) || size === 0) break;
    const start = eol + 2;
    parts.push(buf.subarray(start, start + size));
    pos = start + size + 2;
  }
  return parts.length ? Buffer.concat(parts) : buf;
}

/** tar 包中第一个成员的载荷 */
function tarFirstMember(buf) {
  if (buf.length < 512 || buf.subarray(257, 262).toString('latin1') !== 'ustar') return buf;
  const size = parseInt(buf.subarray(124, 136).toString('latin1').replace(/\0.*$/, '').trim(), 8);
  if (!Number.isFinite(size) || size <= 0) return buf.subarray(512);
  return buf.subarray(512, 512 + size);
}

async function ensure(source) {
  fs.mkdirSync(CACHE, { recursive: true });
  const dest = path.join(CACHE, source.file);
  if (fs.existsSync(dest) && fs.statSync(dest).size > 4096) return dest;
  if (OFFLINE) throw new Error(`离线模式缺少缓存: ${dest}`);
  let lastErr;
  for (const url of source.urls) {
    for (const mode of PROXY ? ['proxy', 'direct'] : ['direct']) {
      try {
        process.stderr.write(`抓取 ${source.file} … `);
        let raw;
        if (mode === 'proxy') {
          const r = await fetchViaProxy(url, PROXY);
          raw = /transfer-encoding: *chunked/i.test(r.head) ? dechunk(r.body) : r.body;
        } else {
          raw = await fetchDirect(url);
        }
        let data = source.gzip ? zlib.gunzipSync(raw) : raw;
        if (source.tar) data = tarFirstMember(data);
        fs.writeFileSync(dest, data);
        process.stderr.write(`${data.length} 字节（${mode}）\n`);
        return dest;
      } catch (e) {
        lastErr = e;
        process.stderr.write(`失败(${e.message})\n`);
      }
    }
  }
  throw lastErr;
}

function readJson(file) {
  const txt = fs.readFileSync(file, 'utf8');
  return JSON.parse(txt.slice(0, txt.lastIndexOf('}') + 1));
}

// ---------------------------------------------------------------- 假名处理
/** 片假名 → 平假名（按码位偏移，避免手写两张表对不齐） */
const KATA_TO_HIRA = (() => {
  const map = new Map();
  for (let cp = 0x30a1; cp <= 0x30f6; cp++) {
    map.set(String.fromCodePoint(cp), String.fromCodePoint(cp - 0x60));
  }
  map.set('ヷ', 'わ'); map.set('ヸ', 'ゐ'); map.set('ヹ', 'ゑ'); map.set('ヺ', 'を');
  map.set('ヴ', 'ゔ');
  return map;
})();
const toHira = (s) => [...s].map((c) => KATA_TO_HIRA.get(c) ?? c).join('');

const KANA_RE = /^[ぁ-ゖァ-ヺー]+$/;
const validReading = (s) => !!s && KANA_RE.test(toHira(s));
const OK_SURFACE = /^[ぁ-ゖァ-ヺー一-鿿々〆ヶ〇]+$/;
const validSurface = (s) => !!s && OK_SURFACE.test(s);

/**
 * 容量控制。日语同音异形极多，全量倒进来必然失控（实测 Mozc+jmnedict
 * 全量 = 123 万条 / 40 MB）。但预算不能用「总条数」截断：
 * Mozc 位次 0 的候选有 51 万，按条数一截就会让后半段读音连首选表记都进不来
 * （实测踩过：こ这个坑）。所以按「保留到哪个位次」来控制。
 */
const MOZC_MAX_RANK = Number(process.env.DSH_MOZC_MAX_RANK ?? 4);
/**
 * 同音表记过多时只取首位的阈值。设得太小会误伤正当写法：
 * さくら 有 17 个同音表记（桜/佐倉/咲良/櫻…），佐倉 排在位次 2，
 * 阈值 12 时它会被整条丢掉（实测踩过）。这里放宽到 40。
 */
const MOZC_CROWDED = Number(process.env.DSH_MOZC_CROWDED ?? 40);
/** 单个读音块内最多考察的表记数 */
const MOZC_MAX_SURFACES = 5;
/** 表记最大长度（更长多是短语碎片或作品名，整串输入一次也没人打） */
const MAX_SURFACE_LEN = 8;
/** jmnedict 专有名词预算（条数） */
/** jmnedict 汉字姓名/地名预算（条数） */
const NAMES_BUDGET = Number(process.env.DSH_NAMES_BUDGET ?? 190000);
/**
 * jmnedict「只有假名表记」的专名预算（西洋人名为主）。
 * 这部分共 7.1 万条，但实测只有 3 条进词频前 5000、1322 条进前 30000，
 * 价值远低于汉字姓名，所以给个小预算、权重也略低（420）。
 */
const KANA_NAMES_BUDGET = Number(process.env.DSH_KANA_NAMES_BUDGET ?? 40000);

/** 平假名 → 片假名（与 KATA_TO_HIRA 互逆） */
const HIRA_TO_KATA = (() => {
  const map = new Map();
  for (let cp = 0x3041; cp <= 0x3096; cp++) {
    map.set(String.fromCodePoint(cp), String.fromCodePoint(cp + 0x60));
  }
  map.set('わ', 'ワ'); map.set('ゐ', 'ヰ'); map.set('ゑ', 'ヱ'); map.set('を', 'ヲ');
  map.set('ゔ', 'ヴ');
  return map;
})();
const toKata = (s) => [...s].map((c) => HIRA_TO_KATA.get(c) ?? c).join('');

const KATA_ONLY_RE = /^[ァ-ヺー]+$/;

/** (表记, 读音) -> { weight, trusted, source, mozcRank } */
const entries = new Map();

function put(surface, reading, w, trusted, source, mrank) {
  if (!validSurface(surface) || !validReading(reading)) return false;
  // 假名文字要跟着表记走：
  //   片假名表记（ゾンビ/ダメ/ジョン）→ 读音用片假名
  //   汉字与平假名表记（俺/なぜ）    → 读音用平假名
  // 否则会生成「ゾンビ + ぞんび」这种日语里不存在的组合
  // （读音栏对不上，等于这个词打不出来）。
  const r2 = KATA_ONLY_RE.test(surface) ? toKata(reading) : toHira(reading);
  const key = surface + '\t' + r2;
  const r = mrank === undefined ? -1 : mrank;
  const prev = entries.get(key);
  if (!prev) {
    entries.set(key, { weight: w, trusted: !!trusted, source, mozcRank: r });
    return true;
  }
  if (trusted) prev.trusted = true;
  if (r >= 0 && (prev.mozcRank < 0 || r < prev.mozcRank)) prev.mozcRank = r;
  if (w > prev.weight) { prev.weight = w; prev.source = source; }
  return false;
}

// ---------------------------------------------------------------- 权重
const TAG_POINTS = {
  ichi1: 46, news1: 34, spec1: 28, gai1: 20, ichi2: 14,
  news2: 11, spec2: 9, gai2: 5, ateji: -4, ik: -6, ok: -6, rK: -10,
};

/** JMdict 词条 → 300~999 */
function scoreOf(entry, opts) {
  const { singleKanji = false } = opts ?? {};
  const tags = new Set();
  for (const k of entry.kanji ?? []) for (const t of k.tags ?? []) tags.add(t);
  for (const k of entry.kana ?? []) for (const t of k.tags ?? []) tags.add(t);
  let pts = 0;
  for (const t of tags) pts += TAG_POINTS[t] ?? 0;
  pts = Math.max(0, Math.min(70, pts));

  const commonKanji = (entry.kanji ?? []).filter((k) => k.common).length;
  const commonKana = (entry.kana ?? []).filter((k) => k.common).length;
  const common = Math.min(8, commonKanji + commonKana) * 5;

  let freq = 0;
  const r = opts?.freqRank ?? 0;
  if (r && r <= 300) freq = 20;
  else if (r && r <= 1000) freq = 15;
  else if (r && r <= 3000) freq = 10;
  else if (r && r <= 8000) freq = 5;

  let raw = 6 + pts + common + freq;
  if (singleKanji) raw *= 0.55;
  return Math.max(300, Math.min(999, 300 + Math.round(raw * 5.3)));
}

/**
 * 同音异形惩罚。
 * 同一读音下常有大量表记（さくら → 桜/佐倉/櫻/偽客…），不处理会并排出现。
 * 判定「可信」的第一依据是 Mozc 位次：Mozc 把该表记排在该读音的首位，
 * 说明它是这个读音下的实际首选（佐倉 さくら 就是这样）；其次是 JMdict 的
 * common 标记或词频前 3000。
 */
function collidedPenalty(nSurfaces, isTrusted) {
  if (isTrusted || nSurfaces <= 1) return 1;
  return Math.max(0.18, 0.5 - 0.07 * (nSurfaces - 2));
}

/** 把 Mozc 位次与 JMdict 的 common 标记合成「可信」判定 */
function applyMozcTrust() {
  // Mozc 位次 0 的条目在入库时已按「该读音下的首选」标为可信，
  // 这里只做统计，便于在日志里核对排序信号确实生效了。
  let rank0 = 0, rank1 = 0, untrustedRank0 = 0;
  for (const [, rec] of entries) {
    if (rec.mozcRank === 0) { rank0 += 1; if (!rec.trusted) untrustedRank0 += 1; }
    else if (rec.mozcRank === 1) rank1 += 1;
  }
  log(`Mozc 排序信号: 位次0 ${rank0} 条（其中未标可信 ${untrustedRank0}）、位次1 ${rank1} 条`);
}

function applyCollisionPenalty(label) {
  const byReading = new Map();
  for (const key of entries.keys()) {
    const i = key.indexOf('\t');
    const reading = key.slice(i + 1);
    if (!byReading.has(reading)) byReading.set(reading, new Set());
    byReading.get(reading).add(key.slice(0, i));
  }
  let n = 0;
  for (const [key, rec] of entries) {
    const i = key.indexOf('\t');
    const nSurf = byReading.get(key.slice(i + 1)).size;
    const factor = collidedPenalty(nSurf, rec.trusted);
    if (factor < 1) { rec.weight = Math.max(300, Math.round(rec.weight * factor)); n += 1; }
  }
  log(`${label}: ${n} 条被下调`);
}

// ---------------------------------------------------------------- 词频表
let freqMap = new Map();
let freqOrder = [];          // 按词频排序的原样表记（含片假名形态）
async function loadFreq() {
  try {
    const p = await ensure(SOURCES.freq);
    let rank = 0;
    for (const line of fs.readFileSync(p, 'utf8').split('\n')) {
      const [w, c] = line.trim().split(/\s+/);
      if (!w || !Number.isFinite(Number(c))) continue;
      rank += 1;
      if (!freqMap.has(w)) { freqMap.set(w, rank); freqOrder.push(w); }
    }
    log(`词频表条目: ${freqMap.size}（判断表记可信度 + 提供片假名形态）`);
  } catch (e) {
    log(`[警告] 词频表不可用(${e.message})`);
  }
}

/**
 * 片假名词补充层。
 *
 * 为什么需要单独一层：Mozc 与 JMdict 对常用外来语**不给片假名表记**——
 * ダメ 在 Mozc 里是「だめ → 駄目」，ジョン 只有「じょん → 鄭」，
 * ドル 是「どる → 取る/弗」。我们的抓取又把读音统一成了平假名，
 * 结果词典里几乎没有片假名层（实测常用片假名词缺 500+ 个，
 * 含 ダメ/バカ/マジ/オレ/クソ 与大批西洋人名）。
 *
 * 词频表恰好保存了**真实文本形态**（ダメ、バカ、ジョン…），
 * 所以这里直接取其中的纯片假名条目当表记，读音就是它自己
 * （日语里片假名表记与读音同形，可放心互推）。
 * 权重只按词频名次给（低于 Mozc 的 470 档），避免抢常用汉字词的位置。
 */
async function loadKatakanaLayer() {
  if (!freqOrder.length) return;
  let added = 0, skipped = 0;
  const TOP = 20000;
  for (let i = 0; i < freqOrder.length && i < TOP; i++) {
    const w = freqOrder[i];
    if (w.length < 2 || w.length > MAX_SURFACE_LEN) { skipped += 1; continue; }
    if (!/^[ァ-ヺー]+$/.test(w)) continue;          // 只要纯片假名
    if (!validReading(w)) { skipped += 1; continue; }
    const rank = i + 1;
    // 名次 → 权重：前 500 名 ≈ 455，5000 名 ≈ 360，20000 名 ≈ 300
    const base = rank <= 500 ? 455 : rank <= 2000 ? 420 : rank <= 5000 ? 380 : 330;
    const w2 = Math.max(300, base - Math.round(Math.log10(rank) * 6));
    const trusted = rank <= 3000;                    // 高频者免同音惩罚
    if (put(w, w, w2, trusted, 'freq-katakana')) added += 1;
  }
  log(`片假名补充层: 新增 ${added} 条（跳过 ${skipped}，总条目 ${entries.size}）`);
}

// ---------------------------------------------------------------- 1. JMdict
async function loadJmdict() {
  if (SKIP_COMMON) return;
  const j = readJson(await ensure(SOURCES.jmdict));
  let nKanji = 0, nKana = 0;
  for (const entry of j.words) {
    const kanji = (entry.kanji ?? []).filter((k) => validSurface(k.text));
    const kana = (entry.kana ?? []).filter((k) => validReading(k.text));
    if (!kana.length) continue;

    let freqRank = 0;
    for (const k of [...kanji, ...kana]) {
      const r = freqMap.get(k.text);
      if (r && (freqRank === 0 || r < freqRank)) freqRank = r;
    }
    const w = scoreOf(entry, { freqRank });
    const surfaces = kanji.length ? kanji : kana;
    for (const s of surfaces) {
      const sRank = freqMap.get(s.text) ?? 0;
      const sTrusted = s.common || (sRank > 0 && sRank <= 3000);
      for (const k of kana) {
        const applies = k.appliesToKanji ?? ['*'];
        if (kanji.length && !applies.includes('*') && !applies.includes(s.text)) continue;
        if (kanji.length) {
          put(s.text, k.text, k.common ? w : Math.round(w * 0.5), sTrusted, 'jmdict');
          nKanji += 1;
        } else {
          put(s.text, k.text, Math.round(w * 0.8), k.common, 'jmdict');
          nKana += 1;
        }
      }
    }
  }
  log(`JMdict 常用词: 总条目 ${entries.size}（汉字 ${nKanji} / 假名 ${nKana}）`);
}

// ---------------------------------------------------------------- 2. Mozc
/** 活用碎片：读音以促音结尾而表记与读音不一致（「ああ言えばこう言っ」之类） */
const FRAGMENT_TAIL = /[っッ]$/;

async function loadMozc() {
  if (SKIP_MOZC) return;
  const p = await ensure(SOURCES.mozc);

  // 读音 → 按文件顺序排列的表记（顺序即该读音下的转换优先级）
  const groups = [];
  let cur = null, surfaces = null;
  const flush = () => { if (cur && surfaces && surfaces.length) groups.push({ r: cur, s: surfaces }); };
  for (const line of fs.readFileSync(p, 'utf8').split('\n')) {
    if (!line) continue;
    const parts = line.split('\t');
    if (parts.length < 2) continue;
    if (parts[0] !== cur) { flush(); cur = parts[0]; surfaces = []; }
    for (let i = 1; i < parts.length; i++) {
      const s = parts[i];
      if (s && !surfaces.includes(s)) surfaces.push(s);
    }
  }
  flush();
  log(`Mozc 读音块: ${groups.length}`);

  // 1) 收集候选。位次是「该读音下的优选顺序」，位次 0 必收；
  //    位次 1/2 只在该读音同音表记不多时才收（同音极多的读音，长尾一定用不上）
  const cands = [];
  let skipped = 0;
  for (const g of groups) {
    if (!validReading(g.r)) { skipped += 1; continue; }
    const distinct = new Set(g.s.map(toHira)).size;
    const maxRank = distinct > MOZC_CROWDED ? 0 : MOZC_MAX_RANK;
    const limit = Math.min(g.s.length, maxRank + 1, MOZC_MAX_SURFACES);
    for (let idx = 0; idx < limit; idx++) {
      const s = g.s[idx];
      if (!validSurface(s) || s.length > MAX_SURFACE_LEN) { skipped += 1; continue; }
      if (FRAGMENT_TAIL.test(g.r) && toHira(s) !== g.r) { skipped += 1; continue; }
      // 同一个读音下把汉字写法排前面（假名写法可由假名变体机制补）
      const kanjiLike = /[一-鿿]/.test(s) ? 0 : 1;
      cands.push({ s, r: g.r, idx, kanjiLike });
    }
  }
  cands.sort((a, b) => a.idx - b.idx || a.kanjiLike - b.kanjiLike
    || a.s.length - b.s.length || a.s.localeCompare(b.s));

  // 2) 入库：位次 → 权重（首位最高，但不越过 520）
  let added = 0;
  for (const c of cands) {
    const ratio = c.idx / Math.max(1, MOZC_MAX_SURFACES - 1);
    const base = 470 - 190 * Math.pow(ratio, 0.7);
    const w = Math.max(300, Math.round(c.s.length === 1 ? base * 0.5 : base));
    // Mozc 位次 0~1 视为「该读音下的实际候选」，标为可信，避免被同音惩罚压到地板
    if (put(c.s, c.r, w, c.idx <= 1, 'mozc', c.idx)) added += 1;
  }
  log(`Mozc: 候选 ${cands.length} 条（保留至位次 ${MOZC_MAX_RANK}，同音>${MOZC_CROWDED} 只取首位），`
    + `新增 ${added} 条（跳过 ${skipped}，总条目 ${entries.size}）`);
}

// ---------------------------------------------------------------- 3. jmnedict
/**
 * jmnedict 专有名词。
 *
 * 分两类、各自独立预算，因为它们的价值不同：
 *   A. 汉字表记的姓名地名（一ノ瀬/佐倉/札幌…）—— 预算 NAMES_BUDGET
 *   B. 只有假名表记的（西洋人名为主：ジョン/マイケル/ピーター…）—— 预算 KANA_NAMES_BUDGET
 * 早先把 B 和 A 混在一起按同一预算截断，结果 B 数量大、把 A 挤掉了。
 * 实测 B 的 7.1 万条里只有 3 条进词频前 5000、1322 条进前 30000，
 * 价值明显低于 A，所以单独给一个小得多的预算。
 */
async function loadNames() {
  if (SKIP_NAMES) return;
  const j = readJson(await ensure(SOURCES.jmnedict));
  const kanjiCands = [];
  const kanaCands = [];
  for (const entry of j.words) {
    const kanji = (entry.kanji ?? []).filter((k) => validSurface(k.text) && k.text.length <= MAX_SURFACE_LEN);
    const kana = (entry.kana ?? []).filter((k) => validReading(k.text));
    if (!kana.length) continue;
    if (kanji.length) {
      for (const s of kanji) {
        for (const k of kana) {
          const rec = entries.get(s.text + '\t' + toHira(k.text));
          kanjiCands.push({ s: s.text, r: k.text, rank: rec && rec.mozcRank >= 0 ? rec.mozcRank : 9 });
        }
      }
    } else {
      // 无汉字表记 → 假名即表记（西洋人名、外来专名）
      for (const k of kana) {
        if (k.text.length < 2 || k.text.length > MAX_SURFACE_LEN) continue;
        const rec = entries.get(k.text + '\t' + toHira(k.text));
        kanaCands.push({ s: k.text, r: k.text, rank: rec && rec.mozcRank >= 0 ? rec.mozcRank : 9 });
      }
    }
  }
  const byValue = (a, b) => a.rank - b.rank || a.s.length - b.s.length || a.s.localeCompare(b.s);
  kanjiCands.sort(byValue);
  kanaCands.sort(byValue);

  let added = 0;
  const apply = (list, budget, weight, label) => {
    const kept = list.slice(0, budget);
    for (const c of kept) {
      // 词频表里能查到的（進撃の巨人、鬼滅、ジョン…）也算可信，
      // 免得它们在同音表记里被一并压到 300
      const r = freqMap.get(c.s);
      const trusted = r > 0 && r <= 3000;
      if (put(c.s, c.r, weight, trusted, 'jmnedict')) added += 1;
    }
    log(`  ${label}: 候选 ${list.length} 条 → 保留 ${kept.length}`);
    return list.length - kept.length;
  };
  const d1 = apply(kanjiCands, NAMES_BUDGET, 430, '汉字姓名地名');
  const d2 = apply(kanaCands, KANA_NAMES_BUDGET, 420, '假名专名（西洋人名等）');
  log(`jmnedict 专有名词: 新增 ${added} 条（丢弃 ${d1 + d2}，总条目 ${entries.size}）`);
}

// ---------------------------------------------------------------- 4. kanjidic2
async function loadKanjidic() {
  const kd = readJson(await ensure(SOURCES.kanjidic));
  const covered = new Set();
  for (const key of entries.keys()) covered.add(key.slice(0, key.indexOf('\t')));
  let nChar = 0, nRead = 0;
  for (const c of kd.characters ?? []) {
    const lit = c.literal;
    if (!validSurface(lit) || covered.has(lit)) continue;
    if (![1, 2, 3, 4, 5, 6, 8].includes(c.misc?.grade)) continue;
    const on = [], kun = [];
    for (const g of c.readingMeaning?.groups ?? []) {
      for (const r of g.readings ?? []) {
        if (r.status) continue;
        if (r.type === 'ja_on' && validReading(r.value)) on.push(toHira(r.value));
        if (r.type === 'ja_kun') {
          const v = r.value.replace(/^[-－]/, '').replace(/[.·].*$/, '');
          if (validReading(v)) kun.push(toHira(v));
        }
      }
    }
    const keep = [...new Set(kun)].slice(0, 1).concat([...new Set(on)].slice(0, 1));
    if (!keep.length) continue;
    nChar += 1;
    const base = scoreOf({ kanji: [{ text: lit, common: true, tags: [] }], kana: [] }, { singleKanji: true });
    keep.forEach((r, i) => { put(lit, r, Math.max(300, base - i * 10), true, 'kanjidic'); nRead += 1; });
  }
  log(`kanjidic2 补齐 JMdict 未收录的常用汉字: ${nChar} 字 / ${nRead} 读音`);
}

// ---------------------------------------------------------------- 主流程
// Mozc 先跑：它提供「同一读音下哪个表记优先」的排序信息，
// 后面的 JMdict / jmnedict 命中同一 (表记, 读音) 时会吃到这个加分，
// 于是「有词频依据的优选表记」能自然浮到前面，而不是靠猜标签。
await loadFreq();
await loadMozc();
applyMozcTrust();
await loadJmdict();
await loadNames();
await loadKanjidic();
await loadKatakanaLayer();
applyCollisionPenalty('同音异形惩罚');

// ---------------------------------------------------------------- 输出
const rows = [...entries.entries()].map(([k, rec]) => {
  const i = k.indexOf('\t');
  return { surface: k.slice(0, i), reading: k.slice(i + 1), w: rec.weight };
});
rows.sort((a, b) => b.w - a.w || a.surface.length - b.surface.length || a.surface.localeCompare(b.surface));

const header =
  '# 日语扩展词库 —— 由 tools/fetch_ja_words.mjs 生成，请勿手工编辑\n' +
  '#\n' +
  '# 数据来源（均为开源数据，分发需保留署名，详见 LICENSE-EDRDG.txt）:\n' +
  '#   JMdict / jmnedict / kanjidic2  © Electronic Dictionary Research and Development Group\n' +
  '#     https://www.edrdg.org/  CC-BY-SA 4.0（经 scriptin/jmdict-simplified 转 JSON）\n' +
  '#   Mozc 开源词库（含 IPAdic / NAIST）  https://github.com/google/mozc  BSD-3-Clause\n' +
  '#     此处使用 rwpersson/mado-ja-dict-data 转换的文本版\n' +
  '#   FrequencyWords  https://github.com/hermitdave/FrequencyWords  MIT\n' +
  '#\n' +
  '# 格式: 表记 <TAB> 假名读音 <TAB> 权重(300~999)\n' +
  `# 词条: ${rows.length}\n`;

fs.writeFileSync(OUT, header + rows.map((r) => `${r.surface}\t${r.reading}\t${r.w}`).join('\n') + '\n', 'utf8');
log(`已写出 ${OUT}: ${rows.length} 词条`);
