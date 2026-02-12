<template>
  <div class="min-h-screen bg-slate-950 text-slate-50 selection:bg-blue-500/30 font-sans relative overflow-x-hidden">
    <!-- 背景裝飾 -->
    <div class="fixed top-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-600/10 blur-[120px] rounded-full pointer-events-none z-0"></div>
    <div class="fixed bottom-[-10%] left-[-10%] w-[30%] h-[30%] bg-indigo-600/10 blur-[100px] rounded-full pointer-events-none z-0"></div>

    <!-- 頂部導航 -->
    <header class="sticky top-0 z-50 backdrop-blur-md bg-slate-950/80 border-b border-white/5">
      <div class="max-w-2xl mx-auto px-4 h-16 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-2.5 h-2.5 bg-blue-500 rounded-full shadow-[0_0_12px_rgba(59,130,246,0.8)]"></div>
          <h1 class="text-lg font-bold tracking-tight">遠端控制中心</h1>
        </div>
        <div v-if="apiKey" class="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-3 py-1 rounded-full text-xs font-semibold">
          <span class="relative flex h-2 w-2">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          在線授權
        </div>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-8 relative z-10" v-loading="loading" element-loading-background="transparent">
      <!-- 未授權狀態 -->
      <div v-if="!apiKey" class="flex flex-col items-center justify-center py-20 text-center space-y-4">
        <div class="w-20 h-20 bg-red-500/10 rounded-3xl flex items-center justify-center mb-2">
          <el-icon size="40" class="text-red-500"><Lock /></el-icon>
        </div>
        <h2 class="text-2xl font-bold">存取受限</h2>
        <p class="text-slate-400 max-w-xs mx-auto">此頁面需要有效的授權金鑰方可存取。請使用原始連結進入。</p>
      </div>

      <!-- 群組與清單 -->
      <div v-else class="space-y-12">
        <div v-for="group in groups" :key="group.id" class="group-section">
          <!-- 群組頭部 -->
          <div class="flex items-end justify-between mb-4 px-1">
            <div class="space-y-1">
              <div class="flex items-center gap-2">
                <span class="text-blue-500 font-black text-lg">#{{ group.id }}</span>
                <h2 class="text-xl font-bold">{{ group.name }}</h2>
              </div>
              <p class="text-xs text-slate-500">當前負載均衡策略：優先級輪詢</p>
            </div>
            <span class="text-[10px] text-slate-500 font-medium uppercase tracking-widest bg-white/5 px-2 py-1 rounded">可拖拽</span>
          </div>

          <!-- 拖拽清單 -->
          <draggable
            v-model="group.providers"
            item-key="id"
            tag="div"
            class="space-y-3"
            @change="() => handleOrderChange(group)"
            :animation="250"
            ghost-class="drag-ghost"
            chosen-class="drag-chosen"
            drag-class="drag-fallback"
            :force-fallback="true"
            fallback-tolerance="0"
          >
            <template #item="{ element, index }">
              <div
                class="group/item relative bg-slate-900/50 hover:bg-slate-800/60 border border-white/5 hover:border-blue-500/30 rounded-2xl p-4 flex items-center gap-4 cursor-grab active:cursor-grabbing select-none"
                :class="{ 'ring-1 ring-blue-500/50 bg-slate-800/80': index === 0 }"
              >
                <!-- 排名標籤 -->
                <div class="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center font-black text-sm transition-colors"
                     :class="index === 0 ? 'bg-blue-500 text-white' : 'bg-slate-800 text-slate-500 group-hover/item:text-slate-300'">
                  {{ index + 1 }}
                </div>

                <!-- 資訊 -->
                <div class="flex-grow min-w-0">
                  <h3 class="font-bold text-slate-100 truncate group-hover/item:text-white transition-colors">{{ element.model }}</h3>
                  <p class="text-xs text-slate-500 truncate mt-0.5">{{ element.name }}</p>
                </div>

                <!-- 狀態指示 -->
                <div v-if="index === 0" class="flex-shrink-0">
                  <div class="flex items-center gap-1.5 bg-blue-500/10 text-blue-400 px-2.5 py-1 rounded-lg border border-blue-500/20 shadow-sm">
                    <el-icon size="14"><CircleCheckFilled /></el-icon>
                    <span class="text-[10px] font-bold uppercase tracking-tight">主供應商</span>
                  </div>
                </div>

                <!-- 裝飾線條 -->
                <div v-if="index === 0" class="absolute -inset-[1px] bg-gradient-to-r from-blue-500/20 to-indigo-500/20 rounded-2xl -z-10 blur-sm"></div>
              </div>
            </template>
          </draggable>
        </div>
      </div>

      <!-- 空狀態 -->
      <div v-if="apiKey && !loading && groups.length === 0" class="py-20 text-center">
        <el-icon size="48" class="text-slate-700 mb-4"><DataBoard /></el-icon>
        <p class="text-slate-500">目前沒有分配任何供應商群組</p>
      </div>
    </main>

    <!-- 底部版權 -->
    <footer class="py-12 border-t border-white/5 relative z-10">
      <div class="max-w-2xl mx-auto px-4 text-center">
        <p class="text-[10px] text-slate-600 uppercase tracking-[0.2em] font-bold">NiceAPI Remote Protocol v2.0</p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import draggable from 'vuedraggable'
import { Lock, CircleCheckFilled, DataBoard } from '@element-plus/icons-vue'
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
    ElMessage({
      message: `${group.name} 優先級已同步`,
      type: 'success',
      duration: 2000,
      plain: true,
      customClass: 'remote-toast'
    })
  } catch (error) {
    ElMessage.error('同步失敗，請嘗試刷新頁面')
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
/* 拖拽時留在原處引導排序的佔位符 (Ghost) */
.drag-ghost {
  opacity: 0.2 !important;
  background: rgba(59, 130, 246, 0.1) !important;
  border: 2px dashed #3b82f6 !important;
  border-radius: 1rem !important;
}

/* 選中元素樣式 (Chosen) */
.drag-chosen {
  cursor: grabbing !important;
}

/* 實際跟隨滑鼠移動的鏡像元素 (Fallback/Drag) */
.drag-fallback {
  opacity: 0.9 !important;
  box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.5), 0 10px 10px -5px rgb(0 0 0 / 0.4) !important;
  border-color: #3b82f6 !important;
  background-color: #1e293b !important;
  pointer-events: none;
  z-index: 9999;
  /* 移除 Transform/Transition 以免干擾 Fallback 定位邏輯 */
  transform: none !important;
  transition: none !important;
}

/* 全域覆蓋 Element Plus 在此頁面的樣式以維持暗色調 */
.remote-toast {
  background-color: #1e293b !important;
  border-color: #3b82f6 !important;
  color: #3b82f6 !important;
}

body {
  background-color: #020617;
}
</style>