import request from '@/utils/request'

export const startScan = (projectId, fullScan = false) =>
  request.post('/api/scan/start', { project_id: projectId, full_scan: fullScan })
export const getScanProgress = (taskId) => request.get(`/api/scan/progress/${taskId}`)
export const getScanTasks = (params) => request.get('/api/scan/tasks', { params })
export const scanAll = () => request.post('/api/scan/scan-all')
