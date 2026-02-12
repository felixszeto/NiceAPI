<template>
  <div class="space-y-6">
    <!-- 頁面標題列 -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h1 class="text-xl font-semibold text-gray-900">調用日誌</h1>
        <p class="text-sm text-gray-500 mt-1">查看 API 請求與回應的詳細歷史紀錄</p>
      </div>
      <div class="flex items-center gap-2 self-end sm:self-auto">
        <el-button :icon="Refresh" @click="fetchLogs" :loading="loading" circle />
      </div>
    </div>

    <!-- 標籤頁過濾 -->
    <div class="bg-white rounded-xl border border-gray-200 p-1 flex items-center shadow-sm">
      <div
        v-for="tab in tabs"
        :key="tab.name"
        class="flex-1 text-center py-2 px-3 rounded-lg cursor-pointer transition-all text-sm font-medium"
        :class="activeTab === tab.name ? 'bg-blue-50 text-blue-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'"
        @click="handleTabChange(tab.name)"
      >
        {{ tab.label }}
      </div>
    </div>

    <!-- 桌面端表格 -->
    <div class="hidden lg:block bg-white rounded-xl border border-gray-200 overflow-hidden">
      <el-table :data="logs" v-loading="loading" size="small" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="API 金鑰" width="140">
          <template #default="scope">
            <code class="text-[10px] bg-gray-100 px-1.5 py-0.5 rounded font-mono text-gray-600">
              {{ formatApiKey(scope.row) }}
            </code>
          </template>
        </el-table-column>
        <el-table-column label="模型" min-width="150" show-overflow-tooltip>
          <template #default="scope">
            <span class="font-medium text-gray-700">{{ getModelName(scope.row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="狀態" width="90" align="center">
          <template #default="scope">
            <div class="flex flex-col items-center">
              <el-tag
                :type="scope.row.is_success ? 'success' : 'danger'"
                size="small"
                effect="light"
                class="!rounded-md"
              >
                {{ scope.row.status_code }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="耗時" width="100" align="right">
          <template #default="scope">
            <span :class="scope.row.response_time_ms > 10000 ? 'text-amber-600 font-medium' : 'text-gray-600'">
              {{ scope.row.response_time_ms }} ms
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="total_tokens" label="Tokens" width="90" align="right" />
        <el-table-column label="費用" width="110" align="right">
          <template #default="scope">
            <span class="text-xs text-gray-500 font-mono">
              ${{ scope.row.cost !== null ? scope.row.cost.toFixed(6) : '0.000000' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="時間" width="160">
          <template #default="scope">
            <span class="text-[11px] text-gray-400">{{ formatDateTime(scope.row.request_timestamp) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center" fixed="right">
          <template #default="scope">
            <el-button type="primary" link :icon="View" size="small" @click="showDetails(scope.row)" />
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 移動端/中尺寸卡片 -->
    <div class="lg:hidden space-y-3" v-loading="loading">
      <div
        v-for="row in logs"
        :key="row.id"
        class="bg-white rounded-xl border border-gray-200 p-4 space-y-3 hover:shadow-md transition-shadow cursor-pointer"
        @click="showDetails(row)"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-xs font-bold text-gray-400">#{{ row.id }}</span>
            <span class="font-semibold text-sm text-gray-900 truncate max-w-[150px]">{{ getModelName(row) }}</span>
          </div>
          <el-tag
            :type="row.is_success ? 'success' : 'danger'"
            size="small"
            class="!rounded-md"
          >
            {{ row.status_code }}
          </el-tag>
        </div>

        <div class="grid grid-cols-3 gap-2 py-2 border-y border-gray-50">
          <div class="text-center">
            <div class="text-[10px] text-gray-400 uppercase">耗時</div>
            <div class="text-xs font-medium text-gray-700 mt-0.5">{{ row.response_time_ms }}ms</div>
          </div>
          <div class="text-center">
            <div class="text-[10px] text-gray-400 uppercase">Tokens</div>
            <div class="text-xs font-medium text-gray-700 mt-0.5">{{ row.total_tokens || 0 }}</div>
          </div>
          <div class="text-center">
            <div class="text-[10px] text-gray-400 uppercase">費用</div>
            <div class="text-xs font-medium text-gray-700 mt-0.5">${{ row.cost?.toFixed(4) || '0.00' }}</div>
          </div>
        </div>

        <div class="flex items-center justify-between">
          <span class="text-[10px] text-gray-400">{{ formatDateTime(row.request_timestamp) }}</span>
          <code class="text-[10px] bg-gray-50 px-1.5 py-0.5 rounded font-mono text-gray-400">
            {{ formatApiKey(row) }}
          </code>
        </div>
      </div>

      <div v-if="!loading && logs.length === 0" class="text-center py-16">
        <el-icon :size="48" class="text-gray-300 mb-3"><Document /></el-icon>
        <p class="text-gray-400">暫無調用日誌</p>
      </div>
    </div>

    <!-- 分頁 -->
    <div v-if="total > 0" class="flex justify-end mt-4">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[20, 50, 100]"
        :layout="isMobile ? 'total, prev, next' : 'total, sizes, prev, pager, next'"
        :total="total"
        :small="isMobile"
        @size-change="fetchLogs"
        @current-change="fetchLogs"
      />
    </div>

    <!-- 詳情對話框 -->
    <el-dialog
      v-model="detailsVisible"
      title="調用詳情"
      :width="isMobile ? '95%' : '850px'"
      :fullscreen="isMobile"
      destroy-on-close
      class="log-detail-dialog"
    >
      <div v-if="currentLog" class="space-y-6">
        <!-- 頂部摘要卡片 -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-gray-50 p-4 rounded-xl border border-gray-100">
          <div class="space-y-1">
            <div class="text-[10px] text-gray-400 font-bold uppercase">狀態</div>
            <div class="flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full" :class="currentLog.is_success ? 'bg-green-500' : 'bg-red-500'"></span>
              <span class="text-sm font-bold" :class="currentLog.is_success ? 'text-green-600' : 'text-red-600'">
                {{ currentLog.status_code }}
              </span>
            </div>
          </div>
          <div class="space-y-1">
            <div class="text-[10px] text-gray-400 font-bold uppercase">總耗時</div>
            <div class="text-sm font-bold text-gray-900">{{ currentLog.response_time_ms }} ms</div>
          </div>
          <div class="space-y-1">
            <div class="text-[10px] text-gray-400 font-bold uppercase">Tokens</div>
            <div class="text-sm font-bold text-gray-900">{{ currentLog.total_tokens || 0 }}</div>
          </div>
          <div class="space-y-1">
            <div class="text-[10px] text-gray-400 font-bold uppercase">費用</div>
            <div class="text-sm font-bold text-gray-900">${{ currentLog.cost?.toFixed(6) || '0.000000' }}</div>
          </div>
        </div>

        <!-- 詳細摺疊面板 -->
        <div v-loading="detailsLoading" class="border rounded-xl border-gray-200 overflow-hidden">
          <el-collapse v-model="activeCollapseNames" class="!border-none">
            <!-- 請求文本 -->
            <el-collapse-item name="2">
              <template #title>
                <div class="flex items-center justify-between w-full pr-4 px-4">
                  <div class="flex items-center gap-2">
                    <el-icon class="text-blue-500"><ChatLineRound /></el-icon>
                    <span class="font-semibold text-gray-700">對話內容 (Parsed)</span>
                  </div>
                  <el-button type="primary" link size="small" :icon="DocumentCopy" @click.stop="copyText(extractText(currentLog.request_body, true))">複製</el-button>
                </div>
              </template>
              <div class="p-4 bg-gray-50 border-t border-gray-100">
                <div class="text-xs text-gray-600 leading-relaxed whitespace-pre-wrap font-sans">
                  {{ extractText(currentLog.request_body, true) }}
                </div>
              </div>
            </el-collapse-item>

            <!-- 響應文本 -->
            <el-collapse-item name="4">
              <template #title>
                <div class="flex items-center justify-between w-full pr-4 px-4">
                  <div class="flex items-center gap-2">
                    <el-icon class="text-green-500"><CircleCheck /></el-icon>
                    <span class="font-semibold text-gray-700">回答文本 (Assistant)</span>
                  </div>
                  <el-button type="primary" link size="small" :icon="DocumentCopy" @click.stop="copyText(extractText(currentLog.response_body, false))">複製</el-button>
                </div>
              </template>
              <div class="p-4 bg-gray-50 border-t border-gray-100">
                <div class="text-xs text-gray-600 leading-relaxed whitespace-pre-wrap font-sans">
                  {{ extractText(currentLog.response_body, false) }}
                </div>
              </div>
            </el-collapse-item>

            <!-- 原始 JSON -->
            <el-collapse-item name="1">
              <template #title>
                <div class="flex items-center justify-between w-full pr-4 px-4">
                  <div class="flex items-center gap-2">
                    <el-icon class="text-gray-400"><Cpu /></el-icon>
                    <span class="font-semibold text-gray-700">原始請求 JSON</span>
                  </div>
                  <el-button type="primary" link size="small" :icon="DocumentCopy" @click.stop="copyText(currentLog.request_body)">複製</el-button>
                </div>
              </template>
              <div class="bg-slate-900 p-4 border-t border-gray-800">
                <pre class="text-[11px] text-blue-300 font-mono overflow-auto max-h-[300px]">{{ formatJson(currentLog.request_body) }}</pre>
              </div>
            </el-collapse-item>

            <el-collapse-item name="3">
              <template #title>
                <div class="flex items-center justify-between w-full pr-4 px-4">
                  <div class="flex items-center gap-2">
                    <el-icon class="text-gray-400"><Cpu /></el-icon>
                    <span class="font-semibold text-gray-700">原始響應 JSON</span>
                  </div>
                  <el-button type="primary" link size="small" :icon="DocumentCopy" @click.stop="copyText(currentLog.response_body)">複製</el-button>
                </div>
              </template>
              <div class="bg-slate-900 p-4 border-t border-gray-800">
                <pre class="text-[11px] text-green-300 font-mono overflow-auto max-h-[300px]">{{ formatJson(currentLog.response_body) }}</pre>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>

        <!-- 錯誤訊息 -->
        <div v-if="currentLog.error_message" class="space-y-2">
          <div class="text-xs font-bold text-red-500 uppercase">錯誤訊息</div>
          <div class="p-3 bg-red-50 border border-red-100 rounded-lg text-xs text-red-700 font-mono break-all whitespace-pre-wrap">
            {{ currentLog.error_message }}
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="detailsVisible = false" class="w-full sm:w-auto">關閉詳情</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import request from '../../utils/request'
import { ElMessage } from 'element-plus'
import { 
  Refresh, View, Document, DocumentCopy, 
  ChatLineRound, CircleCheck, Cpu 
} from '@element-plus/icons-vue'

const screenWidth = ref(window.innerWidth)
const isMobile = computed(() => screenWidth.value < 768)
const onResize = () => { screenWidth.value = window.innerWidth }

const logs = ref<any[]>([])
const loading = ref(false)
const detailsLoading = ref(false)
const activeTab = ref('all')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const detailsVisible = ref(false)
const currentLog = ref<any>(null)
const activeCollapseNames = ref(['2', '4'])

const tabs = [
  { label: '全部請求', name: 'all' },
  { label: '成功', name: 'successful' },
  { label: '失敗', name: 'failed' }
]

const handleTabChange = (name: string) => {
  activeTab.value = name
  currentPage.value = 1
  fetchLogs()
}

const fetchLogs = async () => {
  loading.value = true
  try {
    const skip = (currentPage.value - 1) * pageSize.value
    const params: any = {
      skip,
      limit: pageSize.value
    }
    if (activeTab.value === 'successful') params.filter_success = true
    if (activeTab.value === 'failed') params.filter_success = false

    const data: any = await request.get('logs/', { params })
    logs.value = data.items
    total.value = data.total
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const formatApiKey = (row: any) => {
  if (row.api_key_display) return row.api_key_display
  if (row.api_key?.key) return `${row.api_key.key.slice(0, 5)}...${row.api_key.key.slice(-4)}`
  return 'N/A'
}

const getModelName = (row: any) => {
  if (row.provider?.model) return row.provider.model
  if (row.request_body) {
    try {
      const body = JSON.parse(row.request_body)
      return body.model || 'N/A'
    } catch {
      const match = row.request_body.match(/"model":\s*"([^"]*)"/)
      return match ? match[1] : 'N/A'
    }
  }
  return 'N/A'
}

const formatDateTime = (ts: string) => {
  if (!ts) return '-'
  return new Date(ts).toLocaleString()
}

const formatJson = (jsonStr: string) => {
  if (!jsonStr) return '無數據'
  try {
    return JSON.stringify(JSON.parse(jsonStr), null, 2)
  } catch {
    return jsonStr
  }
}

const extractText = (bodyStr: string, isReq: boolean) => {
  if (!bodyStr) return ''
  try {
    const data = JSON.parse(bodyStr)
    if (isReq) {
      return (data.messages || []).map((m: any) => `[${m.role}]: ${m.content}`).join('\n')
    }
    return data.choices?.[0]?.message?.content || ''
  } catch {
    if (!isReq) {
      const match = bodyStr.match(/"content":\s*"([^"]*)"/g)
      if (match) return match.map(m => m.replace(/"content":\s*"/, '').slice(0, -1)).join('').replace(/\\n/g, '\n')
    }
    return bodyStr
  }
}

const showDetails = async (log: any) => {
  currentLog.value = log
  detailsVisible.value = true
  detailsLoading.value = true
  
  try {
    const data: any = await request.get(`logs/${log.id}`)
    currentLog.value = { ...log, ...data }
  } catch (error) {
    console.error('獲取詳情失敗:', error)
    ElMessage.error('獲取詳情失敗')
  } finally {
    detailsLoading.value = false
  }
}

const copyText = (text: any) => {
  if (!text) {
    ElMessage.warning('無內容可複製')
    return
  }
  const textToCopy = typeof text === 'string' ? text : JSON.stringify(text, null, 2)
  navigator.clipboard.writeText(textToCopy).then(() => {
    ElMessage.success('已複製到剪貼簿')
  }).catch(err => {
    console.error('複製失敗:', err)
    ElMessage.error('複製失敗')
  })
}

onMounted(() => {
  fetchLogs()
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.log-detail-dialog :deep(.el-collapse-item__header) {
  height: auto;
  line-height: normal;
  padding: 12px 0;
}
</style>