import request from '@/utils/request'

export const getSummary = (params) => request.get('/api/dashboard/summary', { params })
export const getTrend = (params) => request.get('/api/dashboard/trend', { params })
export const getByProject = (params) => request.get('/api/dashboard/by-project', { params })
export const getRanking = (params) => request.get('/api/dashboard/ranking', { params })
