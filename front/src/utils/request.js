import axios from 'axios'
import { message } from 'ant-design-vue'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 30000,
})

request.interceptors.response.use(
  (response) => {
    const { code, message: msg, data } = response.data
    if (code === 200) return response.data
    message.error(msg || '请求失败')
    return Promise.reject(new Error(msg))
  },
  (error) => {
    message.error(error.message || '网络异常')
    return Promise.reject(error)
  }
)

export default request
