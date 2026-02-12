<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <!-- 頁面標題列 -->
    <div class="flex flex-col gap-1">
      <h1 class="text-xl font-semibold text-gray-900">系統設置</h1>
      <p class="text-sm text-gray-500">管理 API 閘道的全域行為與自動化規則</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <!-- 左側導航/資訊 -->
      <div class="md:col-span-1 space-y-4">
        <div class="bg-blue-50 rounded-2xl p-6 border border-blue-100">
          <div class="w-12 h-12 bg-blue-500 rounded-xl flex items-center justify-center mb-4 shadow-lg shadow-blue-200">
            <el-icon size="24" class="text-white"><Operation /></el-icon>
          </div>
          <h3 class="font-bold text-blue-900 mb-2">故障轉移機制</h3>
          <p class="text-xs text-blue-700 leading-relaxed">
            系統會自動監測各供應商的調用狀態。當某供應商在設定的時間週期內連續失敗次數超過閾值，將自動被暫時禁用並轉移請求至優先級次高的供應商。
          </p>
        </div>
        
        <div class="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
          <h4 class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">系統資訊</h4>
          <div class="space-y-3">
            <div class="flex justify-between items-center">
              <span class="text-sm text-gray-500">當前版本</span>
              <el-tag size="small" effect="plain" class="!rounded-md">v2.0.0-stable</el-tag>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-sm text-gray-500">核心引擎</span>
              <span class="text-sm font-medium text-gray-700">Go/Node.js Hybrid</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右側設置表單 -->
      <div class="md:col-span-2 space-y-6">
        <div class="bg-white rounded-3xl border border-gray-200 shadow-sm overflow-hidden" v-loading="loading">
          <div class="px-6 py-5 border-b border-gray-100 bg-gray-50/50">
            <h2 class="text-base font-bold text-gray-900">核心自動化參數</h2>
          </div>
          
          <div class="p-8">
            <el-form :model="settings" label-position="top" class="space-y-8">
              <!-- 閾值次數 -->
              <div class="group">
                <div class="flex items-center justify-between mb-3">
                  <label class="text-sm font-bold text-gray-700 group-focus-within:text-blue-600 transition-colors">故障次數閾值</label>
                  <el-tag size="small" type="info" class="!rounded-md !border-none bg-gray-100 text-gray-500">次數</el-tag>
                </div>
                <div class="relative">
                  <el-input-number 
                    v-model="settings.failover_threshold_count" 
                    :min="1" 
                    controls-position="right"
                    class="!w-full !h-12 big-input-number"
                  />
                </div>
                <p class="mt-2 text-xs text-gray-400 leading-relaxed italic">
                  * 建議值：2-5 次。過低可能因網絡抖動頻繁切換，過高則反應遲鈍。
                </p>
              </div>

              <!-- 統計週期 -->
              <div class="group">
                <div class="flex items-center justify-between mb-3">
                  <label class="text-sm font-bold text-gray-700 group-focus-within:text-blue-600 transition-colors">故障統計週期</label>
                  <el-tag size="small" type="info" class="!rounded-md !border-none bg-gray-100 text-gray-500">分鐘</el-tag>
                </div>
                <div class="relative">
                  <el-input-number 
                    v-model="settings.failover_threshold_period_minutes" 
                    :min="1" 
                    controls-position="right"
                    class="!w-full !h-12 big-input-number"
                  />
                </div>
                <p class="mt-2 text-xs text-gray-400 leading-relaxed italic">
                  * 此時間窗內累積的失敗次數若達到上方閾值即觸發熔斷。
                </p>
              </div>

              <div class="pt-6 border-t border-gray-100">
                <el-button 
                  type="primary" 
                  @click="saveSettings" 
                  size="large" 
                  class="!w-full !rounded-2xl !h-14 !text-base font-bold shadow-lg shadow-blue-500/20"
                  :loading="saving"
                >
                  套用變更
                </el-button>
                <p class="text-center mt-4 text-[10px] text-gray-400 font-medium uppercase tracking-widest">
                  Changes will take effect immediately for new requests
                </p>
              </div>
            </el-form>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import request from '../../utils/request'
import { ElMessage } from 'element-plus'
import { Operation } from '@element-plus/icons-vue'

const loading = ref(false)
const saving = ref(false)
const settings = ref({
  failover_threshold_count: 2,
  failover_threshold_period_minutes: 5
})

const fetchSettings = async () => {
  loading.value = true
  try {
    const count: any = await request.get('settings/failover_threshold_count')
    const period: any = await request.get('settings/failover_threshold_period_minutes')
    settings.value.failover_threshold_count = parseInt(count.value)
    settings.value.failover_threshold_period_minutes = parseInt(period.value)
  } catch (error) {
    console.error(error)
    ElMessage.error('無法從伺服器獲取設置')
  } finally {
    loading.value = false
  }
}

const saveSettings = async () => {
  saving.value = true
  try {
    await request.post('settings/', {
      key: 'failover_threshold_count',
      value: settings.value.failover_threshold_count.toString()
    })
    await request.post('settings/', {
      key: 'failover_threshold_period_minutes',
      value: settings.value.failover_threshold_period_minutes.toString()
    })
    ElMessage({
      message: '系統設置已更新並套用',
      type: 'success',
      plain: true
    })
  } catch (error) {
    console.error(error)
    ElMessage.error('保存失敗，請檢查網絡連接')
  } finally {
    saving.value = false
  }
}

onMounted(fetchSettings)
</script>

<style scoped>
@reference "../../style.css";

.big-input-number :deep(.el-input__wrapper) {
  @apply rounded-xl border-gray-200 bg-gray-50/50 shadow-none hover:bg-white focus-within:bg-white focus-within:ring-2 focus-within:ring-blue-500/20 transition-all;
}

.big-input-number :deep(.el-input-number__increase),
.big-input-number :deep(.el-input-number__decrease) {
  @apply bg-transparent border-none w-10;
}

.big-input-number :deep(.el-input__inner) {
  @apply text-left font-mono font-bold text-gray-700;
}
</style>