<template>
  <div class="dashboard-container" v-loading="loading">
    <div class="header-row">
      <h2>儀表板</h2>
      <el-button type="primary" link icon="Refresh" @click="fetchStats">刷新數據</el-button>
    </div>

    <el-row :gutter="24" class="stats-row">
      <el-col :xs="24" :sm="12" :md="6" v-for="item in statCards" :key="item.label" style="margin-bottom: 12px">
        <div class="stat-card shadow-sm">
          <div :class="['icon-box', `bg-${item.color}`]">
            <el-icon><component :is="item.icon" /></el-icon>
          </div>
          <div class="content-box">
            <div class="label">{{ item.label }}</div>
            <div class="value">{{ item.value }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="24" class="charts-row">
      <el-col :xs="24" :sm="24" :md="12" style="margin-bottom: 24px">
        <el-card class="chart-card" shadow="never">
          <template #header>模型使用分佈</template>
          <v-chart class="chart" :option="modelDistributionOption" autoresize />
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="24" :md="12" style="margin-bottom: 24px">
        <el-card class="chart-card" shadow="never">
          <template #header>每日 API 調用次數</template>
          <v-chart class="chart" :option="dailyCallsOption" autoresize />
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="24" :md="12" style="margin-bottom: 24px">
        <el-card class="chart-card" shadow="never">
          <template #header>API 調用成功率</template>
          <v-chart class="chart" :option="successRatePieOption" autoresize />
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="24" :md="12" style="margin-bottom: 24px">
        <el-card class="chart-card" shadow="never">
          <template #header>平均響應時間 (按模型)</template>
          <v-chart class="chart" :option="modelAvgTimeOption" autoresize />
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="24" :md="12" style="margin-bottom: 24px">
        <el-card class="chart-card" shadow="never">
          <template #header>API 端點成功率</template>
          <v-chart class="chart" :option="endpointSuccessOption" autoresize />
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="24" :md="12" style="margin-bottom: 24px">
        <el-card class="chart-card" shadow="never">
          <template #header>平均響應時間 (按端點)</template>
          <v-chart class="chart" :option="endpointAvgTimeOption" autoresize />
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="24" :md="12" style="margin-bottom: 24px">
        <el-card class="chart-card" shadow="never">
          <template #header>總 API 調用 (按端點)</template>
          <v-chart class="chart" :option="endpointTotalCallsOption" autoresize />
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="24" :md="12" style="margin-bottom: 24px">
        <el-card class="chart-card" shadow="never">
          <template #header>總費用 (按模型)</template>
          <v-chart class="chart" :option="modelCostOption" autoresize />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import request from '../../utils/request'

const loading = ref(false)
const stats = ref<any>({
  summary: { total_calls: 0, success_rate: 0, total_tokens: 0, api_keys: 0 },
  model_distribution: [],
  daily_calls: { dates: [], values: [] },
  endpoint_stats: { names: [], success_rates: [], avg_times: [], total_calls: [] },
  model_stats: { names: [], avg_times: [] },
  cost_stats: { names: [], values: [] }
})

const statCards = computed(() => [
  { label: 'API 調用次數', value: stats.value.summary.total_calls.toLocaleString(), icon: 'Lightning', color: 'blue' },
  { label: '成功率', value: `${stats.value.summary.success_rate}%`, icon: 'CircleCheck', color: 'green' },
  { label: '總消耗 Tokens', value: stats.value.summary.total_tokens.toLocaleString(), icon: 'Coin', color: 'orange' },
  { label: '總估算費用', value: `$${stats.value.summary.total_cost || 0}`, icon: 'Money', color: 'purple' }
])

const modelDistributionOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { orient: 'vertical', left: 'left', type: 'plain' },
  series: [{
    name: 'API 調用',
    type: 'pie',
    radius: '70%',
    data: stats.value.model_distribution,
    emphasis: {
      itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' }
    }
  }]
}))

const dailyCallsOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: stats.value.daily_calls.dates },
  yAxis: { type: 'value' },
  series: [{ data: stats.value.daily_calls.values, type: 'bar', itemStyle: { color: '#2F6BFF' } }]
}))

const successRatePieOption = computed(() => {
  const success = stats.value.summary.total_calls * (stats.value.summary.success_rate / 100)
  const fail = stats.value.summary.total_calls - success
  return {
    tooltip: { trigger: 'item' },
    color: ['#10B981', '#EF4444'],
    legend: { top: '5%', left: 'center', type: 'plain' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      label: { show: false, position: 'center' },
      emphasis: { label: { show: true, fontSize: '20', fontWeight: 'bold' } },
      data: [
        { value: Math.round(success), name: '成功' },
        { value: Math.round(fail), name: '失敗' }
      ]
    }]
  }
})

const modelAvgTimeOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: stats.value.model_stats.names, axisLabel: { rotate: 30 } },
  yAxis: { type: 'value', name: 'ms' },
  series: [{ data: stats.value.model_stats.avg_times, type: 'bar', itemStyle: { color: '#2F6BFF' } }]
}))

const endpointSuccessOption = computed(() => ({
  tooltip: { trigger: 'axis', formatter: '{b}: {c}%' },
  xAxis: { type: 'category', data: stats.value.endpoint_stats.names, axisLabel: { rotate: 15 } },
  yAxis: { type: 'value', min: 0, max: 100, axisLabel: { formatter: '{value}%' } },
  series: [{ data: stats.value.endpoint_stats.success_rates, type: 'bar', itemStyle: { color: '#2F6BFF' } }]
}))

const endpointAvgTimeOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: stats.value.endpoint_stats.names, axisLabel: { rotate: 15 } },
  yAxis: { type: 'value', name: 'ms' },
  series: [{ data: stats.value.endpoint_stats.avg_times, type: 'bar', itemStyle: { color: '#2F6BFF' } }]
}))

const endpointTotalCallsOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: stats.value.endpoint_stats.names, axisLabel: { rotate: 15 } },
  yAxis: { type: 'value' },
  series: [{ data: stats.value.endpoint_stats.total_calls, type: 'bar', itemStyle: { color: '#2F6BFF' } }]
}))

const modelCostOption = computed(() => ({
  tooltip: { trigger: 'axis', formatter: '{b}: ${c}' },
  xAxis: { type: 'category', data: stats.value.cost_stats.names, axisLabel: { rotate: 30 } },
  yAxis: { type: 'value', name: '$' },
  series: [{ data: stats.value.cost_stats.values, type: 'bar', itemStyle: { color: '#2F6BFF' } }]
}))

const fetchStats = async () => {
  loading.value = true
  try {
    const data: any = await request.get('dashboard/stats')
    stats.value = data
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

onMounted(fetchStats)
</script>

<style scoped>
.dashboard-container { padding: 10px; }
.header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.stats-row { margin-bottom: 24px; }
.stat-card {
  display: flex;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #ebeef5;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  transition: transform 0.2s;
}
.stat-card:hover {
  transform: translateY(-2px);
}
.icon-box {
  width: 70px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 28px;
}
.bg-blue { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); }
.bg-green { background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
.bg-orange { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
.bg-purple { background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); }

.content-box { padding: 15px 20px; }
.label { font-size: 12px; color: #666; margin-bottom: 4px; }
.value { font-size: 20px; font-weight: bold; }

.charts-row { margin-bottom: 24px; }
.chart-card {
  height: 400px;
  border-radius: 12px;
  border: none;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
}
.chart-card :deep(.el-card__body) {
  overflow: visible !important;
}
.chart { height: 320px; }
</style>