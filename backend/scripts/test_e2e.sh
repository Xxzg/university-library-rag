#!/usr/bin/env bash
# 端到端联调脚本：登录→上传文献→创建会话→SSE问答→验证历史
set -uo pipefail
PY="E:/learning/bishe/backend/venv/Scripts/python.exe"
BASE="http://127.0.0.1:8000"
TESTDOC="E:/learning/bishe/backend/data/testdocs/从“互联网+”到“人工智能+”：技术社会着陆的媒介逻辑与行动方略_曾巍.pdf"

echo "===== 1. 教师登录 ====="
T_TOKEN=$(curl -s -X POST "$BASE/api/auth/login" -H "Content-Type: application/json" \
  -d '{"username":"teacher","password":"teacher123"}' | "$PY" -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
echo "  teacher token: ${T_TOKEN:0:20}..."

echo "===== 2. 上传测试文献 ====="
curl -s -X POST "$BASE/api/documents/upload" \
  -H "Authorization: Bearer $T_TOKEN" \
  -F "file=@$TESTDOC" \
  -F "title=从“互联网+”到“人工智能+”：技术社会着陆的媒介逻辑与行动方略" | "$PY" -c "import sys,json;d=json.load(sys.stdin);print(f\"  文献ID={d['id']} 状态={d['status']} 片段数={d['chunk_count']}\")"

echo "===== 3. 学生登录 ====="
S_TOKEN=$(curl -s -X POST "$BASE/api/auth/login" -H "Content-Type: application/json" \
  -d '{"username":"student","password":"student123"}' | "$PY" -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
echo "  student token: ${S_TOKEN:0:20}..."

echo "===== 4. 创建会话 ====="
SID=$(curl -s -X POST "$BASE/api/sessions" -H "Authorization: Bearer $S_TOKEN" \
  -H "Content-Type: application/json" -d '{}' | "$PY" -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "  session id=$SID"

echo "===== 5. SSE 流式问答 ====="
Q="这篇文献如何论述从“互联网+”到“人工智能+”的转变？其核心的媒介逻辑是什么？"
echo "  问题: $Q"
echo "  --- SSE 响应 ---"
curl -s -N -X POST "$BASE/api/chat" \
  -H "Authorization: Bearer $S_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":$SID,\"question\":\"$Q\"}" \
  | "$PY" -c "
import sys,json
ans=''
cites=[]
for line in sys.stdin:
    line=line.strip()
    if not line.startswith('data: '): continue
    try:
        ev=json.loads(line[6:])
    except: continue
    t=ev.get('event')
    if t=='delta': ans+=ev.get('content','')
    elif t=='citation': cites=ev.get('citations',[])
    elif t=='rewrite': print(f'  [改写] {ev[\"question\"]}')
    elif t=='error': print(f'  [错误] {ev[\"message\"]}'); ans='[ERROR]'
    elif t=='done': print('  [完成]')
print('  --- 答案 ---')
print('  '+ans[:500].replace(chr(10),chr(10)+'  '))
print('  --- 引用来源 ---')
for c in cites:
    print(f'  [{c[\"index\"]}] {c[\"title\"]} 第{c.get(\"page\")}页 相关度{c.get(\"score\")}')
"

echo "===== 6. 拉取会话历史（验证落库） ====="
curl -s "$BASE/api/sessions/$SID" -H "Authorization: Bearer $S_TOKEN" \
  | "$PY" -c "
import sys,json
d=json.load(sys.stdin)
print(f'  会话标题: {d[\"title\"]}')
print(f'  消息数: {d[\"message_count\"]}')
for m in d.get('messages',[]):
    tag='用户' if m['role']=='user' else 'AI'
    cite=f' (含{len(m.get(\"citations\") or [])}条引用)' if m['citations'] else ''
    print(f'  [{tag}] {m[\"content\"][:80]}...{cite}')
"
echo "===== 联调结束 ====="
