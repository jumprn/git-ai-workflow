<template>
  <div class="settings-page">
    <a-card title="存储设置" style="margin-bottom: 16px">
      <a-form :model="configForm" :label-col="{ span: 6 }" :wrapper-col="{ span: 14 }">
        <a-form-item label="仓库存放目录">
          <a-input
            v-model:value="configForm.repos_dir"
            placeholder="例如: C:/ai-coverage-repos 或 /data/repos"
          />
          <span class="form-hint">克隆的远程仓库存放路径（绝对路径），为空则使用 .env 中的默认值</span>
        </a-form-item>
      </a-form>
    </a-card>

    <a-card title="定时扫描设置">
      <a-form :model="configForm" :label-col="{ span: 6 }" :wrapper-col="{ span: 10 }">
        <a-form-item label="启用定时扫描">
          <a-switch v-model:checked="configForm.scan_enabled" />
        </a-form-item>
        <a-form-item label="扫描时间（小时）">
          <a-input-number
            v-model:value="configForm.scan_hour"
            :min="0"
            :max="23"
            style="width: 120px"
          />
          <span class="form-hint">0-23，每天在该小时执行扫描</span>
        </a-form-item>
        <a-form-item label="扫描时间（分钟）">
          <a-input-number
            v-model:value="configForm.scan_minute"
            :min="0"
            :max="59"
            style="width: 120px"
          />
        </a-form-item>
        <a-form-item label="扫描间隔（天）">
          <a-input-number
            v-model:value="configForm.scan_interval_days"
            :min="1"
            :max="30"
            style="width: 120px"
          />
        </a-form-item>
        <a-form-item :wrapper-col="{ offset: 6, span: 10 }">
          <a-button type="primary" :loading="saving" @click="handleSave">保存配置</a-button>
        </a-form-item>
      </a-form>
    </a-card>

    <a-card title="扫描历史" style="margin-top: 16px">
      <a-table
        :data-source="scanTasks"
        :columns="taskColumns"
        :loading="tasksLoading"
        row-key="id"
        size="middle"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="taskStatusColor(record.status)">{{ taskStatusText(record.status) }}</a-tag>
          </template>
          <template v-if="column.key === 'progress'">
            <a-progress :percent="record.progress" size="small" :status="record.status === 'failed' ? 'exception' : undefined" />
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { getConfigs, updateConfigs } from '@/api/config'
import { getScanTasks } from '@/api/scan'

const configForm = ref({
  repos_dir: '',
  scan_enabled: true,
  scan_hour: 2,
  scan_minute: 0,
  scan_interval_days: 1,
})
const saving = ref(false)
const scanTasks = ref([])
const tasksLoading = ref(false)

const taskColumns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
  { title: '项目', dataIndex: 'project_name', key: 'project_name' },
  { title: '类型', dataIndex: 'scan_type', key: 'scan_type', width: 80 },
  { title: '状态', key: 'status', width: 100 },
  { title: '进度', key: 'progress', width: 180 },
  { title: '开始时间', dataIndex: 'started_at', key: 'started_at', width: 180 },
  { title: '完成时间', dataIndex: 'completed_at', key: 'completed_at', width: 180 },
]

const taskStatusColor = (s) => ({ pending: 'default', running: 'processing', completed: 'success', failed: 'error' }[s] || 'default')
const taskStatusText = (s) => ({ pending: '等待中', running: '进行中', completed: '已完成', failed: '失败' }[s] || s)

const fetchConfigs = async () => {
  const res = await getConfigs()
  const configs = res.data || []
  for (const c of configs) {
    if (c.key === 'scan_enabled') configForm.value.scan_enabled = c.value === 'true'
    if (c.key === 'scan_hour') configForm.value.scan_hour = parseInt(c.value) || 2
    if (c.key === 'scan_minute') configForm.value.scan_minute = parseInt(c.value) || 0
    if (c.key === 'scan_interval_days') configForm.value.scan_interval_days = parseInt(c.value) || 1
    if (c.key === 'repos_dir') configForm.value.repos_dir = c.value || ''
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    await updateConfigs([
      { key: 'repos_dir', value: configForm.value.repos_dir },
      { key: 'scan_enabled', value: String(configForm.value.scan_enabled) },
      { key: 'scan_hour', value: String(configForm.value.scan_hour) },
      { key: 'scan_minute', value: String(configForm.value.scan_minute) },
      { key: 'scan_interval_days', value: String(configForm.value.scan_interval_days) },
    ])
    message.success('配置已保存')
  } finally {
    saving.value = false
  }
}

const fetchTasks = async () => {
  tasksLoading.value = true
  try {
    const res = await getScanTasks({})
    scanTasks.value = res.data || []
  } finally {
    tasksLoading.value = false
  }
}

onMounted(() => {
  fetchConfigs()
  fetchTasks()
})
</script>

<style scoped>
.form-hint {
  margin-left: 12px;
  color: #999;
  font-size: 13px;
}
</style>
