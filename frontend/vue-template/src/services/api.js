import axios from 'axios'
import { validateUploadParams, validateQuotaParams, getMissingFieldsMessage } from '@/utils/validation'

// ==================== 用户初始化 API ====================

/**
 * 初始化用户 - 首次访问时调用
 * @param {string} feishuUserId - 飞书用户ID
 * @param {string} tenantKey - 租户Key
 * @param {string} fingerprint - 设备指纹
 * @returns {Promise<Object>} { user_id, feishu_user_id, tenant_key, token, token_type, expires_in }
 */
export async function initUser(feishuUserId, tenantKey, fingerprint) {
  const { data } = await api.post('/api/user/init', {
    feishu_user_id: feishuUserId,
    tenant_key: tenantKey,
    fingerprint: fingerprint
  })
  return data
}

// ====================

// baseURL 规则：
// - 显式配置了 VITE_API_BASE：始终优先使用（适合多环境部署）
// - 开发环境（import.meta.env.DEV）：如果未配置，则默认 http://localhost:8000
// - 生产环境：如果未配置，则默认同源 window.location.origin
let defaultBase = 'http://localhost:8000'

if (typeof window !== 'undefined' && window.location?.origin) {
  if (import.meta.env.DEV) {
    // dev 环境下，大部分人后端都跑在 8000，这里保持 8000 作为默认，
    // 避免像现在这样打到了 Vite 的 5173 上导致 404
    defaultBase = 'http://localhost:8000'
  } else {
    // 生产环境默认同源
    defaultBase = window.location.origin
  }
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || defaultBase,
  timeout: 20000,
})

// 是否开启调试日志（仅开发环境）
const DEBUG = import.meta.env.DEV
if (DEBUG) console.log('[API] baseURL =', api.defaults.baseURL)

// 添加请求拦截器 - 自动添加 JWT Token
api.interceptors.request.use(
  (config) => {
    if (DEBUG) console.log('[API]', config.method?.toUpperCase(), config.url)
    
    // 从 localStorage 获取 JWT Token
    const token = localStorage.getItem('feishu_plugin_jwt_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    return config
  },
  (error) => Promise.reject(error)
)

// Token 刷新状态管理
let isRefreshing = false
let failedQueue = []

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

// 添加响应拦截器 - 处理 401 未授权并自动刷新 Token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    
    if (DEBUG) console.error('[API Error]', originalRequest?.url, error.response?.status)
    
    // 如果返回 401 且未重试过，尝试刷新 Token
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // 如果正在刷新，将请求加入队列
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        }).catch(err => {
          return Promise.reject(err)
        })
      }
      
      originalRequest._retry = true
      isRefreshing = true
      
      try {
        if (DEBUG) console.log('[API] Token expired, attempting to refresh...')
        
        // 重新初始化用户
        const { bitable } = await import('@lark-base-open/js-sdk')
        const info = await bitable.bridge.getUserInfo()
        
        // 生成设备指纹
        const generateFingerprint = () => {
          const nav = navigator
          const screen = window.screen
          const components = [
            nav.userAgent,
            nav.language,
            screen.colorDepth,
            screen.width + 'x' + screen.height,
            new Date().getTimezoneOffset(),
            !!window.sessionStorage,
            !!window.localStorage
          ]
          return btoa(components.join('|'))
        }
        
        const fingerprint = generateFingerprint()
        
        // 调用初始化接口获取新 Token
        const initResult = await initUser(
          info.userId || info.openId,
          info.tenantKey,
          fingerprint
        )
        
        // 保存新 Token
        localStorage.setItem('feishu_plugin_jwt_token', initResult.token)
        const expiryTime = Date.now() + (initResult.expires_in * 1000)
        localStorage.setItem('feishu_plugin_jwt_expiry', expiryTime.toString())
        
        if (DEBUG) console.log('[API] Token refreshed successfully')
        
        // 更新请求头
        api.defaults.headers.Authorization = `Bearer ${initResult.token}`
        originalRequest.headers.Authorization = `Bearer ${initResult.token}`
        
        // 处理队列中的请求
        processQueue(null, initResult.token)
        
        // 重试原请求
        return api(originalRequest)
      } catch (refreshError) {
        if (DEBUG) console.error('[API] Token refresh failed:', refreshError)
        
        // 刷新失败，清除 Token
        processQueue(refreshError, null)
        localStorage.removeItem('feishu_plugin_jwt_token')
        localStorage.removeItem('feishu_plugin_jwt_expiry')
        
        // 提示用户刷新页面
        console.warn('[API] Token refresh failed, please reload the page')
        
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }
    
    return Promise.reject(error)
  }
)

export async function uploadSignature({ blob, fileName, folderToken, hasQuota = false, appToken = '' }) {
  // 参数验证
  const validation = validateUploadParams({ blob, fileName, folderToken, openId: 'jwt', tenantKey: 'jwt' })
  if (!validation.valid) {
    const missing = validation.missing.filter(f => f !== 'openId' && f !== 'tenantKey')
    if (missing.length > 0) {
      throw new Error(getMissingFieldsMessage(missing))
    }
  }

  const form = new FormData()
  form.append('file', blob, fileName)
  form.append('file_name', fileName)
  form.append('folder_token', folderToken)
  form.append('has_quota', hasQuota ? 1 : 0)

  // 从 localStorage 获取指定表格的授权码（必填）
  let baseToken = ''
  if (appToken) {
    // 使用新的多表格存储格式
    const tokens = JSON.parse(localStorage.getItem('feishu_base_tokens') || '{}')
    baseToken = tokens[appToken] || ''
  } else {
    // 兼容旧版本单一授权码
    baseToken = localStorage.getItem('feishu_base_token') || ''
  }
  
  if (!baseToken) {
    throw new Error('未配置授权码，请先在插件中配置您的飞书授权码')
  }

  const config = {
    headers: {
      'X-Base-Token': baseToken
    }
  }

  const { data } = await api.post('/api/sign/upload', form, config)
  return data.file_token
}

export async function getQuota() {
  const { data } = await api.get('/api/quota/status')
  return data
}

// 检查是否可以签名
export async function checkCanSign() {
  const { data } = await api.get('/api/quota/check')
  return data
}

// 消耗配额
export async function consumeQuota(fileToken, fileName, count = 1) {
  const { data } = await api.post('/api/quota/consume', null, {
    params: {
      file_token: fileToken,
      file_name: fileName,
      count: count
    }
  })
  return data
}

// 验证邀请码
export async function validateInvite(code) {
  const { data } = await api.post('/api/invite/validate', { code })
  return data // { valid, benefit, remaining_uses }
}

// 兑换邀请码
export async function redeemInvite(code) {
  if (!code) {
    throw new Error('邀请码不能为空')
  }

  const { data } = await api.post('/api/invite/redeem', { code })
  return data
}

// 获取定价方案
export async function getPricingPlans() {
  const { data } = await api.get('/api/pricing/plans')
  // 确保返回数组格式
  if (data && data.plans) {
    return Array.isArray(data.plans) ? data.plans : []
  }
  if (Array.isArray(data)) {
    return data
  }
  return []
}

// 创建支付订单
export async function createOrder(planId) {
  if (!planId) {
    throw new Error('套餐ID不能为空')
  }

  const { data } = await api.post('/api/payment/create', { plan_id: planId })
  return data
}

// 查询订单状态
export async function getOrderStatus(orderId) {
  const { data } = await api.get(`/api/payment/status/${orderId}`)
  return data
}

// 创建分享表单
export async function createShareForm(formData) {
  // 如果没有传递 base_token，从 localStorage 获取
  if (!formData.base_token) {
    const appToken = formData.app_token
    if (appToken) {
      // 使用新的多表格存储格式
      const tokens = JSON.parse(localStorage.getItem('feishu_base_tokens') || '{}')
      formData.base_token = tokens[appToken] || ''
    } else {
      // 兼容旧版本单一授权码
      formData.base_token = localStorage.getItem('feishu_base_token') || ''
    }
  }
  const { data } = await api.post('/api/form/create', formData)
  return data
}

// 获取分享表单列表（使用JWT认证，不需要传递created_by参数）
export async function getShareFormList() {
  const { data } = await api.get('/api/form/list')
  return data
}

// 获取多维表格字段列表
export async function getTableFields(appToken, tableId) {
  // 使用新的多表格存储格式
  const tokens = JSON.parse(localStorage.getItem('feishu_base_tokens') || '{}')
  const baseToken = tokens[appToken] || localStorage.getItem('feishu_base_token') || ''
  
  const { data } = await api.get('/api/form/table-fields', {
    params: { app_token: appToken, table_id: tableId, base_token: baseToken }
  })
  return data
}

// 获取多维表格记录数量
export async function getRecordCount(appToken, tableId) {
  // 使用新的多表格存储格式
  const tokens = JSON.parse(localStorage.getItem('feishu_base_tokens') || '{}')
  const baseToken = tokens[appToken] || localStorage.getItem('feishu_base_token') || ''
  
  const { data } = await api.get('/api/form/record-count', {
    params: { app_token: appToken, table_id: tableId, base_token: baseToken }
  })
  return data
}

// 获取表单关联记录的数据（公开接口，不需要认证）
export async function getFormRecordData(formId) {
  // 使用不带认证的请求
  const baseURL = import.meta.env.VITE_API_BASE || (import.meta.env.DEV ? 'http://localhost:8000' : window.location.origin)
  const { data } = await axios.get(`${baseURL}/api/form/${formId}/record-data`)
  return data
}

/**
 * 清空所有表单
 */
export async function clearAllForms(createdBy) {
  const { data } = await api.delete('/api/form/clear-all', {
    params: { created_by: createdBy }
  })
  return data
}


// ==================== 支付宝支付 (YunGouOS) ====================

// 创建支付宝支付订单
export async function createAlipayOrder(planId, payType = 'native') {
  if (!planId) {
    throw new Error('套餐ID不能为空')
  }

  const { data } = await api.post('/api/payment/alipay/create', {
    plan_id: planId,
    pay_type: payType
  })
  return data
}

// 查询支付宝订单状态
export async function queryAlipayOrder(orderId) {
  const { data } = await api.get('/api/payment/alipay/query', {
    params: { order_id: orderId }
  })
  return data
}
