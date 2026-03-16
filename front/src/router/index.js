import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/DashboardPage.vue'),
        meta: { title: '总览' },
      },
      {
        path: 'coverage',
        name: 'Coverage',
        component: () => import('@/views/coverage/CoveragePage.vue'),
        meta: { title: '覆盖率查询' },
      },
      {
        path: 'projects',
        name: 'Projects',
        component: () => import('@/views/projects/ProjectsPage.vue'),
        meta: { title: '项目管理' },
      },
      {
        path: 'members',
        name: 'Members',
        component: () => import('@/views/members/MembersPage.vue'),
        meta: { title: '成员管理' },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/settings/SettingsPage.vue'),
        meta: { title: '系统设置' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  document.title = (to.meta.title ? `${to.meta.title} - ` : '') + 'AI代码覆盖率看板'
  next()
})

export default router
