<template>
  <div class="members-page">
    <div class="page-actions">
      <a-button type="primary" @click="showAddModal">
        <PlusOutlined /> 添加成员
      </a-button>
    </div>

    <a-table
      :data-source="memberList"
      :columns="columns"
      :loading="loading"
      row-key="id"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'source'">
          <a-tag :color="record.is_manual ? 'blue' : 'green'">
            {{ record.is_manual ? '手动添加' : '自动提取' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'actions'">
          <a-space>
            <a-button type="link" size="small" @click="showEditModal(record)">编辑</a-button>
            <a-popconfirm title="确定删除该成员？" @confirm="handleDelete(record.id)">
              <a-button type="link" danger size="small">删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal
      v-model:open="modalVisible"
      :title="isEdit ? '编辑成员' : '添加成员'"
      @ok="handleSubmit"
      :confirm-loading="submitLoading"
    >
      <a-form :model="form" :label-col="{ span: 5 }" :wrapper-col="{ span: 18 }">
        <a-form-item label="姓名" required>
          <a-input v-model:value="form.name" placeholder="请输入成员姓名" />
        </a-form-item>
        <a-form-item label="邮箱">
          <a-input v-model:value="form.email" placeholder="请输入邮箱" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { getMembers, createMember, updateMember, deleteMember } from '@/api/member'

const loading = ref(false)
const memberList = ref([])
const modalVisible = ref(false)
const submitLoading = ref(false)
const isEdit = ref(false)
const editId = ref(null)

const form = ref({ name: '', email: '' })

const columns = [
  { title: '姓名', dataIndex: 'name', key: 'name' },
  { title: '邮箱', dataIndex: 'email', key: 'email' },
  { title: '来源', key: 'source', width: 120 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '操作', key: 'actions', width: 150 },
]

const fetchMembers = async () => {
  loading.value = true
  try {
    const res = await getMembers()
    memberList.value = res.data || []
  } finally {
    loading.value = false
  }
}

const showAddModal = () => {
  isEdit.value = false
  editId.value = null
  form.value = { name: '', email: '' }
  modalVisible.value = true
}

const showEditModal = (record) => {
  isEdit.value = true
  editId.value = record.id
  form.value = { name: record.name, email: record.email || '' }
  modalVisible.value = true
}

const handleSubmit = async () => {
  if (!form.value.name) {
    message.warning('请填写成员姓名')
    return
  }
  submitLoading.value = true
  try {
    if (isEdit.value) {
      await updateMember(editId.value, form.value)
      message.success('成员已更新')
    } else {
      await createMember(form.value)
      message.success('成员已添加')
    }
    modalVisible.value = false
    await fetchMembers()
  } finally {
    submitLoading.value = false
  }
}

const handleDelete = async (id) => {
  await deleteMember(id)
  message.success('成员已删除')
  await fetchMembers()
}

onMounted(fetchMembers)
</script>

<style scoped>
.page-actions {
  margin-bottom: 16px;
}
</style>
