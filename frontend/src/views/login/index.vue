<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="login-header">
          <img src="/favicon.png" alt="logo" class="logo">
          <h2>NiceAPI</h2>
        </div>
      </template>
      <el-form :model="loginForm" :rules="loginRules" ref="loginRef" label-position="top">
        <el-form-item label="使用者名稱" prop="username">
          <el-input v-model="loginForm.username" placeholder="請輸入使用者名稱" prefix-icon="User" />
        </el-form-item>
        <el-form-item label="密碼" prop="password">
          <el-input v-model="loginForm.password" type="password" placeholder="請輸入密碼" prefix-icon="Lock" show-password @keyup.enter="handleLogin" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="login-button" :loading="loading" @click="handleLogin">登入</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../../store/user'
import type { FormInstance } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()

const loginRef = ref<FormInstance>()
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const loginRules = {
  username: [{ required: true, message: '請輸入使用者名稱', trigger: 'blur' }],
  password: [{ required: true, message: '請輸入密碼', trigger: 'blur' }]
}

const handleLogin = async () => {
  if (!loginRef.value) return
  
  await loginRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await userStore.login(loginForm)
        router.push('/')
      } catch (error) {
        console.error(error)
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f5f7fa;
}

.login-card {
  width: 400px;
}

.login-header {
  text-align: center;
}

.logo {
  width: 64px;
  height: 64px;
}

.login-button {
  width: 100%;
}
</style>