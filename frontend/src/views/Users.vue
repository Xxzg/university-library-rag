<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const users = ref([])
const loading = ref(false)
const roleOptions = [
  { value: 'student', label: '学生' },
  { value: 'teacher', label: '教师' },
  { value: 'admin', label: '管理员' },
]

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/users')
    users.value = data
  } finally {
    loading.value = false
  }
}
onMounted(load)

async function changeRole(row) {
  try {
    await api.put(`/users/${row.id}/role`, { role: row.role })
    ElMessage.success(`已将 ${row.username} 的角色调整为 ${row.role}`)
  } catch {
    await load() // 回滚显示
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(
      `删除用户 ${row.username}？其名下的会话与历史记录将一并删除。`,
      '删除用户',
      { type: 'warning' },
    )
    await api.delete(`/users/${row.id}`)
    ElMessage.success('已删除')
    await load()
  } catch {
    /* 取消 */
  }
}

const roleTag = { admin: 'danger', teacher: 'warning', student: 'info' }
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2>用户管理</h2>
        <p class="sub">仅管理员可见：角色分配（学生 / 教师 / 管理员三级权限）与账号管理</p>
      </div>
    </div>

    <el-table v-loading="loading" :data="users" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户名" min-width="160" />
      <el-table-column label="当前角色" width="120">
        <template #default="{ row }">
          <el-tag :type="roleTag[row.role]" size="small">{{ row.role }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="调整角色" width="160">
        <template #default="{ row }">
          <el-select :model-value="row.role" size="small" @change="changeRole(row)">
            <el-option v-for="o in roleOptions" :key="o.value" :value="o.value" :label="o.label" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="注册时间" width="180">
        <template #default="{ row }">{{ new Date(row.created_at).toLocaleString('zh-CN') }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.page { padding: 24px; height: 100%; overflow-y: auto; }
.page-header { margin-bottom: 18px; }
h2 { font-size: 17px; color: #303133; margin-bottom: 6px; }
.sub { font-size: 12px; color: #909399; }
</style>
