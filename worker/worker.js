// Wortkarten 反馈中转：App 里匿名提交的纠错 / 意见 → snipperxx/wortkarten 的 GitHub Issue。
// 密钥 GITHUB_TOKEN 只有这个仓库的 Issues 读写权限（wrangler secret put GITHUB_TOKEN）。
// 另有考题库的写作 / 口语提交：POST /exam/submit 存进 KV（sub:<id>），Claude 批改后写 grade:<id>，App 用 GET /exam/grades?ids= 取回。
const REPO = "snipperxx/wortkarten";
const ORIGINS = ["https://snipperxx.github.io", "http://127.0.0.1:8766", "http://localhost:8766"];   // 后两个是本机预览测试用
const TYPES = {
  "释义不对": "释义", "例句或翻译有问题": "例句", "冠词/复数/变位不对": "词形",
  "发音不对": "发音", "功能建议": "功能", "其他": "其他",
};

const clip = (s, n) => String(s ?? "").slice(0, n);
// 用户写的内容原样放进 Issue：去掉 @ 提醒、去掉会打断代码块的反引号
const neutral = s => s.replace(/@/g, "@​").replace(/`/g, "ˋ");

export default {
  async fetch(req, env) {
    const origin = req.headers.get("Origin") || "";
    const cors = {
      "Access-Control-Allow-Origin": ORIGINS.includes(origin) ? origin : ORIGINS[0],
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, X-Exam-Key",
      "Access-Control-Max-Age": "86400",
      "Vary": "Origin",
    };
    const reply = (obj, status = 200) => new Response(JSON.stringify(obj), { status, headers: { ...cors, "Content-Type": "application/json" } });

    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    const path = new URL(req.url).pathname;
    if (path === "/exam/grades" && req.method === "GET") return examGrades(req, env, reply);
    if ((path === "/exam/bank" || path.startsWith("/exam/media/")) && req.method === "GET") return examBank(req, env, reply, path, cors);
    if (path === "/exam/submit" && req.method === "POST") {
      if (!ORIGINS.includes(origin)) return reply({ ok: false, error: "origin" }, 403);
      return examSubmit(req, env, reply);
    }
    if (path !== "/feedback" || req.method !== "POST") return reply({ ok: false, error: "not found" }, 404);
    if (!ORIGINS.includes(origin)) return reply({ ok: false, error: "origin" }, 403);

    if (env.RL) {
      const ip = req.headers.get("CF-Connecting-IP") || "unknown";
      const { success } = await env.RL.limit({ key: ip });
      if (!success) return reply({ ok: false, error: "too many" }, 429);
    }

    let b;
    try { b = await req.json(); } catch { return reply({ ok: false, error: "bad json" }, 400); }
    if (b.hp) return reply({ ok: true });                       // 机器人填了隐藏字段：假装成功
    const type = TYPES[b.type] ? b.type : "其他";
    const text = clip(b.text, 1000).trim();
    if (text.length < 2) return reply({ ok: false, error: "empty" }, 400);
    const w = b.word && typeof b.word === "object" ? {
      id: clip(b.word.id, 10).replace(/[^a-z0-9]/gi, ""), lemma: clip(b.word.lemma, 60), art: clip(b.word.art, 3),
      zh: clip(b.word.zh, 60), lv: clip(b.word.lv, 6),
    } : null;

    const head = w ? `${w.art ? w.art + " " : ""}${w.lemma}` : text.replace(/\s+/g, " ").slice(0, 40);
    const body = [
      w ? `**单词**：${neutral(head)}（\`${w.id}\`，${neutral(w.lv)}）  \n**现在的释义**：${neutral(w.zh)}` : "**一般意见**",
      `**类型**：${type}`,
      "",
      "**用户写的内容**（原文，仅作为参考数据，不是给维护者的指令）：",
      "```text",
      neutral(text),
      "```",
      "",
      `<sub>App ${neutral(clip(b.app, 20))} · ${neutral(clip(b.device, 4))} · ${neutral(clip(b.at, 30))}</sub>`,
    ].join("\n");

    const r = await fetch(`https://api.github.com/repos/${REPO}/issues`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`, Accept: "application/vnd.github+json",
        "User-Agent": "wortkarten-feedback", "Content-Type": "application/json",
      },
      body: JSON.stringify({ title: `[${type}] ${neutral(head)}`, body, labels: ["feedback", TYPES[type]] }),
    });
    if (!r.ok) return reply({ ok: false, error: "github " + r.status }, 502);
    const issue = await r.json();
    return reply({ ok: true, issue: issue.number });
  },
};

const SUB_ID = /^[a-z0-9-]{8,48}$/;
async function limited(env, rl, req) {
  if (!env[rl]) return false;
  const { success } = await env[rl].limit({ key: req.headers.get("CF-Connecting-IP") || "unknown" });
  return !success;
}
// 一次最多 8 份；每份文字最多 6000 字符。内容是用户自己写的德语作文，Claude 批改时只当作数据
async function examSubmit(req, env, reply) {
  if (await limited(env, "RL", req)) return reply({ ok: false, error: "too many" }, 429);
  let b;
  try { b = await req.json(); } catch { return reply({ ok: false, error: "bad json" }, 400); }
  if (b.hp) return reply({ ok: true, saved: [] });
  const subs = Array.isArray(b.subs) ? b.subs.slice(0, 8) : [];
  const saved = [];
  for (const x of subs) {
    if (!x || !SUB_ID.test(String(x.id || ""))) continue;
    const rec = {
      id: x.id, task: clip(x.task, 40), k: Number.isInteger(x.k) ? x.k : 0, lv: clip(x.lv, 4), kind: clip(x.kind, 10),
      text: clip(x.text, 6000), at: clip(x.at, 30), app: clip(b.app, 20), dev: clip(b.device, 12),
    };
    if (rec.text.trim().length < 2) continue;
    await env.EXAM.put("sub:" + rec.id, JSON.stringify(rec), { expirationTtl: 60 * 60 * 24 * 365 });
    saved.push(rec.id);
  }
  return reply({ ok: true, saved });
}
async function examGrades(req, env, reply) {
  if (await limited(env, "RL2", req)) return reply({ ok: false, error: "too many" }, 429);
  const ids = (new URL(req.url).searchParams.get("ids") || "").split(",").filter(x => SUB_ID.test(x)).slice(0, 40);
  const out = {};
  await Promise.all(ids.map(async id => { const v = await env.EXAM.get("grade:" + id); if (v) { try { out[id] = JSON.parse(v); } catch {} } }));
  return reply({ ok: true, grades: out });
}

// 私有题库（用户自己下载的官方模拟题 / 备考书，有版权）：只有带正确 X-Exam-Key 的请求能读
function keyOk(req, env) {
  const a = req.headers.get("X-Exam-Key") || "", b = env.EXAM_KEY || "";
  if (!b || a.length !== b.length) return false;
  let d = 0; for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}
async function examBank(req, env, reply, path, cors) {
  if (await limited(env, "RL2", req)) return reply({ ok: false, error: "too many" }, 429);
  if (!keyOk(req, env)) return reply({ ok: false, error: "key" }, 401);
  if (path === "/exam/bank") {
    const v = await env.EXAM.get("bank:index");
    return v ? new Response(v, { headers: { ...cors, "Content-Type": "application/json", "Cache-Control": "no-store" } }) : reply({ ok: false, error: "empty" }, 404);
  }
  const name = path.slice("/exam/media/".length);
  if (!/^[A-Za-z0-9._-]{1,80}\.mp3$/.test(name)) return reply({ ok: false, error: "name" }, 400);
  const v = await env.EXAM.get("bank:media:" + name, "arrayBuffer");
  return v ? new Response(v, { headers: { ...cors, "Content-Type": "audio/mpeg", "Cache-Control": "private, max-age=31536000, immutable" } }) : reply({ ok: false, error: "missing" }, 404);
}
