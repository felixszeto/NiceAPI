<template>
  <div class="remote-root">
    <div class="glass-bg"></div>
    
    <header class="remote-nav">
      <div class="nav-content">
        <div class="logo-area">
          <div class="logo-dot"></div>
          <h1>遠端控制中心</h1>
        </div>
        <div class="status-badge" v-if="apiKey">
          <span class="pulse"></span> 在線
        </div>
      </div>
    </header>

    <main class="remote-main" v-loading="loading" element-loading-background="rgba(255,255,255,0.1)">
      <div v-if="!apiKey" class="auth-error">
        <el-icon size="64" color="#ff4d4f"><Lock /></el-icon>
        <h2>存取受限</h2>
        <p>請使用授權連結進入此頁面</p>
      </div>

      <div v-else class="groups-container">
        <div v-for="group in groups" :key="group.id" class="group-wrapper">
          <div class="group-header">
            <div class="title-wrap">
              <span class="group-id">#{{ group.id }}</span>
              <h2>{{ group.name }}</h2>
            </div>
            <p class="hint">按住並拖拽可調整優先級</p>
          </div>

          <draggable
            v-model="group.providers"
            item-key="id"
            class="model-list"
            @change="() => handleOrderChange(group)"
            :animation="300"
            ghost-class="ghost-card"
            chosen-class="chosen-card"
          >
            <template #item="{ element, index }">
              <div class="model-item" :class="{ 'is-top': index === 0 }">
                <div class="rank-num">P{{ index + 1 }}</div>
                <div class="info-content">
                  <div class="model-id">{{ element.model }}</div>
                  <div class="provider-name">{{ element.name }}</div>
                </div>
                <div class="active-dot" v-if="index === 0">
                  <el-icon color="#52c41a"><CircleCheckFilled /></el-icon>
                </div>
              </div>
            </template>
          </draggable>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import draggable from 'vuedraggable'
import { Lock, CircleCheckFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import request from '../../utils/request'

interface Provider {
  id: number
  name: string
  model: string
  priority: number
}

interface Group {
  id: number
  name: string
  providers: Provider[]
}

const route = useRoute()
const apiKey = ref('')
const groups = ref<Group[]>([])
const loading = ref(false)

const fetchStatus = async () => {
  if (!apiKey.value) return
  loading.value = true
  try {
    const data: any = await request.get('remote/status', {
      params: { api_key: apiKey.value }
    })
    groups.value = data
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '獲取狀態失敗')
  } finally {
    loading.value = false
  }
}

const handleOrderChange = async (group: Group) => {
  try {
    const providerIds = group.providers.map(p => p.id)
    await request.post('remote/update-order', providerIds, {
      params: {
        api_key: apiKey.value,
        group_id: group.id
      }
    })
    ElMessage.success({
      message: `${group.name} 順序已更新`,
      duration: 1500,
      offset: 50
    })
  } catch (error) {
    ElMessage.error('同步失敗，請刷新頁面')
  }
}

onMounted(() => {
  const key = route.query.key as string
  if (key) {
    apiKey.value = key
    localStorage.setItem('remote_api_key', key)
  } else {
    apiKey.value = localStorage.getItem('remote_api_key') || ''
  }
  
  if (apiKey.value) {
    fetchStatus()
  }
})
</script>

<style scoped>
.remote-root {
  min-height: 100vh;
  background-color: #0f172a;
  color: #f8fafc;
  font-family: 'Inter', -apple-system, sans-serif;
  position: relative;
  overflow-x: hidden;
}

.glass-bg {
  position: fixed;
  top: -10%;
  right: -10%;
  width: 40%;
  height: 40%;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.15) 0%, rgba(0, 0, 0, 0) 70%);
  z-index: 0;
  pointer-events: none;
}

.remote-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(12px);
  background: rgba(15, 23, 42, 0.8);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.nav-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-dot {
  width: 12px;
  height: 12px;
  background: #3b82f6;
  border-radius: 50%;
  box-shadow: 0 0 15px #3b82f6;
}

.logo-area h1 {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0;
  letter-spacing: -0.025em;
}

.status-badge {
  background: rgba(52, 211, 153, 0.1);
  color: #34d399;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  border: 1px solid rgba(52, 211, 153, 0.2);
}

.pulse {
  width: 8px;
  height: 8px;
  background: #34d399;
  border-radius: 50%;
  animation: pulse-ring 2s infinite;
}

@keyframes pulse-ring {
  0% { transform: scale(0.9); opacity: 1; }
  70% { transform: scale(1.5); opacity: 0; }
  100% { transform: scale(0.9); opacity: 0; }
}

.remote-main {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem 1rem;
  position: relative;
  z-index: 1;
}

.group-wrapper {
  margin-bottom: 3rem;
}

.group-header {
  margin-bottom: 1.25rem;
}

.title-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.group-id {
  color: #3b82f6;
  font-weight: 800;
  font-size: 1.1rem;
}

.group-header h2 {
  font-size: 1.5rem;
  margin: 0;
}

.hint {
  color: #94a3b8;
  font-size: 0.875rem;
}

.model-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.model-item {
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 1.2rem;
  display: flex;
  align-items: center;
  gap: 20px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
  cursor: grab;
}

.model-item:active {
  cursor: grabbing;
}

.model-item.is-top {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(30, 41, 59, 0.7));
  border-color: rgba(59, 130, 246, 0.3);
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
}

.rank-num {
  font-size: 0.875rem;
  font-weight: 800;
  color: #64748b;
  min-width: 24px;
}

.is-top .rank-num { color: #3b82f6; }

.info-content {
  flex-grow: 1;
  min-width: 0;
}

.model-id {
  font-weight: 600;
  font-size: 1.05rem;
  margin-bottom: 4px;
  word-break: break-all;
  line-height: 1.4;
}

.provider-name {
  color: #94a3b8;
  font-size: 0.8rem;
  word-break: break-all;
  line-height: 1.2;
}

.auth-error {
  text-align: center;
  padding-top: 10vh;
}

.auth-error h2 { margin: 1.5rem 0 0.5rem; }
.auth-error p { color: #94a3b8; }

.ghost-card {
  opacity: 0.3;
  transform: scale(0.95);
}

.chosen-card {
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
  border-color: rgba(59, 130, 246, 0.5);
}

/* 適配手機 */
@media (max-width: 640px) {
  .remote-main { padding: 1rem; }
  .model-item { padding: 0.75rem; gap: 10px; }
  .group-header h2 { font-size: 1.25rem; }
}
</style>