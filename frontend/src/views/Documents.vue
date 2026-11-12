<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const docs = ref([])
const loading = ref(false)
const uploading = ref(false)
const fileInput = ref(null)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/documents')
    docs.value = data
  } finally {
    loading.value = false
  }
}
onMounted(load)

function pickFile() {
  fileInput.value?.click()
}

async function doUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('title', file.name.replace(/\.[^.]+$/, ''))
    const { data } = await api.post('/documents/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    if (data.status === 'done') {
      ElMessage.success(`入库成功：${data.title}（${data.chunk_count} 个片段）`)
    } else {
      ElMessage.error(`入库失败：${data.error_msg || data.status}`)
    }
    await load()
  } catch {
    /* 拦截器已提示 */
  } finally {
    uploading.value = false
    event.target.value = ''
  }
}

async function remove(doc) {
  try {
    await ElMessageBox.confirm(
      `确定删除《${doc.title}》？向量库中的片段将一并移除。`,
      '删除文献',
      { type: 'warning' },
    )
    await api.delete(`/documents/${doc.id}`)
    ElMessage.success('已删除')
    await load()
  } catch {
    /* 取消 */
  }
}

function fmtSize(n) {
  if (n > 1024 * 1024) return (n / 1024 / 1024).toFixed(1) + ' MB'
  return (n / 1024).toFixed(0) + ' KB'
}

const statusMap = {
  done: { label: '已入库', type: 'success' },
  processing: { label: '处理中', type: 'warning' },
  pending: { label: '待处理', type: 'info' },
  failed: { label: '失败', type: 'danger' },
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2>馆藏文献库</h2>
        <p class="sub">支持 PDF / DOCX / TXT / MD，上传后自动解析、切分并向量化入库</p>
      </div>
      <el-button v-if="userStore.isTeacher" type="primary" :loading="uploading" @click="pickFile">
        ＋ 上传文献
      </el-button>
      <input ref="fileInput" type="file" accept=".pdf,.docx,.txt,.md" hidden @change="doUpload" />
    </div>

    <el-alert v-if="!userStore.isTeacher" type="info" :closable="false" class="tip">
      <template #title>当前角色为{{ userStore.isAdmin ? '管理员' : '学生' }}，仅可浏览文献库；上传文献需教师或管理员角色</template>
    </el-alert>

    <el-table v-loading="loading" :data="docs" stripe>
      <el-table-column label="文献标题" min-width="240">
        <template #default="{ row }">
          <span class="doc-title">{{ row.title }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="file_type" label="类型" width="80" />
      <el-table-column label="大小" width="90">
        <template #default="{ row }">{{ fmtSize(row.file_size) }}</template>
      </el-table-column>
      <el-table-column label="片段数" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.chunk_count" size="small" type="success" effect="plain">{{ row.chunk_count }}</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.status]?.type || 'info'" size="small">
            {{ statusMap[row.status]?.label || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="上传时间" width="170">
        <template #default="{ row }">{{ new Date(row.created_at).toLocaleString('zh-CN') }}</template>
      </el-table-column>
      <el-table-column v-if="userStore.isTeacher" label="操作" width="90" fixed="right">
        <template #default="{ row }">
          <el-button type="danger" text size="small" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="文献库为空，请上传馆藏文献（可用 backend/data/testdocs 下的测试文献）" />
      </template>
    </el-table>
  </div>
</template>

<style scoped>
.page { padding: 24px; height: 100%; overflow-y: auto; }
.page-header {
  display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 18px;
}
h2 { font-size: 17px; color: #303133; margin-bottom: 6px; }
.sub { font-size: 12px; color: #909399; }
.tip { margin-bottom: 16px; }
.doc-title { font-weight: 500; }
</style>
