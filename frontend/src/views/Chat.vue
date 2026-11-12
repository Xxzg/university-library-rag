<script setup>
import { nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import api, { chatStream } from '../api'

const route = useRoute()
const router = useRouter()

const sessionId = ref(null)
const messages = ref([]) // {role, content, citations, streaming}
const input = ref('')
const sending = ref(false)
const listRef = ref(null)
const sessions = ref([]) // 右侧历史会话列表

// 记住当前会话：切换页面/刷新后能回到原会话，避免每次进来新建空会话
const SID_KEY = 'chat_current_sid'

function scrollToBottom() {
  nextTick(() => {
    const el = listRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function rememberSid(id) {
  sessionId.value = id
  if (id) sessionStorage.setItem(SID_KEY, String(id))
  else sessionStorage.removeItem(SID_KEY)
}

async function loadSessions() {
  try {
    const { data } = await api.get('/sessions')
    sessions.value = data
  } catch {
    /* 拦截器已提示 */
  }
}

async function loadSession(id) {
  const { data } = await api.get(`/sessions/${id}`)
  rememberSid(data.id)
  messages.value = data.messages.map((m) => ({ ...m, streaming: false }))
  scrollToBottom()
}

async function switchSession(s) {
  if (s.id === sessionId.value) return
  router.replace(`/chat/${s.id}`)
}

async function deleteSession(s) {
  try {
    await ElMessageBox.confirm(`删除会话「${s.title}」及全部消息？`, '删除会话', { type: 'warning' })
  } catch {
    return
  }
  await api.delete(`/sessions/${s.id}`)
  ElMessage.success('已删除')
  // 删的是当前会话则回到空白
  if (s.id === sessionId.value) startNewChat()
  await loadSessions()
}

/** 「新对话」：清空当前状态回到空白输入，但不立即创建会话（第一次发问时才建） */
function startNewChat() {
  rememberSid(null)
  messages.value = []
  input.value = ''
  router.replace('/chat')
}

onMounted(async () => {
  await loadSessions()
  // 优先级：路由 sessionId > sessionStorage 记住的当前会话 > 空状态（不创建）
  const fromRoute = route.params.sessionId
  const fromMemory = sessionStorage.getItem(SID_KEY)
  const target = fromRoute || fromMemory
  if (target) {
    try {
      await loadSession(target)
      if (!fromRoute) router.replace(`/chat/${target}`)
      return
    } catch {
      sessionStorage.removeItem(SID_KEY)
    }
  }
})

watch(() => route.params.sessionId, (id) => {
  // route.params 是字符串，sessionId.value 是数字，统一转字符串比较，避免类型不匹配误触发 loadSession
  if (id && String(id) !== String(sessionId.value)) loadSession(id)
})

async function send() {
  const question = input.value.trim()
  if (!question || sending.value) return
  // 延迟创建：第一次发问时才真正建立会话
  if (!sessionId.value) {
    const { data } = await api.post('/sessions', {})
    rememberSid(data.id)
    // 静默更新 URL，不触发 Vue Router 的 route 变化，避免重渲染干扰流式回答
    window.history.replaceState(history.state, '', `/chat/${data.id}`)
  }

  input.value = ''
  messages.value.push({ role: 'user', content: question })
  const aiMsg = reactive({ role: 'assistant', content: '', citations: null, streaming: true })
  messages.value.push(aiMsg)
  sending.value = true
  scrollToBottom()

  try {
    await chatStream(sessionId.value, question, (ev) => {
      if (ev.event === 'delta') {
        aiMsg.content += ev.content
        scrollToBottom()
      } else if (ev.event === 'citation') {
        aiMsg.citations = ev.citations
      } else if (ev.event === 'rewrite') {
        aiMsg.rewrite = ev.question
      } else if (ev.event === 'error') {
        aiMsg.content += `\n\n${ev.message}`
        aiMsg.streaming = false
      } else if (ev.event === 'done') {
        aiMsg.streaming = false
      }
    })
  } catch (e) {
    aiMsg.content += `\n\n[连接失败] ${e.message}`
  } finally {
    aiMsg.streaming = false
    sending.value = false
    scrollToBottom()
    // 会话标题可能因首轮提问而更新，刷新右侧列表
    await loadSessions()
  }
}

/** 把答案中的 [1][2] 渲染为可点击标记 */
function renderContent(content) {
  const esc = content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  return esc
    .replace(/\n/g, '<br>')
    .replace(/\[(\d+)\]/g, '<span class="citation-ref" onclick="window.__citeClick && window.__citeClick($1)">[$1]</span>')
}

function jumpToCitation(index) {
  const el = document.getElementById(`cite-card-${index}`)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

function fmtTime(t) {
  const d = new Date(t)
  const now = new Date()
  const diff = (now - d) / 60000 // 分钟
  if (diff < 1) return '刚刚'
  if (diff < 60) return `${Math.floor(diff)}分钟前`
  if (diff < 1440) return `${Math.floor(diff / 60)}小时前`
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

// 供渲染出的 span 调用
window.__citeClick = jumpToCitation
</script>

<template>
  <div class="chat-page">
    <!-- 左：对话区 -->
    <div class="chat-main">
      <div class="chat-header">
        <div class="header-left">
          <span class="page-title">智能问答</span>
          <span class="hint">回答基于馆藏文献生成，引用编号可点击溯源</span>
        </div>
        <el-button @click="startNewChat">＋ 新对话</el-button>
      </div>

      <div ref="listRef" class="msg-list">
        <el-empty v-if="messages.length === 0" description="向馆藏文献库提问吧，例如：TF-IDF 的逆文档频率怎么计算？" />

        <div v-for="(msg, i) in messages" :key="i" class="msg-row" :class="msg.role">
          <div class="avatar">{{ msg.role === 'user' ? '我' : '📖' }}</div>
          <div class="bubble-wrap">
            <div class="bubble">
              <div v-if="msg.role === 'assistant' && msg.rewrite" class="rewrite-tip">
                检索改写：{{ msg.rewrite }}
              </div>
              <div
                :class="{ 'typing-cursor': msg.streaming }"
                v-html="msg.role === 'assistant' ? renderContent(msg.content) : msg.content"
              ></div>
            </div>

            <!-- 溯源引用卡片 -->
            <div v-if="msg.citations?.length" class="citations">
              <div class="cite-title">📚 引用来源（{{ msg.citations.length }}）</div>
              <div
                v-for="c in msg.citations"
                :id="`cite-card-${c.index}`"
                :key="c.index"
                class="cite-card"
              >
                <div class="cite-head">
                  <span class="cite-no">[{{ c.index }}]</span>
                  <span class="cite-book">《{{ c.title }}》</span>
                  <el-tag v-if="c.page" size="small" type="info" effect="plain">第 {{ c.page }} 页</el-tag>
                  <span class="cite-score">{{ (c.score * 100).toFixed(1) }}%</span>
                </div>
                <div class="cite-snippet">{{ c.snippet }}…</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="input-bar">
        <el-input
          v-model="input"
          :disabled="sending"
          placeholder="输入问题，Enter 发送"
          size="large"
          @keyup.enter="send"
        />
        <el-button type="primary" size="large" :loading="sending" @click="send">发送</el-button>
      </div>
    </div>

    <!-- 右：历史会话列表 -->
    <aside class="session-aside">
      <div class="aside-head">
        <span class="aside-title">历史会话</span>
        <span class="aside-count">{{ sessions.length }}</span>
      </div>
      <div class="session-list">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="session-item"
          :class="{ active: s.id === sessionId }"
          @click="switchSession(s)"
        >
          <div class="s-title">{{ s.title }}</div>
          <div class="s-meta">
            <span>{{ s.message_count }} 条</span>
            <span>·</span>
            <span>{{ fmtTime(s.updated_at) }}</span>
          </div>
          <el-icon class="s-del" @click.stop="deleteSession(s)"><Delete /></el-icon>
        </div>
        <el-empty v-if="sessions.length === 0" :image-size="60" description="暂无历史会话" />
      </div>
    </aside>
  </div>
</template>

<style scoped>
.chat-page { height: 100%; display: flex; }

/* 左：对话区 */
.chat-main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.chat-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 24px; background: #fff; border-bottom: 1px solid #e4e7ed;
}
.header-left { display: flex; align-items: baseline; gap: 12px; }
.page-title { font-size: 16px; font-weight: 600; color: #303133; }
.hint { font-size: 12px; color: #909399; }

.msg-list { flex: 1; overflow-y: auto; padding: 24px; }
.msg-row { display: flex; gap: 10px; margin-bottom: 20px; }
.msg-row.user { flex-direction: row-reverse; }
.avatar {
  width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; background: #e6f1fb; color: #185fa5;
}
.msg-row.user .avatar { background: #95ec69; color: #1a3; }
.bubble-wrap { max-width: 78%; }
.bubble {
  padding: 12px 16px; border-radius: 12px; font-size: 14px; line-height: 1.7;
  background: #fff; border: 1px solid #e4e7ed; word-break: break-word;
}
.msg-row.user .bubble { background: #95ec69; border-color: #95ec69; }
.rewrite-tip {
  font-size: 12px; color: #854f0b; background: #faeeda;
  padding: 4px 10px; border-radius: 6px; margin-bottom: 8px;
}

.citations { margin-top: 10px; display: flex; flex-direction: column; gap: 8px; }
.cite-title { font-size: 12px; color: #909399; }
.cite-card {
  background: #f8fafc; border: 1px solid #e4e7ed; border-radius: 8px;
  padding: 10px 12px; transition: border-color 0.2s;
}
.cite-card:hover { border-color: #85b7eb; }
.cite-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
.cite-no { font-size: 12px; color: #185fa5; font-weight: 600; }
.cite-book { font-size: 13px; font-weight: 500; color: #303133; }
.cite-score { font-size: 11px; color: #0f6e56; margin-left: auto; }
.cite-snippet {
  font-size: 12px; color: #606266; line-height: 1.6;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}

.input-bar {
  display: flex; gap: 12px; padding: 14px 24px;
  background: #fff; border-top: 1px solid #e4e7ed;
}

/* 右：历史会话列表 */
.session-aside {
  width: 250px; flex-shrink: 0; background: #fff;
  border-left: 1px solid #e4e7ed; display: flex; flex-direction: column;
}
.aside-head {
  display: flex; align-items: center; gap: 8px;
  padding: 14px 16px; border-bottom: 1px solid #e4e7ed;
}
.aside-title { font-size: 14px; font-weight: 600; color: #303133; }
.aside-count {
  font-size: 11px; color: #909399; background: #f0f2f5;
  padding: 1px 7px; border-radius: 10px;
}
.session-list { flex: 1; overflow-y: auto; padding: 6px; }
.session-item {
  position: relative; padding: 10px 12px; border-radius: 8px; cursor: pointer;
  transition: background 0.15s; margin-bottom: 2px;
}
.session-item:hover { background: #f5f7fa; }
.session-item.active { background: #e6f1fb; }
.session-item.active .s-title { color: #0c447c; }
.s-title {
  font-size: 13px; color: #303133; font-weight: 500; margin-bottom: 4px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-right: 22px;
}
.s-meta { font-size: 11px; color: #909399; display: flex; gap: 4px; }
.s-del {
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  font-size: 14px; color: #c0c4cc; opacity: 0; transition: all 0.15s; cursor: pointer;
}
.session-item:hover .s-del { opacity: 1; }
.s-del:hover { color: #f56c6c; }
</style>
