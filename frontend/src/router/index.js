import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    children: [
      { path: '', redirect: '/chat' },
      { path: 'chat/:sessionId?', name: 'chat', component: () => import('../views/Chat.vue') },
      { path: 'documents', name: 'documents', component: () => import('../views/Documents.vue') },
      { path: 'sessions', name: 'sessions', component: () => import('../views/Sessions.vue') },
      { path: 'users', name: 'users', component: () => import('../views/Users.vue'), meta: { roles: ['admin'] } },
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const user = useUserStore()
  if (to.meta.public) return true
  if (!user.token) return { name: 'login' }
  if (to.meta.roles && !to.meta.roles.includes(user.role)) {
    return { name: 'chat' }
  }
  return true
})

export default router
