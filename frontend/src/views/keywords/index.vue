<template>
  <div class="keywords-container">
    <div class="header-row">
      <h2>關鍵字過濾管理</h2>
      <el-button type="primary" link icon="Refresh" @click="fetchKeywords">刷新</el-button>
    </div>

    <div class="action-row">
      <el-button type="primary" icon="Plus" @click="handleAddKeyword">新增過濾關鍵字</el-button>
    </div>

    <el-table :data="keywords" style="width: 100%" v-loading="loading" size="small" border stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="keyword" label="關鍵字">
        <template #default="scope">
          <code>{{ scope.row.keyword }}</code>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" show-overflow-tooltip />
      <el-table-column label="啟用" width="80" align="center">
        <template #default="scope">
          <el-switch v-model="scope.row.is_active" @change="(val: boolean) => handleStatusChange(scope.row, val)" size="small" />
        </template>
      </el-table-column>
      <el-table-column prop="last_triggered" label="最後觸發時間" width="160">
        <template #default="scope">
          {{ scope.row.last_triggered ? formatDateTime(scope.row.last_triggered) : '從未觸發' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" align="center">
        <template #default="scope">
          <el-button type="primary" link icon="Edit" @click="handleEditKeyword(scope.row)" />
          <el-button type="danger" link icon="Delete" @click="handleDeleteKeyword(scope.row)" />
        </template>
      </el-table-column>
    </el-table>

    <!-- 編輯/新增對話框 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '編輯關鍵字' : '新增關鍵字'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="關鍵字" required>
          <el-input v-model="form.keyword" placeholder="觸發故障轉移的關鍵字" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" placeholder="該關鍵字的作用或來源" />
        </el-form-item>
        <el-form-item label="啟用狀態">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">確定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import request from '../../utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'

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

onMounted(fetchKeywords)
</script>

<style scoped>
.keywords-container { padding: 10px; }
.header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.action-row { margin-bottom: 20px; }
</style>