# Wortkarten（德语背单词网站）

**主力版本（平板 / 手机 / 电脑）：https://snipperxx.github.io/newspaper-route/wortkarten/**
- 源码在 `app/`（index.html + sw.js + manifest + words.json + audio/）。发布：`bash deploy.sh "说明"`，它会复制到送报 App 仓库的 `wortkarten/` 子目录，再推送 main 和 gh-pages，约 1 分钟后上线。设备上打开或切回前台时会自动换成新版。
- 安装到桌面：在安卓 Chrome 里打开网址，菜单选“添加到主屏幕 / 安装应用”。
- 多设备同步：设置 → 多设备同步，粘贴一个只有 gist 权限的 GitHub token（每台设备填一次，可以用同一个）。进度存在私密 Gist “wortkarten-progress.json” 里，每个词按最后修改时间合并。
- 旧的 claude.ai 版：https://claude.ai/artifact/938zwT5CUcFdC6ABjBGCte ，进度和上面的不互通。

## 内容
- 词库 3,174 词：Goethe 官方 A1 / A2 / B1 词表（`src/`），加上求职、IT、办事专题词 113 个（`data/extra.py`）。去掉了只在瑞士或奥地利使用的词。
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
