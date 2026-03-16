import request from '@/utils/request'

export const getConfigs = () => request.get('/api/config')
export const updateConfigs = (data) => request.put('/api/config', data)
export const getConfigByKey = (key) => request.get(`/api/config/${key}`)
