<template>
  <div class="coverage-page">
    <a-card class="filter-card">
      <a-form layout="inline">
        <a-form-item label="时间范围">
          <a-range-picker
            v-model:value="dateRange"
            :placeholder="['开始日期', '结束日期']"
          />
        </a-form-item>
        <a-form-item label="项目">
          <a-select
            v-model:value="filterProjectId"
            placeholder="全部项目"
            allow-clear
            style="width: 180px"
          >
            <a-select-option v-for="p in projects" :key="p.id" :value="p.id">
              {{ p.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="成员">
          <a-select
            v-model:value="filterMemberId"
            placeholder="全部成员"
            allow-clear
            style="width: 180px"
          >
            <a-select-option v-for="m in members" :key="m.id" :value="m.id">
              {{ m.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="handleSearch">查询</a-button>
          <a-button style="margin-left: 8px" @click="handleReset">重置</a-button>
        </a-form-item>
      </a-form>
    </a-card>

    <a-card class="chart-card">
      <v-chart :option="trendOption" autoresize style="height: 300px" />
    </a-card>

    <a-card>
      <template #title>
        <div class="table-header">
          <span>覆盖率</span>
          <a-space>
            <a-dropdown>
              <template #overlay>
                <a-menu @click="handleExport">
                  <a-menu-item key="by-project">按项目导出</a-menu-item>
                  <a-menu-item key="by-member">按成员导出</a-menu-item>
                </a-menu>
              </template>
              <a-button type="primary" ghost>
                <DownloadOutlined /> 导出Excel
              </a-button>
            </a-dropdown>
          </a-space>
        </div>
      </template>
      <a-tabs v-model:active-key="activeTab">
        <a-tab-pane key="detail" tab="覆盖率明细">
          <a-table
            :data-source="tableData"
            :columns="columns"
            :loading="loading"
            :pagination="pagination"
            row-key="id"
            @change="handleTableChange"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'coverage_rate'">
                <a-progress
                  :percent="record.coverage_rate"
                  :size="'small'"
                  :stroke-color="record.coverage_rate > 50 ? '#52c41a' : '#faad14'"
                />
              </template>
            </template>
          </a-table>
        </a-tab-pane>
        <a-tab-pane key="member" tab="按成员聚合">
          <a-table
            :data-source="memberTableData"
            :columns="memberColumns"
            :loading="memberLoading"
            :pagination="memberPagination"
            row-key="rowKey"
            @change="handleMemberTableChange"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'coverage_rate'">
                <a-progress
                  :percent="record.coverage_rate"
                  :size="'small'"
                  :stroke-color="record.coverage_rate > 50 ? '#52c41a' : '#faad14'"
                />
              </template>
            </template>
          </a-table>
        </a-tab-pane>
      </a-tabs>
    </a-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, GridComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { DownloadOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { getCoverage, getCoverageTrend, getCoverageByMember } from '@/api/coverage'
import { useAppStore } from '@/stores/app'

use([CanvasRenderer, LineChart, TitleComponent, TooltipComponent, GridComponent, LegendComponent])

const appStore = useAppStore()
const projects = computed(() => appStore.projects)
const members = computed(() => appStore.members)

const activeTab = ref('detail')

const dateRange = ref(null)
const filterProjectId = ref(null)
const filterMemberId = ref(null)
const loading = ref(false)
const tableData = ref([])
const trendData = ref([])

const memberLoading = ref(false)
const memberTableData = ref([])

const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showTotal: (total) => `共 ${total} 条`,
})

const memberPagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showTotal: (total) => `共 ${total} 条`,
})

const columns = [
  { title: '日期', dataIndex: 'date', key: 'date', width: 120 },
  { title: '成员', dataIndex: 'member_name', key: 'member_name' },
  { title: '项目', dataIndex: 'project_name', key: 'project_name' },
  { title: 'AI代码行数', dataIndex: 'ai_lines', key: 'ai_lines', sorter: true },
  { title: '总代码行数', dataIndex: 'total_lines', key: 'total_lines', sorter: true },
  { title: '覆盖率', key: 'coverage_rate', width: 200 },
]

const memberColumns = [
  { title: '成员', dataIndex: 'member_name', key: 'member_name' },
  { title: '项目', dataIndex: 'project_name', key: 'project_name' },
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

const getFilterParams = () => {
  const params = {}
  if (filterProjectId.value) params.project_id = filterProjectId.value
  if (filterMemberId.value) params.member_id = filterMemberId.value
  if (dateRange.value?.length === 2) {
    params.start_date = dateRange.value[0].format('YYYY-MM-DD')
    params.end_date = dateRange.value[1].format('YYYY-MM-DD')
  }
  return params
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      ...getFilterParams(),
      page: pagination.current,
      per_page: pagination.pageSize,
    }
    const res = await getCoverage(params)
    tableData.value = res.data.items || []
    pagination.total = res.data.total || 0
  } finally {
    loading.value = false
  }
}

const fetchMemberData = async () => {
  memberLoading.value = true
  try {
    const params = {
      ...getFilterParams(),
      page: memberPagination.current,
      per_page: memberPagination.pageSize,
    }
    const res = await getCoverageByMember(params)
    const items = res.data.items || []
    memberTableData.value = items.map((item, index) => ({
      ...item,
      rowKey: `${item.member_id || 'm'}-${item.project_id || 'p'}-${index}`,
    }))
    memberPagination.total = res.data.total || 0
  } finally {
    memberLoading.value = false
  }
}

const fetchTrend = async () => {
  const res = await getCoverageTrend(getFilterParams())
  trendData.value = res.data || []
}

const handleSearch = () => {
  pagination.current = 1
  memberPagination.current = 1
  fetchData()
  fetchTrend()
  fetchMemberData()
}

const handleReset = () => {
  dateRange.value = null
  filterProjectId.value = null
  filterMemberId.value = null
  handleSearch()
}

const handleTableChange = (pag) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchData()
}

const handleMemberTableChange = (pag) => {
  memberPagination.current = pag.current
  memberPagination.pageSize = pag.pageSize
  fetchMemberData()
}

const handleExport = ({ key }) => {
  const params = new URLSearchParams()
  const filters = getFilterParams()
  Object.entries(filters).forEach(([k, v]) => { if (v) params.set(k, v) })

  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  const url = key === 'by-project'
    ? `${baseUrl}/api/export/by-project?${params}`
    : `${baseUrl}/api/export/by-member?${params}`

  window.open(url, '_blank')
  message.success('正在下载...')
}

onMounted(async () => {
  await Promise.all([appStore.fetchProjects(), appStore.fetchMembers()])
  handleSearch()
})
</script>

<style scoped>
.filter-card {
  margin-bottom: 16px;
}

.chart-card {
  margin-bottom: 16px;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
