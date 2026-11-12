<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const router = useRouter()
const route = useRoute()
const sessions = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/sessions')
    sessions.value = data
  } finally {
    loading.value = false
  }
}
onMounted(load)

function open(s) {
  router.push(`/chat/${s.id}`)
}

async function rename(s) {
  try {
    const { value } = await ElMessageBox.prompt('新的会话标题', '重命名', {
      inputValue: s.title,
      inputPattern: /^.{1,64}$/,
      inputErrorMessage: '标题长度 1~64',
    })
    await api.put(`/sessions/${s.id}`, { title: value })
    ElMessage.success('已重命名')
    await load()
  } catch {
    /* 取消 */
  }
}

async function remove(s) {
  try {
    await ElMessageBox.confirm(`删除会话「${s.title}」及全部消息？`, '删除会话', { type: 'warning' })
    await api.delete(`/sessions/${s.id}`)
    if (String(s.id) === String(route.params.sessionId)) router.push('/chat')
    ElMessage.success('已删除')
    await load()
  } catch {
    /* 取消 */
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2>历史会话</h2>
        <p class="sub">按用户隔离存储，点击会话可恢复完整对话上下文继续追问</p>
      </div>
    </div>

    <el-table v-loading="loading" :data="sessions" stripe>
      <el-table-column label="会话" min-width="280">
        <template #default="{ row }">
          <el-link type="primary" @click="open(row)">{{ row.title }}</el-link>
        </template>
      </el-table-column>
      <el-table-column prop="message_count" label="消息数" width="90" />
      <el-table-column label="最近活跃" width="180">
        <template #default="{ row }">{{ new Date(row.updated_at).toLocaleString('zh-CN') }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" @click="rename(row)">重命名</el-button>
          <el-button text size="small" type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无历史会话，去智能问答页发起第一轮提问" />
      </template>
    </el-table>
  </div>
</template>

<style scoped>
.page { padding: 24px; height: 100%; overflow-y: auto; }
.page-header { margin-bottom: 18px; }
h2 { font-size: 17px; color: #303133; margin-bottom: 6px; }
.sub { font-size: 12px; color: #909399; }
</style>
