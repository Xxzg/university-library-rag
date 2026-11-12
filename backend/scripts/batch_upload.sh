#!/usr/bin/env bash
# 批量上传 testdocs 下全部真实文献（用教师账号）
set -uo pipefail
PY="E:/learning/bishe/backend/venv/Scripts/python.exe"
BASE="http://127.0.0.1:8000"
DIR="E:/learning/bishe/backend/data/testdocs"

T_TOKEN=$(curl -s -X POST "$BASE/api/auth/login" -H "Content-Type: application/json" \
  -d '{"username":"teacher","password":"teacher123"}' | "$PY" -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

echo "教师登录成功，开始批量上传 testdocs 下文献..."
total=0; ok=0; fail=0
for f in "$DIR"/*.pdf "$DIR"/*.docx "$DIR"/*.md "$DIR"/*.txt; do
  [ -e "$f" ] || continue
  # 跳过我生成的模拟文献，只上传真实文献（按是否带下划线作者名后缀粗略区分）
  base=$(basename "$f")
  case "$base" in
    信息检索导论_节选.pdf|数字图书馆技术_节选.pdf|图书馆学基础_节选.docx|学术论文写作规范_节选.docx|知识服务与智能问答.md)
      echo "  [跳过模拟文献] $base"
      continue ;;
  esac
  total=$((total+1))
  title="${base%.*}"
  echo "  [上传] $base"
  result=$(curl -s -X POST "$BASE/api/documents/upload" \
    -H "Authorization: Bearer $T_TOKEN" \
    -F "file=@$f" -F "title=$title" \
    | "$PY" -c "
import sys,json
try:
    d=json.load(sys.stdin)
    print(f\"状态={d['status']} 片段数={d['chunk_count']}\" if d.get('status')=='done' else f\"状态={d.get('status')} 错误={d.get('error_msg','')[:80]}\")
except Exception as e:
    print(f'解析响应失败: {e}')
")
  echo "    -> $result"
  case "$result" in
    *状态=done*) ok=$((ok+1)) ;;
    *) fail=$((fail+1)) ;;
  esac
done
echo ""
echo "批量上传完成：共 $total 篇，成功 $ok，失败 $fail"
