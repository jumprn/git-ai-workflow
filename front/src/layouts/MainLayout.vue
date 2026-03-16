<template>
  <a-layout class="main-layout">
    <a-layout-sider
      v-model:collapsed="collapsed"
      :trigger="null"
      collapsible
      theme="dark"
      :width="220"
    >
      <div class="logo">
        <span v-if="!collapsed">AI Coverage</span>
        <span v-else>AC</span>
      </div>
      <a-menu
        theme="dark"
        mode="inline"
        :selected-keys="selectedKeys"
        @click="handleMenuClick"
      >
        <a-menu-item key="Dashboard">
          <template #icon><DashboardOutlined /></template>
          <span>总览</span>
        </a-menu-item>
        <a-menu-item key="Coverage">
          <template #icon><BarChartOutlined /></template>
          <span>覆盖率查询</span>
        </a-menu-item>
        <a-menu-item key="Projects">
          <template #icon><FolderOutlined /></template>
          <span>项目管理</span>
        </a-menu-item>
        <a-menu-item key="Members">
          <template #icon><TeamOutlined /></template>
          <span>成员管理</span>
        </a-menu-item>
        <a-menu-item key="Settings">
          <template #icon><SettingOutlined /></template>
          <span>系统设置</span>
        </a-menu-item>
      </a-menu>
    </a-layout-sider>

    <a-layout>
      <a-layout-header class="layout-header">
        <MenuUnfoldOutlined
          v-if="collapsed"
          class="trigger"
          @click="() => (collapsed = !collapsed)"
        />
        <MenuFoldOutlined
          v-else
          class="trigger"
          @click="() => (collapsed = !collapsed)"
        />
        <span class="header-title">{{ currentTitle }}</span>
      </a-layout-header>

      <a-layout-content class="layout-content">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  DashboardOutlined,
  BarChartOutlined,
  FolderOutlined,
  TeamOutlined,
  SettingOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons-vue'

const router = useRouter()
const route = useRoute()
const collapsed = ref(false)

const selectedKeys = computed(() => [route.name])
const currentTitle = computed(() => route.meta.title || 'AI代码覆盖率看板')

const handleMenuClick = ({ key }) => {
  router.push({ name: key })
}
</script>

<style scoped>
.main-layout {
  min-height: 100vh;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 1px;
  background: rgba(255, 255, 255, 0.08);
}

.layout-header {
  background: #fff;
  padding: 0 24px;
  display: flex;
  align-items: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  z-index: 1;
}

.trigger {
  font-size: 18px;
  cursor: pointer;
  transition: color 0.3s;
}

.trigger:hover {
  color: #1890ff;
}

.header-title {
  margin-left: 16px;
  font-size: 16px;
  font-weight: 500;
}

.layout-content {
  margin: 24px;
  padding: 24px;
  background: #fff;
  border-radius: 8px;
  min-height: 280px;
}
</style>
