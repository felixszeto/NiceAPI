<template>
  <div class="space-y-6">
    <!-- 頁面標題列 -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold text-gray-900">API 金鑰</h1>
        <p class="text-sm text-gray-500 mt-1">管理 API 存取金鑰與群組權限</p>
      </div>
      <div class="flex items-center gap-2">
        <el-button :icon="Refresh" @click="fetchKeys" circle />
        <el-button type="primary" :icon="Plus" @click="handleAddKey">生成金鑰</el-button>
      </div>
    </div>

    <!-- 桌面端表格 -->
    <div class="hidden md:block bg-white rounded-xl border border-gray-200 overflow-hidden">
      <el-table :data="apiKeys" v-loading="loading" size="small" stripe>
        <el-table-column label="金鑰" min-width="160">
          <template #default="scope">
            <div class="flex items-center gap-2">
              <code class="text-xs bg-gray-100 px-2 py-1 rounded font-mono">{{ formatKeyDisplay(scope.row.key) }}</code>
              <el-button type="primary" link :icon="View" size="small" @click="viewFullKey(scope.row.key)" />
              <el-button type="primary" link :icon="CopyDocument" size="small" @click="copyKey(scope.row.key)" />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="狀態" width="80" align="center">
          <template #default="scope">
            <el-switch v-model="scope.row.is_active" @change="(val: boolean) => handleStatusChange(scope.row, val)" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="群組" min-width="150">
          <template #default="scope">
            <div class="flex flex-wrap gap-1">
              <el-tag v-for="g in scope.row.groups" :key="g.id" size="small" effect="plain" class="!rounded-md">{{ g.name }}</el-tag>
              <span v-if="!scope.row.groups?.length" class="text-xs text-gray-400">未分配</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="call_count" label="調用次數" width="90" align="right" />
        <el-table-column label="創建時間" width="150">
          <template #default="scope">
            <span class="text-xs text-gray-500">{{ formatDateTime(scope.row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="最後使用" width="150">
          <template #default="scope">
            <span class="text-xs text-gray-500">{{ scope.row.last_used_at ? formatDateTime(scope.row.last_used_at) : '從未使用' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center" fixed="right">
          <template #default="scope">
            <div class="flex items-center justify-center gap-1">
              <el-button type="primary" link :icon="Edit" size="small" @click="handleEditKey(scope.row)" />
              <el-button type="info" link :icon="Promotion" size="small" @click="openRemote(scope.row.key)" />
              <el-button type="danger" link :icon="Delete" size="small" @click="handleDeleteKey(scope.row)" />
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 移動端卡片 -->
    <div class="md:hidden space-y-3" v-loading="loading">
      <div
        v-for="row in apiKeys"
        :key="row.id"
        class="bg-white rounded-xl border border-gray-200 p-4 space-y-3"
      >
        <!-- 金鑰與狀態 -->
        <div class="flex items-center justify-between">
          <code class="text-xs bg-gray-100 px-2 py-1 rounded font-mono">{{ formatKeyDisplay(row.key) }}</code>
          <el-switch v-model="row.is_active" @change="(val: boolean) => handleStatusChange(row, val)" size="small" />
        </div>

        <!-- 群組標籤 -->
        <div class="flex flex-wrap gap-1">
          <el-tag v-for="g in row.groups" :key="g.id" size="small" effect="plain" class="!rounded-md">{{ g.name }}</el-tag>
          <span v-if="!row.groups?.length" class="text-xs text-gray-400">未分配群組</span>
        </div>

        <!-- 統計資訊 -->
        <div class="grid grid-cols-3 gap-2 text-center text-xs">
          <div class="bg-gray-50 rounded-lg p-2">
            <div class="text-gray-400">調用</div>
            <div class="font-semibold text-gray-900 mt-0.5">{{ row.call_count || 0 }}</div>
          </div>
          <div class="bg-gray-50 rounded-lg p-2">
            <div class="text-gray-400">創建</div>
            <div class="font-semibold text-gray-900 mt-0.5 truncate">{{ formatDateShort(row.created_at) }}</div>
          </div>
          <div class="bg-gray-50 rounded-lg p-2">
            <div class="text-gray-400">最後使用</div>
            <div class="font-semibold text-gray-900 mt-0.5 truncate">{{ row.last_used_at ? formatDateShort(row.last_used_at) : '從未' }}</div>
          </div>
        </div>

        <!-- 操作按鈕 -->
        <div class="flex items-center justify-between pt-2 border-t border-gray-100">
          <div class="flex gap-1">
            <el-button size="small" :icon="CopyDocument" @click="copyKey(row.key)">複製</el-button>
            <el-button size="small" :icon="Promotion" @click="openRemote(row.key)">遠端</el-button>
          </div>
          <div class="flex gap-1">
            <el-button size="small" type="primary" :icon="Edit" @click="handleEditKey(row)" />
            <el-button size="small" type="danger" :icon="Delete" @click="handleDeleteKey(row)" />
          </div>
        </div>
      </div>

      <div v-if="!loading && apiKeys.length === 0" class="text-center py-16">
        <el-icon :size="48" class="text-gray-300 mb-3"><Key /></el-icon>
        <p class="text-gray-400">暫無 API 金鑰</p>
      </div>
    </div>

    <!-- 生成成功對話框 -->
    <el-dialog v-model="showKeyDialog" title="API 金鑰已生成" :width="isMobile ? '90%' : '450px'">
      <div class="space-y-4">
        <div class="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <el-icon class="text-amber-500 mt-0.5" :size="16"><Warning /></el-icon>
          <p class="text-sm text-amber-700">請立即複製並保存此金鑰，關閉後將無法再次查看完整內容。</p>
        </div>
        <el-input v-model="newKey" readonly size="large">
          <template #append>
            <el-button :icon="CopyDocument" @click="copyKey(newKey)" />
          </template>
        </el-input>
      </div>
      <template #footer>
        <el-button type="primary" @click="showKeyDialog = false">我已保存，關閉</el-button>
      </template>
    </el-dialog>

    <!-- 編輯/新增對話框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="form.id ? '編輯 API 金鑰' : '生成新金鑰'"
      :width="isMobile ? '90%' : '500px'"
    >
      <el-form :model="form" label-position="top">
        <el-form-item label="群組權限" required>
          <el-select v-model="form.group_ids" multiple placeholder="選擇要分配的群組" style="width: 100%" size="large">
            <el-option v-for="g in groups" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
          <div class="text-xs text-gray-400 mt-1">金鑰將擁有所選群組中所有供應商的存取權限</div>
        </el-form-item>
        <el-form-item label="啟用狀態">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="flex justify-end gap-2">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm">確定</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import request from '../../utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Edit, Delete, View, CopyDocument, Promotion, Warning, Key } from '@element-plus/icons-vue'

const screenWidth = ref(window.innerWidth)
const isMobile = computed(() => screenWidth.value < 768)
const onResize = () => { screenWidth.value = window.innerWidth }

const apiKeys = ref<any[]>([])
const groups = ref<any[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const showKeyDialog = ref(false)
const newKey = ref('')

const form = reactive({
  id: null as number | null,
  group_ids: [] as number[],
  is_active: true
})

const fetchKeys = async () => {
  loading.value = true
  try {
    const data: any = await request.get('keys/')
    apiKeys.value = data
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const fetchGroups = async () => {
  try {
    const data: any = await request.get('groups/')
    groups.value = data.items
  } catch (error) {
    console.error(error)
  }
}

const formatKeyDisplay = (key: string) => `${key.slice(0, 5)}...${key.slice(-4)}`

const formatDateTime = (ts: string) => new Date(ts).toLocaleString()

const formatDateShort = (ts: string) => {
  const d = new Date(ts)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

const handleAddKey = () => {
  Object.assign(form, { id: null, group_ids: [], is_active: true })
  dialogVisible.value = true
}

const handleEditKey = (row: any) => {
  form.id = row.id
  form.group_ids = row.groups.map((g: any) => g.id)
  form.is_active = row.is_active
  dialogVisible.value = true
}

const submitForm = async () => {
  if (form.group_ids.length === 0) {
    ElMessage.warning('請至少選擇一個群組')
    return
  }
  try {
    if (form.id) {
      await request.patch(`keys/${form.id}`, form)
      ElMessage.success('更新成功')
      fetchKeys()
    } else {
      const res: any = await request.post('keys/', form)
      newKey.value = res.key
      showKeyDialog.value = true
      fetchKeys()
    }
    dialogVisible.value = false
  } catch (error) {
    console.error(error)
  }
}

const handleStatusChange = async (row: any, val: boolean) => {
  try {
    await request.patch(`keys/${row.id}`, { is_active: val })
    ElMessage.success('狀態已更新')
  } catch {
    row.is_active = !val
  }
}

const handleDeleteKey = (row: any) => {
  ElMessageBox.confirm(`確定刪除金鑰 "${formatKeyDisplay(row.key)}" 嗎？`, '警告', { type: 'warning' }).then(async () => {
    await request.delete(`keys/${row.id}`)
    ElMessage.success('已刪除')
    fetchKeys()
  })
}

const viewFullKey = (key: string) => {
  ElMessage.info({
    message: `完整金鑰: ${key}`,
    duration: 10000,
    showClose: true
  })
}

const copyKey = (key: string) => {
  navigator.clipboard.writeText(key).then(() => {
    ElMessage.success('已複製到剪貼簿')
  })
}

const openRemote = (key: string) => {
  window.open(`/remote?key=${key}`, '_blank')
}

onMounted(() => {
  fetchKeys()
  fetchGroups()
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
})
</script>