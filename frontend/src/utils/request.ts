import axios from 'axios'
import { ElMessage } from 'element-plus'

const service = axios.create({
  baseURL: import.meta.env.VITE_APP_BASE_API || '/api/',
  timeout: 50000
})

// Request interceptor
service.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = 'Bearer ' + token
    }
    return config
  },
  error => {
    console.log(error)
    return Promise.reject(error)
  }
)

// Response interceptor
service.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.log('err' + error)
    let message = error.message
    if (error.response && error.response.data && error.response.data.detail) {
      message = error.response.data.detail
    }
    
    if (error.response && error.response.status === 401) {
      // 只有當不在 remote 頁面時才跳轉到登入
      if (!window.location.pathname.startsWith('/remote')) {
        localStorage.removeItem('token')
        window.location.href = '/login'
      }
    }

    ElMessage({
      message: message,
      type: 'error',
      duration: 5 * 1000
    })
    return Promise.reject(error)
  }
)

export default service