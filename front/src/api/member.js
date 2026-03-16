import request from '@/utils/request'

export const getMembers = () => request.get('/api/members')
export const getMember = (id) => request.get(`/api/members/${id}`)
export const createMember = (data) => request.post('/api/members', data)
export const updateMember = (id, data) => request.put(`/api/members/${id}`, data)
export const deleteMember = (id) => request.delete(`/api/members/${id}`)
