import { createRouter, createWebHistory } from 'vue-router'
import auth from '@/api/auth'

const routes = [
  { path: '/', name: 'home', component: () => import('@/views/LandingView.vue') },
  { path: '/admin/login', name: 'admin-login', component: () => import('@/views/admin/LoginView.vue') },
  {
    path: '/admin',
    component: () => import('@/views/admin/AdminLayout.vue'),
    beforeEnter: async (to, from, next) => {
      const user = await auth.checkSession()
      if (user) next()
      else next({ name: 'admin-login' })
    },
    children: [
      { path: '', name: 'admin-home', component: () => import('@/views/admin/AdminHome.vue') },
      { path: 'firmen', name: 'admin-firmen', component: () => import('@/views/admin/FirmenView.vue') },
      { path: 'kunden', name: 'admin-kunden', component: () => import('@/views/admin/KundenView.vue') },
    ],
  },
  {
    path: '/installer/login',
    name: 'installer-login',
    component: () => import('@/views/installer/LoginView.vue'),
  },
  {
    path: '/installer',
    component: () => import('@/views/installer/InstallerLayout.vue'),
    beforeEnter: async (to, from, next) => {
      const user = await auth.checkSession()
      if (user) next()
      else next({ name: 'installer-login' })
    },
    children: [
      { path: '', redirect: { name: 'installer-kunden' } },
      { path: 'kunden', name: 'installer-kunden', component: () => import('@/views/installer/KundenView.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', name: 'notfound', component: () => import('@/views/NotFoundView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
