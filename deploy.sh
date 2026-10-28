#!/usr/bin/env bash
# 发布：提交并推送到 snipperxx/wortkarten，GitHub Pages 从 main 的 docs/ 发布，约 1 分钟上线。
# 用法：bash deploy.sh "提交说明"
# 反馈机器人也会往 main 推送，所以先拉取再推。
set -euo pipefail
cd "$(dirname "$0")"
python -I scripts/check.py
git add -A
git commit -q -m "${1:-更新}" || true
git pull -q --rebase
git push -q && echo "已推送：https://snipperxx.github.io/wortkarten/"
