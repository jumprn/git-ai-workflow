<template>
  <div class="dashboard">
    <a-row :gutter="16" class="summary-row">
      <a-col :span="6">
        <a-card class="stat-card">
          <a-statistic title="项目总数" :value="summary.total_projects" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card">
          <a-statistic title="成员总数" :value="summary.total_members" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card">
          <a-statistic
            title="平均AI覆盖率"
            :value="summary.avg_coverage"
            suffix="%"
            :precision="2"
          />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card">
          <a-statistic title="AI代码行数" :value="summary.total_ai_lines" />
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="16" class="chart-row">
      <a-col :span="16">
        <a-card title="覆盖率趋势" class="chart-card">
          <div class="chart-filters">
            <a-range-picker
              v-model:value="trendDateRange"
              :placeholder="['开始日期', '结束日期']"
              @change="fetchTrend"
            />
            <a-select
              v-model:value="trendProjectId"
              placeholder="全部项目"
              allow-clear
              style="width: 180px; margin-left: 12px"
              @change="fetchTrend"
            >
              <a-select-option v-for="p in projects" :key="p.id" :value="p.id">
                {{ p.name }}
              </a-select-option>
            </a-select>
          </div>
          <v-chart :option="trendOption" autoresize style="height: 320px" />
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card title="各项目覆盖率" class="chart-card">
          <v-chart :option="projectOption" autoresize style="height: 320px" />
        </a-card>
      </a-col>
    </a-row>

    <a-card title="成员覆盖率排行" class="ranking-card">
      <a-table
        :data-source="ranking"
        :columns="rankingColumns"
        :pagination="false"
        size="middle"
        row-key="member_id"
      >
        <template #bodyCell="{ column, record, index }">
          <template v-if="column.key === 'rank'">
            <a-tag :color="index < 3 ? 'gold' : 'default'">{{ index + 1 }}</a-tag>
          </template>
          <template v-if="column.key === 'coverage_rate'">
            <a-progress
              :percent="record.coverage_rate"
              :size="'small'"
              :stroke-color="record.coverage_rate > 50 ? '#52c41a' : '#faad14'"
            />
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, GridComponent,
  LegendComponent, DataZoomComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import dayjs from 'dayjs'
import { getSummary, getTrend, getByProject, getRanking } from '@/api/dashboard'
import { useAppStore } from '@/stores/app'

use([
  CanvasRenderer, LineChart, BarChart,
  TitleComponent, TooltipComponent, GridComponent,
  LegendComponent, DataZoomComponent,
])

const appStore = useAppStore()
const projects = computed(() => appStore.projects)

const summary = ref({
  total_projects: 0,
  total_members: 0,
  avg_coverage: 0,
  total_ai_lines: 0,
  total_lines: 0,
})
const trendData = ref([])
const projectData = ref([])
const ranking = ref([])

const trendDateRange = ref(null)
const trendProjectId = ref(null)

const rankingColumns = [
  { title: '排名', key: 'rank', width: 70 },
  { title: '成员', dataIndex: 'member_name', key: 'member_name' },
  { title: 'AI代码行数', dataIndex: 'ai_lines', key: 'ai_lines' },
  { title: '总代码行数', dataIndex: 'total_lines', key: 'total_lines' },
  { title: '覆盖率', key: 'coverage_rate', width: 200 },
]

const trendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 60, right: 20, top: 20, bottom: 40 },
  xAxis: {
    type: 'category',
    data: trendData.value.map((d) => d.date),
    axisLabel: { rotate: 30 },
  },
  yAxis: { type: 'value', name: '覆盖率(%)', max: 100 },
  series: [
    {
      name: 'AI覆盖率',
      type: 'line',
      data: trendData.value.map((d) => d.coverage_rate),
      smooth: true,
      areaStyle: { opacity: 0.15 },
      itemStyle: { color: '#4472C4' },
    },
  ],
}))

const projectOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 80, right: 20, top: 10, bottom: 20 },
  xAxis: { type: 'value', name: '%', max: 100 },
  yAxis: {
    type: 'category',
    data: projectData.value.map((d) => d.project_name),
    axisLabel: { width: 60, overflow: 'truncate' },
  },
  series: [
    {
      type: 'bar',
      data: projectData.value.map((d) => d.coverage_rate),
      itemStyle: { color: '#4472C4', borderRadius: [0, 4, 4, 0] },
      barMaxWidth: 24,
    },
  ],
}))

const fetchSummary = async () => {
  const res = await getSummary()
  summary.value = res.data
}

const fetchTrend = async () => {
  const params = {}
  if (trendProjectId.value) params.project_id = trendProjectId.value
  if (trendDateRange.value?.length === 2) {
    params.start_date = trendDateRange.value[0].format('YYYY-MM-DD')
    params.end_date = trendDateRange.value[1].format('YYYY-MM-DD')
  }
  const res = await getTrend(params)
  trendData.value = res.data || []
}

const fetchProjectData = async () => {
  const res = await getByProject()
  projectData.value = res.data || []
}

const fetchRanking = async () => {
  const res = await getRanking({ limit: 10 })
  ranking.value = res.data || []
}

onMounted(async () => {
  await appStore.fetchProjects()
  await Promise.all([fetchSummary(), fetchTrend(), fetchProjectData(), fetchRanking()])
})
</script>

<style scoped>
.summary-row {
  margin-bottom: 16px;
}

.stat-card {
  text-align: center;
}

.chart-row {
  margin-bottom: 16px;
}

.chart-card {
  height: 100%;
}

.chart-filters {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
}

.ranking-card {
  margin-bottom: 16px;
}
</style>
