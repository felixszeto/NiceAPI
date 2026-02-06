import { createRouter, createWebHistory } from 'vue-router'
import Layout from '../layout/index.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/login/index.vue')
    },
    {
      path: '/',
      component: Layout,
      redirect: '/dashboard',
      children: [
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('../views/dashboard/index.vue')
        },
        {
          path: 'providers',
          name: 'Providers',
          component: () => import('../views/providers/index.vue')
        },
        {
          path: 'groups',
          name: 'Groups',
          component: () => import('../views/groups/index.vue')
        },
        {
          path: 'api-keys',
          name: 'ApiKeys',
          component: () => import('../views/api-keys/index.vue')
        },
        {
          path: 'keywords',
          name: 'Keywords',
          component: () => import('../views/keywords/index.vue')
        },
        {
          path: 'logs',
          name: 'Logs',
          component: () => import('../views/logs/index.vue')
        },
        {
          path: 'settings',
          name: 'Settings',
          component: () => import('../views/settings/index.vue')
        }
      ]
    },
    {
      path: '/remote',
      name: 'Remote',
      component: () => import('../views/remote/index.vue'),
      meta: { public: true }
    }
  ]
})

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.public) {
    next()
    return
  }

  if (to.name !== 'Login' && !token) {
    next({ name: 'Login' })
  } else if (to.name === 'Login' && token) {
    next({ name: 'Dashboard' })
  } else {
    next()
  }
})

export default router