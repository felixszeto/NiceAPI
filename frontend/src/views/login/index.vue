<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-primary-900 to-slate-900 p-4">
    <!-- Background decoration -->
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <div class="absolute -top-40 -right-40 w-80 h-80 bg-primary-500/10 rounded-full blur-3xl" />
      <div class="absolute -bottom-40 -left-40 w-80 h-80 bg-primary-400/10 rounded-full blur-3xl" />
    </div>

    <div class="relative w-full max-w-md">
      <!-- Login card -->
      <div class="bg-white rounded-2xl shadow-2xl shadow-black/20 p-8 md:p-10">
        <!-- Header -->
        <div class="text-center mb-8">
          <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary-50 mb-4">
            <img src="/favicon.png" alt="logo" class="w-10 h-10" />
          </div>
          <h1 class="text-2xl font-bold text-slate-800">NiceAPI</h1>
          <p class="text-slate-500 text-sm mt-1">登入您的管理後台</p>
        </div>

        <!-- Form -->
        <el-form :model="loginForm" :rules="loginRules" ref="loginRef" label-position="top" size="large">
          <el-form-item label="使用者名稱" prop="username">
            <el-input
              v-model="loginForm.username"
              placeholder="請輸入使用者名稱"
              prefix-icon="User"
              class="!rounded-lg"
            />
          </el-form-item>
          <el-form-item label="密碼" prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="請輸入密碼"
              prefix-icon="Lock"
              show-password
              class="!rounded-lg"
              @keyup.enter="handleLogin"
            />
          </el-form-item>
          <el-form-item class="!mt-8 !mb-0">
            <el-button
              type="primary"
              class="w-full !h-11 !rounded-lg !text-base !font-medium"
              :loading="loading"
              @click="handleLogin"
            >
              登入
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- Footer -->
      <p class="text-center text-slate-400 text-xs mt-6">
        &copy; {{ new Date().getFullYear() }} NiceAPI. All rights reserved.
      </p>
    </div>
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