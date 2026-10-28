// Wortkarten 反馈中转：App 里匿名提交的纠错 / 意见 → snipperxx/wortkarten 的 GitHub Issue。
// 密钥 GITHUB_TOKEN 只有这个仓库的 Issues 读写权限（wrangler secret put GITHUB_TOKEN）。
const REPO = "snipperxx/wortkarten";
const ORIGINS = ["https://snipperxx.github.io"];
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
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      "Access-Control-Max-Age": "86400",
      "Vary": "Origin",
    };
    const reply = (obj, status = 200) => new Response(JSON.stringify(obj), { status, headers: { ...cors, "Content-Type": "application/json" } });

    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (new URL(req.url).pathname !== "/feedback" || req.method !== "POST") return reply({ ok: false, error: "not found" }, 404);
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
