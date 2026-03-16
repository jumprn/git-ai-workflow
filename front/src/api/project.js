import request from '@/utils/request'

export const getProjects = () => request.get('/api/projects')
export const getProject = (id) => request.get(`/api/projects/${id}`)
export const createProject = (data) => request.post('/api/projects', data)
export const updateProject = (id, data) => request.put(`/api/projects/${id}`, data)
export const deleteProject = (id) => request.delete(`/api/projects/${id}`)
