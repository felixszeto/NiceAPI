<template>
  <div class="flex h-screen overflow-hidden bg-[#f8fafc]">
    <!-- Mobile overlay -->
    <div
      v-if="isMobile && !isCollapse"
      class="fixed inset-0 bg-black/50 z-40 transition-opacity"
      @click="isCollapse = true"
    />

    <!-- Sidebar -->
    <aside
      class="fixed md:relative z-50 h-full flex flex-col transition-all duration-300 ease-in-out"
      :class="[
        isMobile
          ? (isCollapse ? '-translate-x-full' : 'translate-x-0')
          : '',
        isCollapse && !isMobile ? 'w-[68px]' : 'w-[240px]'
      ]"
      :style="{ backgroundColor: '#0f172a' }"
    >
      <!-- Logo area -->
      <div class="flex items-center h-16 px-4 border-b border-white/10 shrink-0">
        <img src="/favicon.png" alt="logo" class="w-8 h-8 shrink-0" />
        <transition name="fade">
          <span
            v-if="!isCollapse || isMobile"
            class="ml-3 text-white font-semibold text-lg tracking-tight whitespace-nowrap"
          >NiceAPI</span>
        </transition>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 overflow-y-auto py-4 px-2 space-y-1">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="nav-item group flex items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200"
          :class="[
            activeMenu === item.path
              ? 'bg-primary-600 text-white shadow-lg shadow-primary-600/30'
              : 'text-slate-400 hover:bg-white/10 hover:text-white'
          ]"
          @click="isMobile && (isCollapse = true)"
        >
          <el-icon class="text-lg shrink-0" :class="isCollapse && !isMobile ? 'mx-auto' : ''">
            <component :is="item.icon" />
          </el-icon>
          <transition name="fade">
            <span v-if="!isCollapse || isMobile" class="ml-3 whitespace-nowrap">{{ item.label }}</span>
          </transition>
        </router-link>
      </nav>

      <!-- Sidebar footer -->
      <div class="p-3 border-t border-white/10 shrink-0">
        <button
          v-if="!isMobile"
          @click="isCollapse = !isCollapse"
          class="w-full flex items-center justify-center rounded-lg py-2 text-slate-400 hover:bg-white/10 hover:text-white transition-colors"
        >
          <el-icon class="text-lg">
            <component :is="isCollapse ? icons.Expand : icons.Fold" />
          </el-icon>
        </button>
      </div>
    </aside>

    <!-- Main content area -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <!-- Header -->
      <header class="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-4 md:px-6 shrink-0 shadow-sm">
        <div class="flex items-center gap-3">
          <button
            v-if="isMobile"
            @click="isCollapse = !isCollapse"
            class="p-2 -ml-2 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition-colors"
          >
            <el-icon class="text-xl">
              <component :is="isCollapse ? icons.Expand : icons.Fold" />
            </el-icon>
          </button>
          <h1 class="text-base md:text-lg font-semibold text-slate-800 truncate">
            {{ currentPageTitle }}
          </h1>
        </div>
        <div class="flex items-center">
          <el-dropdown @command="handleCommand" trigger="click">
            <button class="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-100 transition-colors text-slate-600">
              <div class="w-8 h-8 rounded-full bg-primary-500 flex items-center justify-center text-white text-sm font-medium">A</div>
              <span class="hidden sm:inline text-sm font-medium">管理員</span>
              <el-icon class="text-xs"><ArrowDown /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">
                  <el-icon class="mr-2"><SwitchButton /></el-icon>
                  登出
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- Page content -->
      <main class="flex-1 overflow-y-auto p-4 md:p-6">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, markRaw } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '../store/user'
import {
  DataBoard,
  Connection,
  Files,
  Key,
  Filter,
  Document,
  Setting,
  ArrowDown,
  Expand,
  Fold,
  SwitchButton
} from '@element-plus/icons-vue'

const route = useRoute()
const userStore = useUserStore()

const icons = { Expand, Fold }

const menuItems = [
  { path: '/dashboard', icon: markRaw(DataBoard), label: '儀表板' },
  { path: '/providers', icon: markRaw(Connection), label: '供應商管理' },
  { path: '/groups', icon: markRaw(Files), label: '群組管理' },
  { path: '/api-keys', icon: markRaw(Key), label: 'API 金鑰' },
  { path: '/keywords', icon: markRaw(Filter), label: '關鍵字過濾' },
  { path: '/logs', icon: markRaw(Document), label: '調用日誌' },
  { path: '/settings', icon: markRaw(Setting), label: '系統設置' },
]

const isCollapse = ref(false)
const screenWidth = ref(window.innerWidth)
const isMobile = computed(() => screenWidth.value < 768)

const updateScreenWidth = () => {
  screenWidth.value = window.innerWidth
  if (isMobile.value) {
    isCollapse.value = true
  }
}

onMounted(() => {
  window.addEventListener('resize', updateScreenWidth)
  updateScreenWidth()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateScreenWidth)
})

const activeMenu = computed(() => route.path)

const currentPageTitle = computed(() => {
  const item = menuItems.find(m => m.path === route.path)
  return item ? item.label : ''
})

const handleCommand = (command: string) => {
  if (command === 'logout') {
    userStore.logout()
  }
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.nav-item {
  text-decoration: none;
}
</style>