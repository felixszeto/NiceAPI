import { defineStore } from 'pinia'
import request from '../utils/request'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    username: ''
  }),
  actions: {
    async login(loginForm: any) {
      const data: any = await request.post('/auth/login', loginForm)
      this.token = data.access_token
      localStorage.setItem('token', data.access_token)
    },
    logout() {
      this.token = ''
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
  }
})