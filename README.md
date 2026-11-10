# Wortkarten（德语背单词网站）

**主力版本（平板 / 手机 / 电脑）：https://snipperxx.github.io/wortkarten/**（仓库 github.com/snipperxx/wortkarten，公开）
- 网页在 `docs/`（index.html + sw.js + manifest + words.json + audio/），GitHub Pages 从 main 分支的 docs/ 发布。发布：`bash deploy.sh "说明"`（提交并推送），约 1 分钟上线；设备上打开或切回前台时自动换成新版。
- 和送报 App 同一个域名（snipperxx.github.io），共用浏览器缓存区：两边的 sw.js 都只清理自己前缀的缓存（wortkarten- / songbao），改 sw.js 时别改坏。
- 不进仓库：src/（Goethe 原始 PDF）、audio_small/、site/（旧 claude.ai 版）。
- 安装到桌面：在安卓 Chrome 里打开网址，菜单选“添加到主屏幕 / 安装应用”。
- 多设备同步：设置 → 多设备同步，粘贴一个只有 gist 权限的 GitHub token（每台设备填一次，可以用同一个）。进度存在私密 Gist “wortkarten-progress.json” 里，每个词按最后修改时间合并。
- 旧的 claude.ai 版：https://claude.ai/artifact/938zwT5CUcFdC6ABjBGCte ，进度和上面的不互通。

## 内容
- 词库 6,580 词：Goethe 官方 A1 / A2 / B1 词表（`src/`），加上求职、IT、办事专题词 113 个（`data/extra.py`），以及 B2 1,994 + C1 1,412 个（2026-11-10，`data/adv/<主题>.json`，按 `data/adv/SPEC.md` 由 Claude 分主题生成）。去掉了只在瑞士或奥地利使用的词。
- B2 / C1：`python -I scripts/build_adv.py .` 去重、校验、分配固定 id（y0000 起）→ `data/adv_words.json`，merge.py 会把它并进词库；发音用 `scripts/gen_audio_adv.py`，按 id 固定分包到 `docs/audio/b32+`（旧包 b0–b31 在用户设备上永久缓存，不能改）。要补词：在 `data/adv/` 加或改主题文件，重跑这两个脚本。生成前先导出已有词表到 `data/existing_lemmas.txt`（不进仓库）。
- 中文释义、例句翻译、义项、常用搭配和提示由 Claude 生成（`data/chunk*_zh.json`、`chunk*_use.json`），可能有个别错误。
- 单词发音：微软 Katja 神经语音（edge-tts）预生成，经 ffmpeg 压缩（`audio_small/`），打包成 `site/audio/b*.json`。

## 重建流程
```
python -I scripts/parse_goethe.py src data      # PDF → A1/A2/B1_raw.json
python -I scripts/build_base.py data            # → base.json
# chunk*_zh.json / chunk*_use.json 由 Claude 生成
python -I data/extra.py data/extra.json
python -I scripts/merge.py .                    # → site/words.json
<装了 edge-tts 的 python> scripts/gen_audio.py .  # 缺的音频补生成并打包
```
改完后让 Claude 用 Artifact 工具重新发布 `site/wortkarten.html`，并带上 `words.json` 和 `audio/*.json`，网址不变。
