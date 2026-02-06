<template>
  <div class="logs-container">
    <div class="header">
      <div class="title-row">
        <h2>調用日誌</h2>
        <el-button type="primary" link icon="Refresh" :loading="loading" @click="fetchLogs">刷新</el-button>
      </div>
      <div class="tabs-row">
        <el-tabs v-model="activeTab" @tab-change="handleTabChange">
          <el-tab-pane label="全部請求" name="all" />
          <el-tab-pane label="成功請求" name="successful" />
          <el-tab-pane label="失敗請求" name="failed" />
        </el-tabs>
      </div>
    </div>

    <el-table :data="logs" style="width: 100%" v-loading="loading" size="small" border stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="API 金鑰" width="140">
        <template #default="scope">
          <code>{{ formatApiKey(scope.row) }}</code>
        </template>
      </el-table-column>
      <el-table-column label="模型" width="150" show-overflow-tooltip>
        <template #default="scope">
          {{ getModelName(scope.row) }}
        </template>
      </el-table-column>
      <el-table-column label="請求位址" min-width="180" show-overflow-tooltip>
        <template #default="scope">
          {{ scope.row.provider?.api_endpoint || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="時間" width="160">
        <template #default="scope">
          {{ formatDateTime(scope.row.request_timestamp) }}
        </template>
      </el-table-column>
      <el-table-column label="成功" width="70" align="center">
        <template #default="scope">
          <el-icon :color="scope.row.is_success ? '#67C23A' : '#F56C6C'">
            <component :is="scope.row.is_success ? 'Check' : 'Close'" />
          </el-icon>
        </template>
      </el-table-column>
      <el-table-column prop="status_code" label="狀態碼" width="80" align="center" />
      <el-table-column prop="response_time_ms" label="耗時(ms)" width="100" align="right" />
      <el-table-column prop="total_tokens" label="Tokens" width="100" align="right" />
      <el-table-column label="費用" width="100" align="right">
        <template #default="scope">
          {{ scope.row.cost !== null ? scope.row.cost.toFixed(6) : 'N/A' }}
        </template>
      </el-table-column>
      <el-table-column prop="error_message" label="錯誤訊息" show-overflow-tooltip>
        <template #default="scope">
          <el-button v-if="scope.row.error_message" type="danger" link size="small" @click="showError(scope.row)">
            詳情
          </el-button>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80" align="center">
        <template #default="scope">
          <el-button type="primary" link icon="View" @click="showDetails(scope.row)" />
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        :total="total"
        @size-change="fetchLogs"
        @current-change="fetchLogs"
      />
    </div>

    <!-- 詳情對話框 -->
    <!-- 詳情對話框 -->
    <el-dialog v-model="detailsVisible" title="調用詳情" :width="windowWidth < 850 ? '95%' : '800px'" top="5vh" destroy-on-close>
      <div v-if="currentLog" class="log-details">
        <!-- 基本資訊摘要 (即使在加載 Body 時也先行顯示) -->
        <div class="log-info-grid">
          <div class="info-item">
            <span class="label">ID:</span>
            <span class="value">#{{ currentLog.id }}</span>
          </div>
          <div class="info-item">
            <span class="label">狀態:</span>
            <el-tag :type="currentLog.is_success ? 'success' : 'danger'" size="small">
              {{ currentLog.is_success ? '成功' : '失敗' }} ({{ currentLog.status_code }})
            </el-tag>
          </div>
          <div class="info-item">
            <span class="label">耗時:</span>
            <span class="value">{{ currentLog.response_time_ms }} ms</span>
          </div>
          <div class="info-item">
            <span class="label">Tokens:</span>
            <span class="value">{{ currentLog.total_tokens || 0 }}</span>
          </div>
          <div class="info-item">
            <span class="label">模型:</span>
            <span class="value">{{ currentLog.provider?.model || 'N/A' }}</span>
          </div>
          <div class="info-item">
            <span class="label">費用:</span>
            <span class="value">${{ currentLog.cost?.toFixed(6) || '0.000000' }}</span>
          </div>
          <div class="info-item" style="grid-column: span 2">
            <span class="label">請求時間:</span>
            <span class="value">{{ formatDateTime(currentLog.request_timestamp) }}</span>
          </div>
        </div>

        <div v-loading="detailsLoading" element-loading-text="正在獲取完整日誌詳情...">
          <el-collapse v-model="activeCollapseNames">
          <el-collapse-item name="1">
            <template #title>
              <div class="collapse-title">
                <span>請求內容 (Request Body)</span>
                <el-button type="primary" link size="small" icon="DocumentCopy" @click.stop="copyText(currentLog.request_body)">複製 JSON</el-button>
              </div>
            </template>
            <div class="detail-section no-border">
              <pre class="json-box">{{ formatJson(currentLog.request_body) }}</pre>
            </div>
          </el-collapse-item>
          
          <el-collapse-item name="2">
            <template #title>
              <div class="collapse-title">
                <span class="text-blue font-bold">對話文本 (Parsed Messages)</span>
                <el-button type="primary" link size="small" icon="DocumentCopy" @click.stop="copyText(extractText(currentLog.request_body, true))">複製文本</el-button>
              </div>
            </template>
            <div class="detail-section no-border">
              <div class="text-area bg-blue-50">{{ extractText(currentLog.request_body, true) }}</div>
            </div>
          </el-collapse-item>

          <el-collapse-item name="3">
            <template #title>
              <div class="collapse-title">
                <span>響應內容 (Response Body)</span>
                <el-button type="primary" link size="small" icon="DocumentCopy" @click.stop="copyText(currentLog.response_body)">複製 JSON</el-button>
              </div>
            </template>
            <div class="detail-section no-border">
              <pre class="json-box">{{ formatJson(currentLog.response_body) }}</pre>
            </div>
          </el-collapse-item>

          <el-collapse-item name="4">
            <template #title>
              <div class="collapse-title">
                <span class="text-green font-bold">回答文本 (Assistant Content)</span>
                <el-button type="primary" link size="small" icon="DocumentCopy" @click.stop="copyText(extractText(currentLog.response_body, false))">複製文本</el-button>
              </div>
            </template>
            <div class="detail-section no-border">
              <div class="text-area bg-green-50">{{ extractText(currentLog.response_body, false) }}</div>
            </div>
          </el-collapse-item>
        </el-collapse>
        </div>
      </div>
    </el-dialog>

    <!-- 錯誤詳情 -->
    <el-dialog v-model="errorVisible" title="錯誤詳情" width="500px">
      <div class="error-box">{{ currentLog?.error_message }}</div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import request from '../../utils/request'
import { ElMessage } from 'element-plus'

const logs = ref<any[]>([])
const loading = ref(false)
const detailsLoading = ref(false)
const activeTab = ref('all')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const detailsVisible = ref(false)
const errorVisible = ref(false)
const currentLog = ref<any>(null)
const activeCollapseNames = ref(['2', '4'])
const windowWidth = ref(window.innerWidth)

const handleResize = () => {
  windowWidth.value = window.innerWidth
}

const handleTabChange = () => {
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
  // 後端返回的資料結構中，如果沒有帶關聯，我們可能只能看到 ID
  // 這裡假設後端返回了 api_key_display 或者我們需要從 api_key 物件中獲取
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
  // 先將當前點擊的 log 設置為 currentLog，這樣對話框打開時可以先顯示基本信息
  currentLog.value = log
  detailsVisible.value = true
  detailsLoading.value = true
  
  try {
    // 獲取完整詳情（包含 request_body 和 response_body）
    const data: any = await request.get(`logs/${log.id}`)
    // 合併數據：保留列表中的基本信息，覆蓋/添加詳情中的完整信息
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

const showError = (log: any) => {
  currentLog.value = log
  errorVisible.value = true
}

onMounted(() => {
  fetchLogs()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.logs-container {
  padding: 10px;
}
.header {
  margin-bottom: 15px;
}
.title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.pagination {
  margin-top: 15px;
  display: flex;
  justify-content: flex-end;
}
.log-details {
  display: flex;
  flex-direction: column;
  gap: 15px;
}
.log-info-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  background: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 5px;
}
.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.info-item .label {
  font-size: 12px;
  color: #909399;
}
.info-item .value {
  font-weight: bold;
  font-size: 14px;
  word-break: break-all;
}

@media (max-width: 768px) {
  .log-info-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .log-info-grid {
    grid-template-columns: 1fr;
  }
}

.detail-section {
  border: 1px solid #ebeef5;
  border-radius: 4px;
}
.section-title {
  padding: 8px 12px;
  background: #f5f7fa;
  font-weight: bold;
  font-size: 14px;
  border-bottom: 1px solid #ebeef5;
}
.text-blue { color: #409EFF; }
.text-green { color: #67C23A; }
.font-bold { font-weight: bold; }
.mb-4 { margin-bottom: 16px; }
.no-border { border: none !important; }
.collapse-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding-right: 20px;
}
.bg-blue-50 { background-color: #ecf5ff; }
.bg-green-50 { background-color: #f0f9eb; }

.json-box {
  padding: 12px;
  margin: 0;
  font-family: monospace;
  font-size: 12px;
  max-height: 250px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.text-area {
  padding: 12px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow: auto;
}
.error-box {
  padding: 15px;
  background: #fef0f0;
  color: #f56c6c;
  border: 1px solid #fde2e2;
  border-radius: 4px;
  word-break: break-all;
  white-space: pre-wrap;
}
</style>