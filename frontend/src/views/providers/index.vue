<template>
  <div v-loading="loading">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
      <div class="flex flex-wrap gap-2">
        <el-button type="primary" icon="Plus" @click="handleAddProvider">新增供應商</el-button>
        <el-button type="primary" plain icon="Refresh" @click="handleSyncModels">同步模型</el-button>
        <el-button type="danger" plain icon="DeleteFilled" @click="handleQuickRemove">快速刪除</el-button>
      </div>
      <el-input
        v-model="searchQuery"
        placeholder="搜尋模型..."
        prefix-icon="Search"
        clearable
        class="!w-full sm:!w-64"
        @input="handleSearch"
      />
    </div>

    <!-- Desktop table -->
    <div class="hidden md:block bg-white rounded-xl border border-slate-200 overflow-hidden">
      <el-table :data="providers" style="width: 100%" size="default" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="model" label="模型" show-overflow-tooltip />
        <el-table-column prop="name" label="別名" show-overflow-tooltip />
        <el-table-column prop="price_per_million_tokens" label="價格 ($/1M)" width="130" align="right" />
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
    </div>

    <!-- Mobile cards -->
    <div class="md:hidden space-y-3">
      <div
        v-for="row in providers"
        :key="row.id"
        class="bg-white rounded-xl border border-slate-200 p-4"
      >
        <div class="flex items-start justify-between mb-3">
          <div class="min-w-0 flex-1">
            <div class="text-sm font-semibold text-slate-800 truncate">{{ row.model }}</div>
            <div class="text-xs text-slate-500 mt-0.5">{{ row.name }} · ID: {{ row.id }}</div>
          </div>
          <el-switch v-model="row.is_active" @change="(val: boolean) => handleStatusChange(row, val)" size="small" />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-xs text-slate-500">${{ row.price_per_million_tokens }} / 1M tokens</span>
          <div class="flex gap-1">
            <el-button type="primary" link icon="Edit" size="small" @click="handleEditProvider(row)" />
            <el-button type="danger" link icon="Delete" size="small" @click="handleDeleteProvider(row)" />
          </div>
        </div>
      </div>
      <div v-if="providers.length === 0" class="text-center py-8 text-slate-400 text-sm">暫無數據</div>
    </div>

    <!-- Pagination -->
    <div class="flex justify-end mt-4">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100, 200, 500]"
        :layout="isMobile ? 'prev, pager, next' : 'total, sizes, prev, pager, next, jumper'"
        :total="total"
        :small="isMobile"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- Add/Edit dialog -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '編輯供應商' : '新增供應商'" :width="isMobile ? '95%' : '600px'" :fullscreen="isMobile">
      <el-tabs v-model="activeDialogTab">
        <el-tab-pane label="批量導入" name="batch" v-if="!form.id">
          <el-form :model="importForm" label-position="top">
            <el-form-item label="Base URL" required>
              <el-input v-model="importForm.base_url" placeholder="例如: https://api.openai.com" />
            </el-form-item>
            <el-form-item label="API Key" required>
              <el-input v-model="importForm.api_key" type="password" show-password />
            </el-form-item>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-4">
              <el-form-item label="名稱前綴">
                <el-input v-model="importForm.alias" />
              </el-form-item>
              <el-form-item label="計費類型">
                <el-select v-model="importForm.default_type" class="!w-full">
                  <el-option label="per_token" value="per_token" />
                  <el-option label="per_call" value="per_call" />
                </el-select>
              </el-form-item>
              <el-form-item label="過濾模式">
                <el-select v-model="importForm.filter_mode" class="!w-full">
                  <el-option label="None" value="None" />
                  <el-option label="Include" value="Include" />
                  <el-option label="Exclude" value="Exclude" />
                </el-select>
              </el-form-item>
              <el-form-item label="模型過濾" v-if="importForm.filter_mode !== 'None'">
                <el-input v-model="importForm.filter_keyword" />
              </el-form-item>
            </div>
            <div v-if="importing" class="mt-4 text-center">
              <el-progress :percentage="importProgress" />
              <div class="mt-2 text-sm text-slate-500">{{ importMessage }}</div>
            </div>
          </el-form>
        </el-tab-pane>
        <el-tab-pane :label="form.id ? '編輯屬性' : '單個新增'" name="single">
          <el-form :model="form" label-position="top">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-4">
              <el-form-item label="名稱" required>
                <el-input v-model="form.name" />
              </el-form-item>
              <el-form-item label="模型" required>
                <el-input v-model="form.model" />
              </el-form-item>
            </div>
            <el-form-item label="API 端點" required>
              <el-input v-model="form.api_endpoint" />
            </el-form-item>
            <el-form-item label="API 金鑰" :required="!form.id">
              <el-input v-model="form.api_key" type="password" show-password :placeholder="form.id ? '留空表示不修改' : ''" />
            </el-form-item>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-x-4">
              <el-form-item label="價格 ($/1M)">
                <el-input-number v-model="form.price_per_million_tokens" :precision="4" :step="0.0001" class="!w-full" />
              </el-form-item>
              <el-form-item label="類型">
                <el-select v-model="form.type" class="!w-full">
                  <el-option label="per_token" value="per_token" />
                  <el-option label="per_call" value="per_call" />
                </el-select>
              </el-form-item>
              <el-form-item label="啟用">
                <el-switch v-model="form.is_active" />
              </el-form-item>
            </div>
          </el-form>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleDialogSubmit" :loading="importing">確定</el-button>
      </template>
    </el-dialog>

    <!-- Sync dialog -->
    <el-dialog v-model="syncDialogVisible" title="同步模型" :width="isMobile ? '95%' : '500px'" :close-on-click-modal="!syncing">
      <el-form v-if="!syncing" label-position="top">
        <el-form-item label="選擇供應商">
          <el-select v-model="syncTargets" multiple class="!w-full" v-loading="loadingUnique">
            <el-option v-for="item in allUniqueProviders" :key="item.key" :label="item.label" :value="item.key" />
          </el-select>
        </el-form-item>
      </el-form>
      <div v-else class="text-center py-4">
        <div class="text-sm font-semibold text-primary-600 mb-3">{{ currentSyncTargetLabel }}</div>
        <el-progress :percentage="syncProgress" :status="syncStatus" />
        <div class="mt-2 text-sm text-slate-500">{{ syncMessage }}</div>
      </div>
      <template #footer>
        <el-button @click="syncDialogVisible = false" :disabled="syncing">取消</el-button>
        <el-button type="primary" @click="submitSync" :loading="syncing">同步</el-button>
      </template>
    </el-dialog>

    <!-- Quick remove dialog -->
    <el-dialog v-model="quickRemoveVisible" title="快速刪除供應商" :width="isMobile ? '95%' : '500px'">
      <el-form label-position="top">
        <el-form-item label="根據 API Key 刪除">
          <el-select v-model="removeTargetKey" class="!w-full" v-loading="loadingUnique">
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
import { ref, reactive, computed, onMounted } from 'vue'
import request from '../../utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'

const screenWidth = ref(window.innerWidth)
const isMobile = computed(() => screenWidth.value < 768)

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
    const data: any = await request.get('providers/')
    const map = new Map()
    data.items.forEach((p: any) => {
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
  form.api_key = ''
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

onMounted(() => {
  fetchProviders()
  window.addEventListener('resize', () => { screenWidth.value = window.innerWidth })
})
</script>