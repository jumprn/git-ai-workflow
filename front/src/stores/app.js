import { ref } from 'vue'
import { defineStore } from 'pinia'
import { getProjects } from '@/api/project'
import { getMembers } from '@/api/member'

export const useAppStore = defineStore('app', () => {
  const projects = ref([])
  const members = ref([])
  const collapsed = ref(false)

  const fetchProjects = async () => {
    const res = await getProjects()
    projects.value = res.data || []
  }

  const fetchMembers = async () => {
    const res = await getMembers()
    members.value = res.data || []
  }

  const toggleCollapsed = () => {
    collapsed.value = !collapsed.value
  }

  return { projects, members, collapsed, fetchProjects, fetchMembers, toggleCollapsed }
})
