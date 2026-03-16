import request from '@/utils/request'

export const getCoverage = (params) => request.get('/api/coverage', { params })
export const getCoverageTrend = (params) => request.get('/api/coverage/trend', { params })
export const getCoverageByMember = (params) => request.get('/api/coverage/by-member', { params })
