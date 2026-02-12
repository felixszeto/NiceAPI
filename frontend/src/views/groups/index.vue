<template>
  <div class="space-y-6">
    <!-- 頁面標題列 -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold text-gray-900">分組管理</h1>
        <p class="text-sm text-gray-500 mt-1">管理 API 供應商分組與優先級配置</p>
      </div>
      <div class="flex items-center gap-2">
        <el-button :icon="Refresh" @click="fetchGroups" circle />
        <el-button type="primary" :icon="Plus" @click="handleAddGroup">創建分組</el-button>
      </div>
    </div>

    <!-- 群組卡片列表 -->
    <div v-loading="loading" class="space-y-4">
      <div
        v-for="group in groups"
        :key="group.id"
        class="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
      >
        <!-- 卡片頭部 -->
        <div class="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center flex-shrink-0">
              <el-icon :size="20"><Folder /></el-icon>
            </div>
            <div class="min-w-0">
              <h3 class="text-base font-semibold text-gray-900 truncate">{{ group.name }}</h3>
              <div class="flex items-center gap-2 text-xs text-gray-400 mt-0.5">
                <span>ID: {{ group.id }}</span>
                <span class="w-1 h-1 rounded-full bg-gray-300"></span>
                <span>{{ group.providers?.length || 0 }} 個供應商</span>
              </div>
            </div>
          </div>
          <div class="flex items-center gap-2 flex-shrink-0">
            <el-button type="primary" plain size="small" :icon="Setting" @click="handleManageProviders(group)">
              管理供應商
            </el-button>
            <el-button type="danger" plain size="small" :icon="Delete" @click="handleDeleteGroup(group)" />
          </div>
        </div>

        <!-- 供應商標籤 -->
        <div v-if="group.providers && group.providers.length" class="px-4 sm:px-5 pb-4 flex flex-wrap gap-1.5">
          <el-tag
            v-for="p in sortProviders(group.providers).slice(0, isMobile ? 5 : 10)"
            :key="p.id"
            size="small"
            effect="plain"
            :type="p.priority <= 2 ? 'primary' : 'info'"
            class="!rounded-md"
          >
            P{{ p.priority }}: {{ p.name }}.{{ p.model }}
          </el-tag>
          <el-tag
            v-if="group.providers.length > (isMobile ? 5 : 10)"
            size="small"
            type="info"
            effect="plain"
            class="!rounded-md"
          >
            +{{ group.providers.length - (isMobile ? 5 : 10) }} 更多
          </el-tag>
        </div>
        <div v-else class="px-4 sm:px-5 pb-4">
          <span class="text-xs text-gray-400">尚未添加供應商</span>
        </div>
      </div>

      <!-- 空狀態 -->
      <div v-if="!loading && groups.length === 0" class="text-center py-16">
        <el-icon :size="48" class="text-gray-300 mb-3"><Folder /></el-icon>
        <p class="text-gray-400">暫無分組，點擊上方按鈕創建</p>
      </div>
    </div>

    <!-- 分頁 -->
    <div v-if="total > 0" class="flex justify-end">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :layout="isMobile ? 'total, prev, next' : 'total, sizes, prev, pager, next, jumper'"
        :total="total"
        :small="isMobile"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 管理供應商對話框 -->
    <el-dialog
      v-model="manageDialogVisible"
      :title="'管理供應商: ' + currentGroup?.name"
      :width="isMobile ? '95%' : '900px'"
      :fullscreen="isMobile"
      destroy-on-close
    >
      <div class="space-y-4">
        <el-input
          v-model="providerSearch"
          placeholder="搜尋供應商或模型..."
          :prefix-icon="Search"
          clearable
          size="large"
        />

        <!-- 桌面端表格 -->
        <div class="hidden sm:block">
          <el-table :data="filteredProviders" style="width: 100%" height="450px" size="small" border>
            <el-table-column label="模型/別名" min-width="200">
              <template #default="scope">
                <div
                  class="p-2 rounded-lg cursor-pointer transition-colors"
                  :class="scope.row.selected ? 'bg-blue-50' : 'hover:bg-gray-50'"
                  @click="toggleSelect(scope.row)"
                >
                  <div class="font-semibold text-sm text-gray-900">{{ scope.row.model }}</div>
                  <div class="text-xs text-gray-500 mt-0.5">{{ scope.row.name }}</div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="優先級 (P1-P5)" width="350" align="center">
              <template #default="scope">
                <div
                  class="flex justify-center gap-2.5 p-2 rounded-lg"
                  :class="{ 'bg-blue-50': scope.row.selected }"
                >
                  <div v-for="p in 5" :key="p" class="flex flex-col items-center gap-0.5">
                    <span
                      class="text-[10px] font-bold transition-colors"
                      :class="scope.row.priority === p ? 'text-blue-600' : 'text-gray-400'"
                    >P{{ p }}</span>
                    <el-switch
                      v-model="scope.row.priority"
                      :active-value="p"
                      :inactive-value="lastPriorities.get(scope.row.id) === p ? 0 : scope.row.priority"
                      @change="(val: any) => handlePriorityChange(scope.row, val)"
                      size="small"
                    />
                  </div>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 移動端卡片列表 -->
        <div class="sm:hidden space-y-2 max-h-[60vh] overflow-y-auto">
          <div
            v-for="provider in filteredProviders"
            :key="provider.id"
            class="p-3 rounded-xl border transition-colors"
            :class="provider.selected ? 'border-blue-300 bg-blue-50' : 'border-gray-200 bg-white'"
            @click="toggleSelect(provider)"
          >
            <div class="flex items-center justify-between mb-2">
              <div class="min-w-0 flex-1">
                <div class="font-semibold text-sm text-gray-900 truncate">{{ provider.model }}</div>
                <div class="text-xs text-gray-500">{{ provider.name }}</div>
              </div>
              <el-tag v-if="provider.selected && provider.priority > 0" size="small" type="primary">
                P{{ provider.priority }}
              </el-tag>
            </div>
            <div v-if="provider.selected" class="flex justify-center gap-3 pt-2 border-t border-gray-100" @click.stop>
              <div v-for="p in 5" :key="p" class="flex flex-col items-center gap-0.5">
                <span
                  class="text-[10px] font-bold"
                  :class="provider.priority === p ? 'text-blue-600' : 'text-gray-400'"
                >P{{ p }}</span>
                <el-switch
                  v-model="provider.priority"
                  :active-value="p"
                  :inactive-value="lastPriorities.get(provider.id) === p ? 0 : provider.priority"
                  @change="(val: any) => handlePriorityChange(provider, val)"
                  size="small"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <el-button @click="manageDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveManagement" :loading="loading">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Plus, Refresh, Setting, Delete, Folder, Search } from '@element-plus/icons-vue'
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

const screenWidth = ref(window.innerWidth)
const isMobile = computed(() => screenWidth.value < 768)

const onResize = () => { screenWidth.value = window.innerWidth }

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
  const selected = allProviders.value.filter(p => p.selected)
  const unselected = allProviders.value.filter(p => !p.selected)
  const filteredUnselected = search
    ? unselected.filter(p => p.name.toLowerCase().includes(search) || p.model.toLowerCase().includes(search))
    : unselected
  const sortedSelected = selected.sort((a, b) => {
    const pA = a.priority || 999
    const pB = b.priority || 999
    if (pA !== pB) return pA - pB
    return a.name.localeCompare(b.name)
  })
  const sortedUnselected = filteredUnselected.sort((a, b) => a.name.localeCompare(b.name))
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
    const oldP = oldVal
    row.priority = 0
    row.selected = false
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
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
})
</script>