<template>
  <div class="settings-container">
    <div class="header-row">
      <h2>系統設置</h2>
    </div>

    <el-card class="settings-card shadow-sm" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span class="title">故障轉移設置</span>
          <div class="subtitle">配置自動偵測並切換故障供應商的閾值</div>
        </div>
      </template>

      <el-form :model="settings" label-position="top">
        <el-form-item label="故障次數閾值">
          <el-input-number v-model="settings.failover_threshold_count" :min="1" style="width: 100%" />
          <div class="tip">在指定時間內失敗達到此處次數則觸發轉移</div>
        </el-form-item>

        <el-form-item label="故障統計週期 (分鐘)">
          <el-input-number v-model="settings.failover_threshold_period_minutes" :min="1" style="width: 100%" />
          <div class="tip">統計失敗次數的時間窗口</div>
        </el-form-item>

        <el-form-item class="mt-8">
          <el-button type="primary" @click="saveSettings" size="large" class="w-full">保存設置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import request from '../../utils/request'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const settings = ref({
  failover_threshold_count: 2,
  failover_threshold_period_minutes: 5
})

const fetchSettings = async () => {
  loading.value = true
  try {
    const count: any = await request.get('settings/failover_threshold_count')
    const period: any = await request.get('settings/failover_threshold_period_minutes')
    settings.value.failover_threshold_count = parseInt(count.value)
    settings.value.failover_threshold_period_minutes = parseInt(period.value)
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const saveSettings = async () => {
  try {
    await request.post('settings/', {
      key: 'failover_threshold_count',
      value: settings.value.failover_threshold_count.toString()
    })
    await request.post('settings/', {
      key: 'failover_threshold_period_minutes',
      value: settings.value.failover_threshold_period_minutes.toString()
    })
    ElMessage.success('設置已成功保存')
  } catch (error) {
    console.error(error)
  }
}

onMounted(fetchSettings)
</script>

<style scoped>
.settings-container { padding: 10px; }
.header-row { margin-bottom: 20px; }
.settings-card { max-width: 500px; }
.card-header .title { font-size: 18px; font-weight: bold; }
.card-header .subtitle { font-size: 12px; color: #909399; margin-top: 4px; }
.tip { font-size: 12px; color: #909399; line-height: 1.4; margin-top: 4px; }
.mt-8 { margin-top: 32px; }
.w-full { width: 100%; }
</style>