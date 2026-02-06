<template>
  <div class="api-keys-container">
    <div class="header-row">
      <h2>API 金鑰</h2>
      <el-button type="primary" link icon="Refresh" @click="fetchKeys">刷新</el-button>
    </div>

    <div class="action-row">
      <el-button type="primary" icon="Plus" @click="handleAddKey">生成 API 金鑰</el-button>
    </div>

    <el-table :data="apiKeys" style="width: 100%" v-loading="loading" size="small" border stripe>
      <el-table-column label="金鑰">
        <template #default="scope">
          <div class="key-display">
            <code>{{ formatKeyDisplay(scope.row.key) }}</code>
            <div class="key-actions">
              <el-button type="primary" link icon="View" @click="viewFullKey(scope.row.key)">
                <el-tooltip content="查看金鑰" placement="top" />
              </el-button>
              <el-button type="primary" link icon="CopyDocument" @click="copyKey(scope.row.key)">
                <el-tooltip content="複製金鑰" placement="top" />
              </el-button>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="啟用" width="80" align="center">
        <template #default="scope">
          <el-switch v-model="scope.row.is_active" @change="(val: boolean) => handleStatusChange(scope.row, val)" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="群組">
        <template #default="scope">
          <div class="group-tags">
            <el-tag v-for="g in scope.row.groups" :key="g.id" size="small" class="mr-2">{{ g.name }}</el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="call_count" label="API 調用" width="100" align="right" />
      <el-table-column prop="created_at" label="創建時間" width="160">
        <template #default="scope">
          {{ formatDateTime(scope.row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column prop="last_used_at" label="最後使用" width="160">
        <template #default="scope">
          {{ scope.row.last_used_at ? formatDateTime(scope.row.last_used_at) : '從未使用' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" align="center">
        <template #default="scope">
          <el-button type="primary" link icon="Edit" @click="handleEditKey(scope.row)" />
          <el-button type="info" link icon="Promotion" @click="openRemote(scope.row.key)">
            <el-tooltip content="打開遠端管理" placement="top" />
          </el-button>
          <el-button type="danger" link icon="Delete" @click="handleDeleteKey(scope.row)" />
        </template>
      </el-table-column>
    </el-table>

    <!-- 生成成功對話框 -->
    <el-dialog v-model="showKeyDialog" title="API 金鑰已生成" width="400px">
      <p class="text-sm text-gray-500 mb-4">請立即複製並保存此金鑰，關閉後將無法再次查看完整內容。</p>
      <el-input v-model="newKey" readonly>
        <template #append>
          <el-button icon="CopyDocument" @click="copyKey(newKey)" />
        </template>
      </el-input>
      <template #footer>
        <el-button type="primary" @click="showKeyDialog = false">關閉</el-button>
      </template>
    </el-dialog>

    <!-- 編輯/新增對話框 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '編輯 API 金鑰' : '生成新金鑰'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="群組權限" required>
          <el-select v-model="form.group_ids" multiple placeholder="分配到群組" style="width: 100%">
            <el-option v-for="g in groups" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
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
    const data: any = await request.get('groups/', { params: { limit: 1000 } })
    groups.value = data.items
  } catch (error) {
    console.error(error)
  }
}

const formatKeyDisplay = (key: string) => {
  return `${key.slice(0, 5)}...${key.slice(-4)}`
}

const formatDateTime = (ts: string) => {
  return new Date(ts).toLocaleString()
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
})
</script>

<style scoped>
.api-keys-container { padding: 10px; }
.header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.action-row { margin-bottom: 20px; }
.key-display { display: flex; align-items: center; justify-content: space-between; }
.key-actions { display: flex; gap: 5px; }
.mr-2 { margin-right: 8px; }
</style>