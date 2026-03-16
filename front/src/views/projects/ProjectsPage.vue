<template>
  <div class="projects-page">
    <div class="page-actions">
      <a-button type="primary" @click="showAddModal">
        <PlusOutlined /> 添加项目
      </a-button>
      <a-button style="margin-left: 8px" @click="handleScanAll" :loading="scanAllLoading">
        <SyncOutlined /> 扫描全部
      </a-button>
    </div>

    <a-table
      :data-source="projectList"
      :columns="columns"
      :loading="loading"
      row-key="id"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-tag :color="statusColor(record.status)">{{ statusText(record.status) }}</a-tag>
        </template>
        <template v-if="column.key === 'actions'">
          <a-space>
            <a-button type="link" size="small" @click="handleScan(record)">增量扫描</a-button>
            <a-popconfirm title="将清空该项目的 commit 缓存并重新扫描全部提交，确定？" @confirm="() => handleFullScan(record)">
              <a-button type="link" size="small" danger>全量扫描</a-button>
            </a-popconfirm>
            <a-button type="link" size="small" @click="showEditModal(record)">编辑</a-button>
            <a-popconfirm title="确定删除该项目？" @confirm="handleDelete(record.id)">
              <a-button type="link" danger size="small">删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal
      v-model:open="modalVisible"
      :title="isEdit ? '编辑项目' : '添加项目'"
      @ok="handleSubmit"
      :confirm-loading="submitLoading"
      :width="560"
    >
      <a-form :model="form" :label-col="{ span: 5 }" :wrapper-col="{ span: 18 }">
        <a-form-item label="项目名称" required>
          <a-input v-model:value="form.name" placeholder="请输入项目名称" />
        </a-form-item>
        <a-form-item label="仓库地址" required>
          <a-input v-model:value="form.repo_url" placeholder="https://github.com/..." />
        </a-form-item>
        <a-form-item label="默认分支">
          <a-input v-model:value="form.branch" placeholder="main" />
        </a-form-item>
        <a-form-item label="认证方式">
          <a-radio-group v-model:value="form.auth_type">
            <a-radio value="token">访问令牌</a-radio>
            <a-radio value="password">账号密码</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item v-if="form.auth_type === 'token'" label="访问令牌">
          <a-input-password v-model:value="form.auth_token" placeholder="请输入访问令牌" />
        </a-form-item>
        <template v-if="form.auth_type === 'password'">
          <a-form-item label="用户名">
            <a-input v-model:value="form.auth_username" placeholder="请输入用户名" />
          </a-form-item>
          <a-form-item label="密码">
            <a-input-password v-model:value="form.auth_password" placeholder="请输入密码" />
          </a-form-item>
        </template>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="scanModalVisible"
      title="扫描进度"
      :footer="null"
      :closable="scanTask?.status !== 'running'"
      :mask-closable="false"
    >
      <div v-if="scanTask" class="scan-progress">
        <a-progress :percent="scanTask.progress" :status="scanProgressStatus" />
        <p class="scan-phase">{{ scanTask.current_phase || '等待中...' }}</p>
        <p v-if="scanTask.total_commits" class="scan-detail">
          提交检查: {{ scanTask.checked_commits || 0 }}/{{ scanTask.total_commits }}
        </p>
        <p v-if="scanTask.total_files" class="scan-detail">
          文件分析: {{ scanTask.scanned_files || 0 }}/{{ scanTask.total_files }}
        </p>
        <a-alert
          v-if="scanTask.status === 'failed'"
          type="error"
          :message="scanTask.message || '扫描失败'"
          show-icon
          style="margin-top: 12px"
        />
        <a-alert
          v-if="scanTask.status === 'completed'"
          type="success"
          message="扫描完成"
          show-icon
          style="margin-top: 12px"
        />
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined, SyncOutlined } from '@ant-design/icons-vue'
import { getProjects, createProject, updateProject, deleteProject } from '@/api/project'
import { startScan, getScanProgress, scanAll } from '@/api/scan'

const loading = ref(false)
const projectList = ref([])
const modalVisible = ref(false)
const submitLoading = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const scanAllLoading = ref(false)

const scanModalVisible = ref(false)
const scanTask = ref(null)
let pollTimer = null

const form = ref({
  name: '',
  repo_url: '',
  branch: 'main',
  auth_type: 'token',
  auth_token: '',
  auth_username: '',
  auth_password: '',
})

const columns = [
  { title: '项目名称', dataIndex: 'name', key: 'name' },
  { title: '仓库地址', dataIndex: 'repo_url', key: 'repo_url', ellipsis: true },
  { title: '分支', dataIndex: 'branch', key: 'branch', width: 100 },
  { title: '状态', key: 'status', width: 100 },
  { title: '最后扫描', dataIndex: 'last_scan_at', key: 'last_scan_at', width: 180 },
  { title: '操作', key: 'actions', width: 200 },
]

const statusColor = (s) => ({ pending: 'default', cloning: 'processing', ready: 'success', error: 'error' }[s] || 'default')
const statusText = (s) => ({ pending: '待初始化', cloning: '克隆中', ready: '就绪', error: '错误' }[s] || s)

const scanProgressStatus = computed(() => {
  if (!scanTask.value) return 'normal'
  if (scanTask.value.status === 'completed') return 'success'
  if (scanTask.value.status === 'failed') return 'exception'
  return 'active'
})

const fetchProjects = async () => {
  loading.value = true
  try {
    const res = await getProjects()
    projectList.value = res.data || []
  } finally {
    loading.value = false
  }
}

const showAddModal = () => {
  isEdit.value = false
  editId.value = null
  form.value = { name: '', repo_url: '', branch: 'main', auth_type: 'token', auth_token: '', auth_username: '', auth_password: '' }
  modalVisible.value = true
}

const showEditModal = (record) => {
  isEdit.value = true
  editId.value = record.id
  form.value = {
    name: record.name,
    repo_url: record.repo_url,
    branch: record.branch || 'main',
    auth_type: record.auth_type || 'token',
    auth_token: '',
    auth_username: '',
    auth_password: '',
  }
  modalVisible.value = true
}

const handleSubmit = async () => {
  if (!form.value.name || !form.value.repo_url) {
    message.warning('请填写项目名称和仓库地址')
    return
  }
  submitLoading.value = true
  try {
    if (isEdit.value) {
      await updateProject(editId.value, form.value)
      message.success('项目已更新')
    } else {
      await createProject(form.value)
      message.success('项目已添加')
    }
    modalVisible.value = false
    await fetchProjects()
  } finally {
    submitLoading.value = false
  }
}

const handleDelete = async (id) => {
  await deleteProject(id)
  message.success('项目已删除')
  await fetchProjects()
}

const handleScan = async (record) => {
  try {
    const res = await startScan(record.id, false)
    scanTask.value = res.data
    scanModalVisible.value = true
    startPolling(res.data.id)
  } catch (e) {
    // error handled by interceptor
  }
}

const handleFullScan = async (record) => {
  try {
    const res = await startScan(record.id, true)
    scanTask.value = res.data
    scanModalVisible.value = true
    startPolling(res.data.id)
  } catch (e) {
    // error handled by interceptor
  }
}

const handleScanAll = async () => {
  scanAllLoading.value = true
  try {
    await scanAll()
    message.success('已启动全部项目扫描')
    await fetchProjects()
  } finally {
    scanAllLoading.value = false
  }
}

const startPolling = (taskId) => {
  stopPolling()
  pollTimer = setInterval(async () => {
    const res = await getScanProgress(taskId)
    scanTask.value = res.data
    if (res.data.status === 'completed' || res.data.status === 'failed') {
      stopPolling()
      await fetchProjects()
    }
  }, 2000)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(fetchProjects)
onUnmounted(stopPolling)
</script>

<style scoped>
.page-actions {
  margin-bottom: 16px;
}

.scan-progress {
  padding: 16px 0;
}

.scan-phase {
  margin-top: 12px;
  color: #666;
  font-size: 14px;
}

.scan-detail {
  margin-top: 4px;
  color: #999;
  font-size: 13px;
}
</style>
