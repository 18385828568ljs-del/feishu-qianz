import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:8000',
  timeout: 20000,
})

// 是否开启调试日志（仅开发环境）
const DEBUG = import.meta.env.DEV

// 添加请求拦截器
api.interceptors.request.use(
  (config) => {
    if (DEBUG) console.log('[API]', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => Promise.reject(error)
)

// 添加响应拦截器
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (DEBUG) console.error('[API Error]', error.config?.url, error.response?.status)
    return Promise.reject(error)
  }
)

export async function authStart() {
  const { data } = await api.get('/auth/start')
  return data // { auth_url, state }
}

export async function authStatus(sessionId) {
  const { data } = await api.get('/auth/status', { params: { session_id: sessionId } })
  return data // { authorized, expires_at, user }
}

export async function uploadSignature({ blob, fileName, sessionId, folderToken, useUserToken = 1, openId, tenantKey }) {
  const form = new FormData()
  form.append('file', blob, fileName || 'signature.png')
  form.append('file_name', fileName || 'signature.png')
  form.append('use_user_token', useUserToken ? 1 : 0)
  if (sessionId) form.append('session_id', sessionId)
  if (folderToken) form.append('folder_token', folderToken)
  if (openId) form.append('open_id', openId)
  if (tenantKey) form.append('tenant_key', tenantKey)
  const { data } = await api.post('/api/sign/upload', form)
  return data.file_token
}

export async function getQuota(openId, tenantKey) {
  const { data } = await api.get('/api/quota/status', { params: { open_id: openId, tenant_key: tenantKey } })
  return data
}

// 检查是否可以签名
export async function checkCanSign(openId, tenantKey) {
  const { data } = await api.get('/api/quota/check', { params: { open_id: openId, tenant_key: tenantKey } })
  return data // { can_sign, reason, consume_quota }
}

// 消耗配额
export async function consumeQuota(openId, tenantKey, fileToken, fileName) {
  const { data } = await api.post('/api/quota/consume', null, {
    params: { open_id: openId, tenant_key: tenantKey, file_token: fileToken, file_name: fileName }
  })
  return data
}

// 验证邀请码
export async function validateInvite(code) {
  const { data } = await api.post('/api/invite/validate', { code })
  return data // { valid, benefit, remaining_uses }
}

// 兑换邀请码
export async function redeemInvite(code, openId, tenantKey) {
  const { data } = await api.post('/api/invite/redeem', { code, open_id: openId, tenant_key: tenantKey })
  return data
}

// 获取定价方案
export async function getPricingPlans() {
  const { data } = await api.get('/api/payment/plans')
  return data.plans
}

// 创建支付订单
export async function createOrder(planId, openId, tenantKey) {
  const { data } = await api.post('/api/payment/create', { plan_id: planId, open_id: openId, tenant_key: tenantKey })
  return data
}

// 模拟支付（测试用）
export async function mockPay(orderId) {
  const { data } = await api.post('/api/payment/mock-pay', null, { params: { order_id: orderId } })
  return data
}

// 查询订单状态
export async function getOrderStatus(orderId) {
  const { data } = await api.get(`/api/payment/status/${orderId}`)
  return data
}

// 创建分享表单
export async function createShareForm(formData) {
  const { data } = await api.post('/api/form/create', formData)
  return data
}

// 获取分享表单列表
export async function getShareFormList(createdBy) {
  const { data } = await api.get('/api/form/list', { params: { created_by: createdBy } })
  return data
}

// 获取多维表格字段列表
export async function getTableFields(appToken, tableId, sessionId) {
  const { data } = await api.get('/api/form/table-fields', {
    params: { app_token: appToken, table_id: tableId, session_id: sessionId }
  })
  return data
}
