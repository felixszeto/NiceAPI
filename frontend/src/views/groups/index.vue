<template>
  <div class="groups-container">
    <div class="header-row">
      <h2>分組管理</h2>
      <el-button type="primary" link icon="Refresh" @click="fetchGroups">刷新</el-button>
    </div>

    <div class="action-row">
      <el-button type="primary" icon="Plus" @click="handleAddGroup">創建新分組</el-button>
    </div>

    <div class="groups-list" v-loading="loading">
      <el-card v-for="group in groups" :key="group.id" class="group-card mb-4" shadow="hover">
        <div class="group-header">
          <div class="group-info">
            <span class="group-name">{{ group.name }}</span>
            <span class="group-meta">ID: {{ group.id }} | {{ group.providers?.length || 0 }} 供應商</span>
          </div>
          <div class="group-actions">
            <el-button type="primary" plain icon="Setting" @click="handleManageProviders(group)">管理供應商</el-button>
            <el-button type="danger" link icon="Delete" @click="handleDeleteGroup(group)" />
          </div>
        </div>
        <div class="group-providers" v-if="group.providers && group.providers.length">
          <el-tag v-for="p in sortProviders(group.providers).slice(0, 10)" :key="p.id" 
                  size="small" class="mr-2 mb-1" effect="light" type="info">
            P{{ p.priority }}: {{ p.name }}.{{ p.model }}
          </el-tag>
          <el-tag v-if="group.providers.length > 10" size="small" type="info">+ {{ group.providers.length - 10 }} ...</el-tag>
        </div>
        <div v-else class="text-gray-400 text-sm mt-2">尚未添加供應商</div>
      </el-card>
    </div>

    <div class="pagination-container">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 管理供應商對話框 -->
    <el-dialog v-model="manageDialogVisible" :title="'管理供應商: ' + currentGroup?.name" width="900px">
      <div class="manage-content">
        <el-input v-model="providerSearch" placeholder="搜尋供應商或模型..." prefix-icon="Search" class="mb-4" clearable />
        <el-table :data="filteredProviders" style="width: 100%" height="450px" size="small" border>
          <el-table-column label="模型/別名" min-width="200">
            <template #default="scope">
              <div class="provider-info-cell" :class="{ 'is-selected': scope.row.selected }" @click="toggleSelect(scope.row)">
                <div class="font-bold">{{ scope.row.model }}</div>
                <div class="text-xs text-gray-500">{{ scope.row.name }}</div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="優先級 (P1-P5)" width="350" align="center">
            <template #default="scope">
              <div class="priority-selector" :class="{ 'is-selected': scope.row.selected }">
                <div v-for="p in 5" :key="p" class="p-item">
                  <div class="p-label" :class="{ 'is-active': scope.row.priority === p }">P{{ p }}</div>
                  <el-switch v-model="scope.row.priority" :active-value="p" :inactive-value="lastPriorities.get(scope.row.id) === p ? 0 : scope.row.priority"
                             @change="(val: any) => handlePriorityChange(scope.row, val)" size="small" />
                </div>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-button @click="manageDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveManagement">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import request from '../../utils/request'

interface Provider {
  id: number
  name: string
  model: string
  selected: boolean
  priority: number
}

interface Group {
  id: number
  name: string
  providers: any[]
}

const groups = ref<Group[]>([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const manageDialogVisible = ref(false)
const currentGroup = ref<Group | null>(null)
const allProviders = ref<Provider[]>([])
const providerSearch = ref('')
const lastPriorities = new Map<number, number>()

const fetchGroups = async () => {
  loading.value = true
  try {
    const data: any = await request.get('groups/', {
      params: {
        skip: (currentPage.value - 1) * pageSize.value,
        limit: pageSize.value
      }
    })
    groups.value = data.items
    total.value = data.total
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleSizeChange = (val: number) => {
  pageSize.value = val
  fetchGroups()
}

const handleCurrentChange = (val: number) => {
  currentPage.value = val
  fetchGroups()
}

const fetchAllProviders = async () => {
  try {
    // For the management dialog, we fetch a larger batch to ensure the shifting logic works across available providers
    // If there are more than 1000, we might need a better search/fetch strategy, but 1000 is a safe start.
    const data: any = await request.get('providers/', { params: { limit: 1000 } })
    allProviders.value = data.items.map((p: any) => ({
      ...p,
      selected: false,
      priority: 0
    }))
  } catch (error) {
    console.error(error)
  }
}

const handleAddGroup = () => {
  ElMessageBox.prompt('請輸入群組名稱', '新增群組', {
    confirmButtonText: '確定',
    cancelButtonText: '取消',
  }).then(async (data: any) => {
    if (data.value) {
      await request.post('groups/', { name: data.value })
      ElMessage.success('群組創建成功')
      fetchGroups()
    }
  })
}

const handleDeleteGroup = (group: Group) => {
  ElMessageBox.confirm(`確定要刪除群組 "${group.name}" 嗎？`, '警告', {
    type: 'warning',
  }).then(async () => {
    await request.delete(`groups/${group.id}`)
    ElMessage.success('群組已刪除')
    fetchGroups()
  })
}

const handleManageProviders = (group: Group) => {
  currentGroup.value = group
  const groupProviderMap = new Map()
  group.providers.forEach((p: any) => {
    groupProviderMap.set(p.id, p.priority)
  })

  allProviders.value.forEach(p => {
    const pVal = groupProviderMap.get(p.id)
    p.selected = groupProviderMap.has(p.id)
    p.priority = p.selected ? (pVal > 5 ? 0 : pVal) : 0
    lastPriorities.set(p.id, p.priority)
  })

  manageDialogVisible.value = true
}

const sortProviders = (providers: any[]) => {
  return [...providers].sort((a, b) => (a.priority || 99) - (b.priority || 99))
}

const filteredProviders = computed(() => {
  const search = providerSearch.value.toLowerCase()
  
  // 分成兩組：已選中（置頂）與未選中
  const selected = allProviders.value.filter(p => p.selected)
  const unselected = allProviders.value.filter(p => !p.selected)
  
  // 僅對未選中的進行搜尋篩選
  const filteredUnselected = search
    ? unselected.filter(p => p.name.toLowerCase().includes(search) || p.model.toLowerCase().includes(search))
    : unselected

  // 已選中的按優先級排序
  const sortedSelected = selected.sort((a, b) => {
    const pA = a.priority || 999
    const pB = b.priority || 999
    if (pA !== pB) return pA - pB
    return a.name.localeCompare(b.name)
  })

  // 未選中的按名稱排序
  const sortedUnselected = filteredUnselected.sort((a, b) => a.name.localeCompare(b.name))

  // 合併：已選中永遠在最上方
  return [...sortedSelected, ...sortedUnselected]
})

const toggleSelect = (row: Provider) => {
  row.selected = !row.selected
  if (!row.selected) {
    handlePriorityChange(row, 0)
  }
}

const handlePriorityChange = (row: Provider, val: any) => {
  const oldVal = lastPriorities.get(row.id) || 0
  if (val === oldVal) return

  if (val === 0) {
    const oldP = oldVal // 使用快照中的舊值，因為 row.priority 可能已被 v-model 改為 0
    row.priority = 0
    row.selected = false
    // 4.3 自動補上功能：取消某個優先級時，後面的自動往前遞補
    if (oldP > 0 && oldP <= 5) {
      allProviders.value.forEach(p => {
        if (p.selected && p.priority > oldP && p.priority <= 5) {
          p.priority -= 1
          lastPriorities.set(p.id, p.priority)
        }
      })
    }
    lastPriorities.set(row.id, 0)
    return
  }
  
  // 4.4 排隊關係 (順延邏輯)
  allProviders.value.forEach(p => {
    if (p.id !== row.id && p.selected && p.priority >= val && p.priority <= 5) {
      p.priority += 1
      if (p.priority > 5) {
        p.priority = 0
        p.selected = false
      }
      lastPriorities.set(p.id, p.priority)
    }
  })
  
  row.priority = val
  row.selected = true
  lastPriorities.set(row.id, val)
}

const saveManagement = async () => {
  if (!currentGroup.value) return
  loading.value = true
  try {
    const providersData = allProviders.value.map(p => ({
      id: p.id,
      priority: p.priority > 0 ? p.priority : 99,
      selected: p.selected
    }))
    
    await request.put(`groups/${currentGroup.value.id}/providers`, providersData)
    
    ElMessage.success('保存成功')
    manageDialogVisible.value = false
    fetchGroups()
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchGroups()
  fetchAllProviders()
})
</script>

<style scoped>
.groups-container { padding: 10px; }
.header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.action-row { margin-bottom: 20px; }
.group-card { border-left: 4px solid #409EFF; }
.group-header { display: flex; justify-content: space-between; align-items: center; }
.group-name { font-size: 18px; font-weight: bold; margin-right: 15px; }
.group-meta { font-size: 12px; color: #909399; }
.group-providers { margin-top: 10px; display: flex; flex-wrap: wrap; }
.mr-2 { margin-right: 8px; }

.provider-info-cell {
  padding: 8px;
  cursor: pointer;
  border-radius: 4px;
}
.provider-info-cell.is-selected { background-color: #ecf5ff; }

.priority-selector {
  display: flex;
  justify-content: center;
  gap: 10px;
  padding: 8px;
}
.priority-selector.is-selected { background-color: #ecf5ff; }

.p-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.p-label {
  font-size: 10px;
  font-weight: bold;
  color: #909399;
  margin-bottom: -2px;
  transition: color 0.3s;
}
.p-label.is-active {
  color: #409EFF;
}
.pagination-container { margin-top: 20px; display: flex; justify-content: flex-end; }
</style>