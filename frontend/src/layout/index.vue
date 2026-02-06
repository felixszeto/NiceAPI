<template>
  <el-container class="layout-container">
    <el-aside :width="isCollapse ? (isMobile ? '0' : '64px') : '200px'" class="aside-container" :class="{ 'mobile-hidden': isMobile && isCollapse }">
      <el-menu
        :default-active="activeMenu"
        class="el-menu-vertical"
        router
        :collapse="isCollapse"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <div class="menu-logo">
          <img src="/favicon.png" alt="logo" class="small-logo" />
        </div>
        <el-menu-item index="/dashboard">
          <el-icon><DataBoard /></el-icon>
          <span>儀表板</span>
        </el-menu-item>
        <el-menu-item index="/providers">
          <el-icon><Connection /></el-icon>
          <span>供應商管理</span>
        </el-menu-item>
        <el-menu-item index="/groups">
          <el-icon><Files /></el-icon>
          <span>群組管理</span>
        </el-menu-item>
        <el-menu-item index="/api-keys">
          <el-icon><Key /></el-icon>
          <span>API 金鑰</span>
        </el-menu-item>
        <el-menu-item index="/keywords">
          <el-icon><Filter /></el-icon>
          <span>關鍵字過濾</span>
        </el-menu-item>
        <el-menu-item index="/logs">
          <el-icon><Document /></el-icon>
          <span>調用日誌</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>系統設置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="layout-header">
        <div class="header-left">
          <el-icon class="toggle-icon" @click="isCollapse = !isCollapse">
            <component :is="isCollapse ? icons.Expand : icons.Fold" />
          </el-icon>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="el-dropdown-link">
              管理員 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </span>
            <template #header></template>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">登出</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
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
  Fold
} from '@element-plus/icons-vue'

const route = useRoute()
const userStore = useUserStore()

// 註冊組件以供 <component :is /> 使用，解決 TS6133 錯誤
const icons = {
  Expand,
  Fold
}

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

const handleCommand = (command: string) => {
  if (command === 'logout') {
    userStore.logout()
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.el-menu-vertical {
  height: 100%;
  border-right: none;
}

.menu-logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
  font-size: 18px;
  background-color: #2b2f3a;
}

.small-logo {
  width: 30px;
  height: 30px;
  margin-right: 10px;
}

.layout-header {
  background-color: white;
  border-bottom: 1px solid #dcdfe6;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.toggle-icon {
  font-size: 20px;
  cursor: pointer;
  color: #606266;
}

.aside-container {
  transition: width 0.3s;
  overflow: hidden;
}

.mobile-hidden {
  width: 0 !important;
}

.header-right {
  cursor: pointer;
}
</style>