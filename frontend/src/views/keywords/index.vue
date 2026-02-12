<template>
  <div class="space-y-6">
    <!-- 頁面標題列 -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold text-gray-900">關鍵字過濾</h1>
        <p class="text-sm text-gray-500 mt-1">管理觸發故障轉移的關鍵字規則</p>
      </div>
      <div class="flex items-center gap-2">
        <el-button :icon="Refresh" @click="fetchKeywords" circle />
        <el-button type="primary" :icon="Plus" @click="handleAddKeyword">新增關鍵字</el-button>
      </div>
    </div>

    <!-- 桌面端表格 -->
    <div class="hidden md:block bg-white rounded-xl border border-gray-200 overflow-hidden">
      <el-table :data="keywords" v-loading="loading" size="small" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="關鍵字" min-width="180">
          <template #default="scope">
            <code class="text-xs bg-red-50 text-red-600 px-2 py-0.5 rounded font-mono">{{ scope.row.keyword }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip>
          <template #default="scope">
            <span class="text-sm text-gray-600">{{ scope.row.description || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="啟用" width="80" align="center">
          <template #default="scope">
            <el-switch v-model="scope.row.is_active" @change="(val: boolean) => handleStatusChange(scope.row, val)" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="最後觸發" width="160">
          <template #default="scope">
            <span class="text-xs text-gray-500">{{ scope.row.last_triggered ? formatDateTime(scope.row.last_triggered) : '從未觸發' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="scope">
            <div class="flex items-center justify-center gap-1">
              <el-button type="primary" link :icon="Edit" size="small" @click="handleEditKeyword(scope.row)" />
              <el-button type="danger" link :icon="Delete" size="small" @click="handleDeleteKeyword(scope.row)" />
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 移動端卡片 -->
    <div class="md:hidden space-y-3" v-loading="loading">
      <div
        v-for="row in keywords"
        :key="row.id"
        class="bg-white rounded-xl border border-gray-200 p-4 space-y-3"
      >
        <div class="flex items-start justify-between">
          <div class="space-y-1 min-w-0 flex-1">
            <code class="text-sm bg-red-50 text-red-600 px-2 py-0.5 rounded font-mono">{{ row.keyword }}</code>
            <p v-if="row.description" class="text-xs text-gray-500 mt-1.5">{{ row.description }}</p>
          </div>
          <el-switch v-model="row.is_active" @change="(val: boolean) => handleStatusChange(row, val)" size="small" />
        </div>

        <div class="flex items-center justify-between pt-2 border-t border-gray-100">
          <span class="text-xs text-gray-400">
            {{ row.last_triggered ? '最後觸發: ' + formatDateTime(row.last_triggered) : '從未觸發' }}
          </span>
          <div class="flex gap-1">
            <el-button size="small" type="primary" :icon="Edit" @click="handleEditKeyword(row)" />
            <el-button size="small" type="danger" :icon="Delete" @click="handleDeleteKeyword(row)" />
          </div>
        </div>
      </div>

      <div v-if="!loading && keywords.length === 0" class="text-center py-16">
        <el-icon :size="48" class="text-gray-300 mb-3"><Filter /></el-icon>
        <p class="text-gray-400">暫無過濾關鍵字</p>
      </div>
    </div>

    <!-- 編輯/新增對話框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="form.id ? '編輯關鍵字' : '新增關鍵字'"
      :width="isMobile ? '90%' : '500px'"
    >
      <el-form :model="form" label-position="top">
        <el-form-item label="關鍵字" required>
          <el-input v-model="form.keyword" placeholder="觸發故障轉移的關鍵字" size="large" />
          <div class="text-xs text-gray-400 mt-1">當 API 回應中包含此關鍵字時，將觸發故障轉移機制</div>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="該關鍵字的作用或來源" />
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
import { Plus, Refresh, Edit, Delete, Filter } from '@element-plus/icons-vue'

const screenWidth = ref(window.innerWidth)
const isMobile = computed(() => screenWidth.value < 768)
const onResize = () => { screenWidth.value = window.innerWidth }

const keywords = ref<any[]>([])
const loading = ref(false)
const dialogVisible = ref(false)

const form = reactive({
  id: null as number | null,
  keyword: '',
  description: '',
  is_active: true
})

const fetchKeywords = async () => {
  loading.value = true
  try {
    const data: any = await request.get('keywords/')
    keywords.value = data
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const formatDateTime = (ts: string) => {
  return new Date(ts).toLocaleString()
}

const handleAddKeyword = () => {
  Object.assign(form, { id: null, keyword: '', description: '', is_active: true })
  dialogVisible.value = true
}

const handleEditKeyword = (row: any) => {
  Object.assign(form, row)
  dialogVisible.value = true
}

const handleDeleteKeyword = (row: any) => {
  ElMessageBox.confirm('確定要刪除此關鍵字嗎？', '警告', { type: 'warning' }).then(async () => {
    await request.delete(`keywords/${row.id}`)
    ElMessage.success('已刪除')
    fetchKeywords()
  })
}

const handleStatusChange = async (row: any, val: boolean) => {
  try {
    await request.patch(`keywords/${row.id}`, { is_active: val })
    ElMessage.success('狀態已更新')
  } catch {
    row.is_active = !val
  }
}

const submitForm = async () => {
  if (!form.keyword) {
    ElMessage.warning('請輸入關鍵字')
    return
  }
  try {
    if (form.id) {
      await request.patch(`keywords/${form.id}`, form)
    } else {
      await request.post('keywords/', form)
    }
    ElMessage.success('操作成功')
    dialogVisible.value = false
    fetchKeywords()
  } catch (error) {
    console.error(error)
  }
}

onMounted(() => {
  fetchKeywords()
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
})
</script>