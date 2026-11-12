<script setup>
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { ElMessageBox } from 'element-plus'

const router = useRouter()
const user = useUserStore()

function handleLogout() {
  ElMessageBox.confirm('确定退出登录？', '提示', { type: 'warning' })
    .then(() => {
      user.logout()
      router.push('/login')
    })
    .catch(() => {})
}
</script>

<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">
        <span class="logo-icon">📖</span>
        <span class="logo-text">馆藏智能问答</span>
      </div>
      <el-menu :default-active="$route.path" router class="menu">
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>智能问答</span>
        </el-menu-item>
        <el-menu-item index="/documents">
          <el-icon><Collection /></el-icon>
          <span>文献库</span>
        </el-menu-item>
        <el-menu-item v-if="user.isAdmin" index="/users">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
      </el-menu>
      <div class="aside-footer">
        <div class="user-info">
          <el-avatar :size="32">{{ user.user?.username?.[0]?.toUpperCase() }}</el-avatar>
          <div class="user-meta">
            <div class="username">{{ user.user?.username }}</div>
            <el-tag size="small" :type="user.isAdmin ? 'danger' : user.isTeacher ? 'warning' : 'info'">
              {{ { admin: '管理员', teacher: '教师', student: '学生' }[user.role] }}
            </el-tag>
          </div>
        </div>
        <el-button text size="small" @click="handleLogout">退出登录</el-button>
      </div>
    </el-aside>
    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script>
import { ChatDotRound, Collection, User } from '@element-plus/icons-vue'
export default { components: { ChatDotRound, Collection, User } }
</script>

<style scoped>
.layout { height: 100%; }
.aside {
  display: flex;
  flex-direction: column;
  background: #fff;
  border-right: 1px solid #e4e7ed;
}
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 18px 20px;
  font-size: 16px;
  font-weight: 600;
  color: #0c447c;
}
.menu { border-right: none; flex: 1; }
.aside-footer {
  padding: 14px 16px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.user-info { display: flex; align-items: center; gap: 8px; }
.user-meta { display: flex; flex-direction: column; gap: 2px; }
.username { font-size: 13px; color: #303133; }
.main { padding: 0; height: 100%; overflow: hidden; }
</style>
