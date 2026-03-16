import request from '@/utils/request'

export const getCoverage = (params) => request.get('/api/coverage', { params })
export const getCoverageTrend = (params) => request.get('/api/coverage/trend', { params })
