<template>
  <div class="providers-container">
    <div class="header-row">
      <h2>供應商</h2>
      <div class="search-box">
        <el-input v-model="searchQuery" placeholder="搜尋模型..." prefix-icon="Search" clearable @input="handleSearch" />
      </div>
    </div>

    <div class="action-row">
      <el-button type="primary" icon="Plus" @click="handleAddProvider">新增供應商</el-button>
      <el-button type="primary" plain icon="Refresh" @click="handleSyncModels">同步模型</el-button>
      <el-button type="danger" plain icon="DeleteFilled" @click="handleQuickRemove">快速刪除</el-button>
    </div>

    <el-table :data="providers" style="width: 100%" v-loading="loading" size="small" border stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="model" label="模型" show-overflow-tooltip />
      <el-table-column prop="name" label="別名" show-overflow-tooltip />
      <el-table-column prop="price_per_million_tokens" label="價格 ($/1M)" width="120" align="right" />
      <el-table-column label="狀態" width="80" align="center">
        <template #default="scope">
          <el-switch v-model="scope.row.is_active" @change="(val: boolean) => handleStatusChange(scope.row, val)" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" align="center">
        <template #default="scope">
          <el-button type="primary" link icon="Edit" @click="handleEditProvider(scope.row)" />
          <el-button type="danger" link icon="Delete" @click="handleDeleteProvider(scope.row)" />
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-container">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100, 200, 500]"
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 編輯/新增對話框 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '編輯供應商' : '新增供應商'" width="600px">
      <el-tabs v-model="activeDialogTab">
        <el-tab-pane label="批量導入" name="batch" v-if="!form.id">
          <el-form :model="importForm" label-width="120px">
            <el-form-item label="Base URL" required>
              <el-input v-model="importForm.base_url" placeholder="例如: https://api.openai.com" />
            </el-form-item>
            <el-form-item label="API Key" required>
              <el-input v-model="importForm.api_key" type="password" show-password />
            </el-form-item>
            <el-form-item label="名稱前綴">
              <el-input v-model="importForm.alias" />
            </el-form-item>
            <el-form-item label="計費類型">
              <el-select v-model="importForm.default_type" style="width: 100%">
                <el-option label="per_token" value="per_token" />
                <el-option label="per_call" value="per_call" />
              </el-select>
            </el-form-item>
            <el-form-item label="過濾模式">
              <el-select v-model="importForm.filter_mode" style="width: 100%">
                <el-option label="None" value="None" />
                <el-option label="Include" value="Include" />
                <el-option label="Exclude" value="Exclude" />
              </el-select>
            </el-form-item>
            <el-form-item label="模型過濾" v-if="importForm.filter_mode !== 'None'">
              <el-input v-model="importForm.filter_keyword" />
            </el-form-item>
            <div v-if="importing" class="import-progress">
              <el-progress :percentage="importProgress" />
              <div class="progress-text">{{ importMessage }}</div>
            </div>
          </el-form>
        </el-tab-pane>
        <el-tab-pane :label="form.id ? '編輯屬性' : '單個新增'" name="single">
          <el-form :model="form" label-width="120px">
            <el-form-item label="名稱" required>
              <el-input v-model="form.name" />
            </el-form-item>
            <el-form-item label="API 端點" required>
              <el-input v-model="form.api_endpoint" />
            </el-form-item>
            <el-form-item label="API 金鑰" :required="!form.id">
              <el-input v-model="form.api_key" type="password" show-password :placeholder="form.id ? '留空表示不修改' : ''" />
            </el-form-item>
            <el-form-item label="模型" required>
              <el-input v-model="form.model" />
            </el-form-item>
            <el-form-item label="價格 ($/1M)">
              <el-input-number v-model="form.price_per_million_tokens" :precision="4" :step="0.0001" style="width: 100%" />
            </el-form-item>
            <el-form-item label="類型">
              <el-select v-model="form.type" style="width: 100%">
                <el-option label="per_token" value="per_token" />
                <el-option label="per_call" value="per_call" />
              </el-select>
            </el-form-item>
            <el-form-item label="啟用">
              <el-switch v-model="form.is_active" />
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleDialogSubmit" :loading="importing">確定</el-button>
      </template>
    </el-dialog>

    <!-- 同步模型對話框 -->
    <el-dialog v-model="syncDialogVisible" title="同步模型" width="500px" :close-on-click-modal="!syncing">
      <el-form v-if="!syncing">
        <el-form-item label="選擇供應商">
          <el-select v-model="syncTargets" multiple style="width: 100%" v-loading="loadingUnique">
            <el-option v-for="item in allUniqueProviders" :key="item.key" :label="item.label" :value="item.key" />
          </el-select>
        </el-form-item>
      </el-form>
      <div v-else class="sync-progress">
        <div class="sync-target-info">{{ currentSyncTargetLabel }}</div>
        <el-progress :percentage="syncProgress" :status="syncStatus" />
        <div class="progress-text">{{ syncMessage }}</div>
      </div>
      <template #footer>
        <el-button @click="syncDialogVisible = false" :disabled="syncing">取消</el-button>
        <el-button type="primary" @click="submitSync" :loading="syncing">同步</el-button>
      </template>
    </el-dialog>

    <!-- 快速刪除對話框 -->
    <el-dialog v-model="quickRemoveVisible" title="快速刪除供應商" width="500px">
      <el-form>
        <el-form-item label="根據 API Key 刪除">
          <el-select v-model="removeTargetKey" style="width: 100%" v-loading="loadingUnique">
            <el-option v-for="item in allUniqueProviders" :key="item.apiKey" :label="item.label" :value="item.apiKey" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="quickRemoveVisible = false">取消</el-button>
        <el-button type="danger" @click="submitQuickRemove">刪除</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import request from '../../utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'

const providers = ref<any[]>([])
const loading = ref(false)
const searchQuery = ref('')
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const dialogVisible = ref(false)
const activeDialogTab = ref('batch')
const syncDialogVisible = ref(false)
const quickRemoveVisible = ref(false)
const syncTargets = ref<string[]>([])
const removeTargetKey = ref('')
const allUniqueProviders = ref<any[]>([])
const loadingUnique = ref(false)
const syncing = ref(false)
const syncProgress = ref(0)
const syncMessage = ref('')
const syncStatus = ref<'' | 'success' | 'exception' | 'warning'>('')
const currentSyncTargetLabel = ref('')

const form = reactive({
  id: null as number | null,
  name: '',
  api_endpoint: '',
  api_key: '',
  model: '',
  price_per_million_tokens: 0,
  type: 'per_token',
  is_active: true
})

const importForm = reactive({
  base_url: '',
  api_key: '',
  alias: '',
  default_type: 'per_token',
  filter_mode: 'None',
  filter_keyword: ''
})

const importing = ref(false)
const importProgress = ref(0)
const importMessage = ref('')

const fetchProviders = async () => {
  loading.value = true
  try {
    const data: any = await request.get('providers/', {
      params: {
        skip: (currentPage.value - 1) * pageSize.value,
        limit: pageSize.value,
        name_filter: searchQuery.value || undefined
      }
    })
    providers.value = data.items
    total.value = data.total
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const fetchUniqueProviders = async () => {
  loadingUnique.value = true
  try {
    // We need all providers to find unique endpoints/keys, since 'providers' ref only contains current page
    const data: any = await request.get('providers/', { params: { limit: 10000 } })
    const map = new Map()
    data.items.forEach((p: any) => {
      // Logic for grouping by endpoint + key to show UNIQUE providers in sync/remove dialogs
      const key = `${p.api_endpoint}|${p.api_key}`
      if (!map.has(key)) {
        map.set(key, {
          key,
          apiKey: p.api_key || '',
          apiEndpoint: p.api_endpoint || '',
          name: p.name || '',
          type: p.type || 'per_token',
          label: `${p.name || 'Unknown'} [${p.api_endpoint || 'No Endpoint'}] (${p.api_key ? p.api_key.slice(0, 5) : '***'}...)`
        })
      }
    })
    allUniqueProviders.value = Array.from(map.values())
  } catch (error) {
    console.error(error)
  } finally {
    loadingUnique.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchProviders()
}

const handleSizeChange = (val: number) => {
  pageSize.value = val
  fetchProviders()
}

const handleCurrentChange = (val: number) => {
  currentPage.value = val
  fetchProviders()
}

const handleAddProvider = () => {
  Object.assign(form, { id: null, name: '', api_endpoint: '', api_key: '', model: '', price_per_million_tokens: 0, type: 'per_token', is_active: true })
  activeDialogTab.value = 'batch'
  dialogVisible.value = true
}

const handleEditProvider = (row: any) => {
  Object.assign(form, row)
  form.api_key = '' // 編輯時金鑰留空
  activeDialogTab.value = 'single'
  dialogVisible.value = true
}

const handleDialogSubmit = () => {
  if (activeDialogTab.value === 'batch' && !form.id) {
    submitImport()
  } else {
    submitSingle()
  }
}

const submitSingle = async () => {
  try {
    if (form.id) {
      const data = { ...form }
      if (!data.api_key) delete (data as any).api_key
      await request.patch(`providers/${form.id}`, data)
    } else {
      await request.post('providers/', form)
    }
    ElMessage.success('操作成功')
    dialogVisible.value = false
    fetchProviders()
  } catch (error) {
    console.error(error)
  }
}

const submitImport = async () => {
  if (!importForm.base_url || !importForm.api_key) {
    ElMessage.warning('請填寫完整信息')
    return
  }
  importing.value = true
  importProgress.value = 0
  importMessage.value = '正在連接...'
  try {
    const token = localStorage.getItem('token')
    let baseApi = import.meta.env.VITE_APP_BASE_API || 'http://47.106.65.25:8001/api/'
    if (!baseApi.endsWith('/')) baseApi += '/'
    const response = await fetch(`${baseApi}import-models/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify(importForm)
    })
    if (!response.body) throw new Error('ReadableStream not supported')
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let total = 0
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      const lines = decoder.decode(value).split('\n')
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim()
          const parts = data.split('=')
          const key = parts[0]
          const val = parts[1] || ''

          if (key === 'TOTAL') total = parseInt(val)
          else if (key === 'PROGRESS') {
            const current = parseInt(val)
            importProgress.value = total > 0 ? Math.round((current / total) * 100) : 0
            importMessage.value = `已導入 ${current} / ${total}`
          } else if (key === 'DONE') {
            ElMessage.success('導入完成')
            dialogVisible.value = false
            fetchProviders()
          } else if (key === 'ERROR') {
            ElMessage.error(val)
          }
        }
      }
    }
  } catch (error: any) {
    ElMessage.error('導入失敗: ' + error.message)
  } finally {
    importing.value = false
  }
}

const handleDeleteProvider = (row: any) => {
  ElMessageBox.confirm(`確定刪除供應商 "${row.name}" 嗎？`, '警告', { type: 'warning' }).then(async () => {
    await request.delete(`providers/${row.id}`)
    ElMessage.success('已刪除')
    fetchProviders()
  })
}

const handleStatusChange = async (row: any, val: boolean) => {
  try {
    await request.patch(`providers/${row.id}`, { is_active: val })
    ElMessage.success('狀態已更新')
  } catch {
    row.is_active = !val
  }
}

const handleSyncModels = () => {
  syncTargets.value = []
  syncDialogVisible.value = true
  fetchUniqueProviders()
}

const submitSync = async () => {
  if (syncTargets.value.length === 0) return
  syncing.value = true
  syncStatus.value = ''
  
  try {
    const token = localStorage.getItem('token')
    const totalTargets = syncTargets.value.length
    let hasError = false
    
    for (let i = 0; i < totalTargets; i++) {
      const targetKey = syncTargets.value[i]
      const target = allUniqueProviders.value.find(t => t.key === targetKey)
      
      if (!target || !target.apiEndpoint || !target.apiKey) {
        ElMessage.error(`供應商 ${target?.name || '未知'} 缺少 API Key 或端點，無法同步`)
        hasError = true
        continue
      }

      currentSyncTargetLabel.value = `正在同步: ${target.name}`
      syncProgress.value = 0
      syncMessage.value = `正在準備 (${i + 1}/${totalTargets})...`

      let baseUrl = target.apiEndpoint.replace(/\/chat\/completions$/, '')
      if (baseUrl.endsWith('/v1')) baseUrl = baseUrl.slice(0, -3)

      let baseApi = import.meta.env.VITE_APP_BASE_API || 'http://47.106.65.25:8001/api/'
      if (!baseApi.endsWith('/')) baseApi += '/'
      
      const response = await fetch(`${baseApi}import-models/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          base_url: baseUrl,
          api_key: target.apiKey,
          alias: target.name || undefined,
          default_type: target.type || 'per_token',
          filter_mode: 'None'
        })
      })

      if (!response.body) throw new Error('ReadableStream not supported')
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let providerTotal = 0

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        const lines = decoder.decode(value).split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim()
            const parts = data.split('=')
            const key = parts[0]
            const val = parts[1] || ''

            if (key === 'TOTAL') providerTotal = parseInt(val)
            else if (key === 'PROGRESS') {
              const current = parseInt(val)
              syncProgress.value = providerTotal > 0 ? Math.round((current / providerTotal) * 100) : 0
              syncMessage.value = `同步進度: ${current} / ${providerTotal}`
            } else if (key === 'ERROR') {
              ElMessage.error(`${target.name}: ${val}`)
            }
          }
        }
      }
    }
    
    if (!hasError) {
      syncStatus.value = 'success'
      syncMessage.value = '全部同步完成'
      ElMessage.success('同步完成')
      setTimeout(() => {
        syncDialogVisible.value = false
        fetchProviders()
      }, 1500)
    } else {
      syncStatus.value = 'warning'
      syncMessage.value = '同步結束，部分供應商失敗'
      fetchProviders()
    }
  } catch (error: any) {
    syncStatus.value = 'exception'
    syncMessage.value = '同步失敗: ' + error.message
    ElMessage.error('同步失敗: ' + error.message)
  } finally {
    syncing.value = false
  }
}

const handleQuickRemove = () => {
  removeTargetKey.value = ''
  quickRemoveVisible.value = true
  fetchUniqueProviders()
}

const submitQuickRemove = async () => {
  if (!removeTargetKey.value) return
  ElMessageBox.confirm('將刪除所有使用此 API Key 的供應商，確定嗎？', '警告', { type: 'warning' }).then(async () => {
    try {
      await request.delete(`providers/quick-remove/${removeTargetKey.value}`)
      ElMessage.success('刪除成功')
      quickRemoveVisible.value = false
      fetchProviders()
    } catch (error) {
      console.error(error)
    }
  })
}

onMounted(fetchProviders)
</script>

<style scoped>
.providers-container { padding: 10px; }
.header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.search-box { width: 300px; }
.action-row { margin-bottom: 20px; }
.pagination-container { margin-top: 20px; display: flex; justify-content: flex-end; }
.import-progress, .sync-progress { margin-top: 20px; text-align: center; }
.progress-text { margin-top: 8px; font-size: 13px; color: #666; }
.sync-target-info { margin-bottom: 12px; font-weight: bold; color: #409EFF; }
</style>