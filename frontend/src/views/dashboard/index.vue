<template>
  <div v-loading="loading" class="min-h-screen">
    <!-- Stats cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div
        v-for="item in statCards"
        :key="item.label"
        class="bg-white rounded-xl border border-slate-200 p-5 flex items-center gap-4 hover:shadow-md transition-shadow"
      >
        <div
          class="w-12 h-12 rounded-xl flex items-center justify-center text-white text-xl shrink-0"
          :class="item.bgClass"
        >
          <el-icon><component :is="item.icon" /></el-icon>
        </div>
        <div class="min-w-0">
          <div class="text-xs text-slate-500 font-medium">{{ item.label }}</div>
          <div class="text-xl font-bold text-slate-800 mt-0.5 truncate">{{ item.value }}</div>
        </div>
      </div>
    </div>

    <!-- Charts grid -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
      <div v-for="chart in charts" :key="chart.title" class="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div class="px-5 py-4 border-b border-slate-100">
          <h3 class="text-sm font-semibold text-slate-700">{{ chart.title }}</h3>
        </div>
        <div class="p-4 relative">
          <!-- 確保父容器有明確的最小高度且寬度隨佈局撐開 -->
          <div class="h-[280px] md:h-[320px] w-full relative">
            <v-chart
              v-if="!loading && statsLoaded"
              class="absolute inset-0 w-full h-full"
              :option="chart.option"
              autoresize
            />
            <div v-else class="absolute inset-0 flex flex-col items-center justify-center text-slate-400 text-xs italic">
              <el-icon class="is-loading mb-2 text-xl"><Loading /></el-icon>
              正在準備圖表數據...
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import request from '../../utils/request'

const loading = ref(true)
const statsLoaded = ref(false)
const stats = ref<any>({
  summary: { total_calls: 0, success_rate: 0, total_tokens: 0, api_keys: 0 },
  model_distribution: [],
  daily_calls: { dates: [], values: [] },
  endpoint_stats: { names: [], success_rates: [], avg_times: [], total_calls: [] },
  model_stats: { names: [], avg_times: [] },
  cost_stats: { names: [], values: [] }
})

const statCards = computed(() => [
  { label: 'API 調用次數', value: stats.value.summary.total_calls.toLocaleString(), icon: 'Lightning', bgClass: 'bg-gradient-to-br from-blue-500 to-blue-600' },
  { label: '成功率', value: `${stats.value.summary.success_rate}%`, icon: 'CircleCheck', bgClass: 'bg-gradient-to-br from-emerald-500 to-emerald-600' },
  { label: '總消耗 Tokens', value: stats.value.summary.total_tokens.toLocaleString(), icon: 'Coin', bgClass: 'bg-gradient-to-br from-amber-500 to-amber-600' },
  { label: '總估算費用', value: `$${stats.value.summary.total_cost || 0}`, icon: 'Money', bgClass: 'bg-gradient-to-br from-violet-500 to-violet-600' }
])

const chartColors = {
  primary: '#3b82f6',
  success: '#22c55e',
  danger: '#ef4444',
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true }
}

const modelDistributionOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { orient: 'vertical', left: 'left', type: 'scroll', textStyle: { fontSize: 12 } },
  series: [{
    name: 'API 調用',
    type: 'pie',
    radius: '65%',
    data: stats.value.model_distribution,
    emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.3)' } }
  }]
}))

const dailyCallsOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: chartColors.grid,
  xAxis: { type: 'category', data: stats.value.daily_calls.dates, axisLabel: { fontSize: 11 } },
  yAxis: { type: 'value', axisLabel: { fontSize: 11 } },
  series: [{ data: stats.value.daily_calls.values, type: 'bar', itemStyle: { color: chartColors.primary, borderRadius: [4, 4, 0, 0] } }]
}))

const successRatePieOption = computed(() => {
  const success = stats.value.summary.total_calls * (stats.value.summary.success_rate / 100)
  const fail = stats.value.summary.total_calls - success
  return {
    tooltip: { trigger: 'item' },
    color: [chartColors.success, chartColors.danger],
    legend: { top: '5%', left: 'center', type: 'plain', textStyle: { fontSize: 12 } },
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      avoidLabelOverlap: false,
      label: { show: false, position: 'center' },
      emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
      data: [
        { value: Math.round(success), name: '成功' },
        { value: Math.round(fail), name: '失敗' }
      ]
    }]
  }
})

const modelAvgTimeOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: chartColors.grid,
  xAxis: { type: 'category', data: stats.value.model_stats.names, axisLabel: { rotate: 30, fontSize: 11 } },
  yAxis: { type: 'value', name: 'ms', axisLabel: { fontSize: 11 } },
  series: [{ data: stats.value.model_stats.avg_times, type: 'bar', itemStyle: { color: chartColors.primary, borderRadius: [4, 4, 0, 0] } }]
}))

const endpointSuccessOption = computed(() => ({
  tooltip: { trigger: 'axis', formatter: '{b}: {c}%' },
  grid: chartColors.grid,
  xAxis: { type: 'category', data: stats.value.endpoint_stats.names, axisLabel: { rotate: 15, fontSize: 11 } },
  yAxis: { type: 'value', min: 0, max: 100, axisLabel: { formatter: '{value}%', fontSize: 11 } },
  series: [{ data: stats.value.endpoint_stats.success_rates, type: 'bar', itemStyle: { color: chartColors.success, borderRadius: [4, 4, 0, 0] } }]
}))

const endpointAvgTimeOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: chartColors.grid,
  xAxis: { type: 'category', data: stats.value.endpoint_stats.names, axisLabel: { rotate: 15, fontSize: 11 } },
  yAxis: { type: 'value', name: 'ms', axisLabel: { fontSize: 11 } },
  series: [{ data: stats.value.endpoint_stats.avg_times, type: 'bar', itemStyle: { color: '#8b5cf6', borderRadius: [4, 4, 0, 0] } }]
}))

const endpointTotalCallsOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: chartColors.grid,
  xAxis: { type: 'category', data: stats.value.endpoint_stats.names, axisLabel: { rotate: 15, fontSize: 11 } },
  yAxis: { type: 'value', axisLabel: { fontSize: 11 } },
  series: [{ data: stats.value.endpoint_stats.total_calls, type: 'bar', itemStyle: { color: '#f59e0b', borderRadius: [4, 4, 0, 0] } }]
}))

const modelCostOption = computed(() => ({
  tooltip: { trigger: 'axis', formatter: '{b}: ${c}' },
  grid: chartColors.grid,
  xAxis: { type: 'category', data: stats.value.cost_stats.names, axisLabel: { rotate: 30, fontSize: 11 } },
  yAxis: { type: 'value', name: '$', axisLabel: { fontSize: 11 } },
  series: [{ data: stats.value.cost_stats.values, type: 'bar', itemStyle: { color: '#ec4899', borderRadius: [4, 4, 0, 0] } }]
}))

const charts = computed(() => [
  { title: '模型使用分佈', option: modelDistributionOption.value },
  { title: '每日 API 調用次數', option: dailyCallsOption.value },
  { title: 'API 調用成功率', option: successRatePieOption.value },
  { title: '平均響應時間 (按模型)', option: modelAvgTimeOption.value },
  { title: 'API 端點成功率', option: endpointSuccessOption.value },
  { title: '平均響應時間 (按端點)', option: endpointAvgTimeOption.value },
  { title: '總 API 調用 (按端點)', option: endpointTotalCallsOption.value },
  { title: '總費用 (按模型)', option: modelCostOption.value },
])

const fetchStats = async () => {
  loading.value = true
  statsLoaded.value = false
  try {
    const data: any = await request.get('dashboard/stats')
    stats.value = data
    // 確保數據更新後等待 DOM 渲染週期
    await nextTick()
  } catch (error) {
    console.error(error)
  } finally {
    // 先讓 loading 指令消失，使 DOM 可見並獲得正確寬高
    loading.value = false
    // 在下一個 tick，當 DOM 已經掛載且具備有效尺寸時，才啟用 v-chart 渲染
    await nextTick()
    setTimeout(() => {
      statsLoaded.value = true
    }, 100)
  }
}

onMounted(fetchStats)
</script>