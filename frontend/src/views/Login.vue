<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const mode = ref('login')
const form = reactive({ username: '', password: '' })

async function submit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    if (mode.value === 'login') {
      const { data } = await api.post('/auth/login', form)
      userStore.setLogin(data.access_token, data.user)
      ElMessage.success(`欢迎回来，${data.user.username}`)
      router.push('/chat')
    } else {
      await api.post('/auth/register', form)
      ElMessage.success('注册成功，请登录')
      mode.value = 'login'
    }
  } catch {
    /* 拦截器已提示 */
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="card">
      <div class="title">
        <span class="icon">📖</span>
        <h1>高校图书馆智能问答系统</h1>
        <p>基于 LangChain + RAG 的馆藏文献检索增强问答</p>
      </div>
      <el-form @submit.prevent="submit">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" size="large" :prefix-icon="'User'" />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            show-password
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button type="primary" size="large" class="submit" :loading="loading" @click="submit">
          {{ mode === 'login' ? '登 录' : '注 册' }}
        </el-button>
      </el-form>
      <div class="switch">
        <el-link type="primary" @click="mode = mode === 'login' ? 'register' : 'login'">
          {{ mode === 'login' ? '没有账号？注册（默认学生角色）' : '已有账号？去登录' }}
        </el-link>
      </div>
      <el-alert type="info" :closable="false" class="demo-tip">
        <template #title>演示账号：admin/admin123 · teacher/teacher123 · student/student123</template>
      </el-alert>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e6f1fb 0%, #f5f7fa 60%, #e1f5ee 100%);
}
.card {
  width: 400px;
  background: #fff;
  border-radius: 16px;
  padding: 40px 36px 28px;
  box-shadow: 0 8px 24px rgba(12, 68, 124, 0.08);
}
.title { text-align: center; margin-bottom: 28px; }
.icon { font-size: 36px; }
h1 { font-size: 19px; color: #0c447c; margin: 10px 0 6px; }
p { font-size: 12px; color: #909399; }
.submit { width: 100%; margin-top: 4px; }
.switch { text-align: center; margin: 14px 0 10px; }
.demo-tip { margin-top: 6px; }
</style>
