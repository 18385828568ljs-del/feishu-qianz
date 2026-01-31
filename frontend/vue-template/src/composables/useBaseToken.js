/**
 * 授权码管理 Composable
 * 用于存储和获取用户的飞书授权码 (PersonalBaseToken)
 * 
 * 改进：支持多个多维表格，每个表格独立存储授权码
 */
import { ref, computed } from 'vue'

// localStorage 存储键名
const STORAGE_KEY = 'feishu_base_tokens' // 改为复数，存储多个表格的授权码

// 响应式状态 - 存储所有表格的授权码
const baseTokens = ref(loadBaseTokens())

// 当前表格的 app_token
const currentAppToken = ref('')

// 当前表格的授权码（计算属性）
const currentBaseToken = computed(() => {
  if (!currentAppToken.value) return ''
  return baseTokens.value[currentAppToken.value] || ''
})

// 是否已配置当前表格的授权码
const hasBaseToken = computed(() => !!currentBaseToken.value)

/**
 * 从 localStorage 加载所有授权码
 */
function loadBaseTokens() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      return JSON.parse(stored)
    }
  } catch (e) {
    console.error('[BaseToken] Failed to load tokens:', e)
  }
  
  // 兼容旧版本：如果存在旧的单一授权码，迁移到新格式
  try {
    const oldToken = localStorage.getItem('feishu_base_token')
    if (oldToken) {
      console.log('[BaseToken] Migrating old token format')
      // 无法知道旧 token 对应哪个表格，所以只能清除
      localStorage.removeItem('feishu_base_token')
    }
  } catch (e) {
    console.error('[BaseToken] Migration failed:', e)
  }
  
  return {}
}

/**
 * 保存所有授权码到 localStorage
 */
function saveBaseTokens() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(baseTokens.value))
  } catch (e) {
    console.error('[BaseToken] Failed to save tokens:', e)
  }
}

/**
 * 授权码管理 Hook
 */
export function useBaseToken() {
  /**
   * 设置当前表格的 app_token
   * @param {string} appToken - 多维表格的 app_token
   */
  function setCurrentAppToken(appToken) {
    currentAppToken.value = appToken
    console.log('[BaseToken] Current app_token set:', appToken)
    console.log('[BaseToken] Has token for this app:', !!baseTokens.value[appToken])
    console.log('[BaseToken] hasBaseToken computed:', hasBaseToken.value)
  }

  /**
   * 设置指定表格的授权码
   * @param {string} appToken - 多维表格的 app_token
   * @param {string} token - 授权码
   */
  function setBaseToken(appToken, token) {
    if (!appToken) {
      console.warn('[BaseToken] appToken is required')
      return
    }
    
    if (token) {
      // 使用新对象触发响应式更新
      baseTokens.value = {
        ...baseTokens.value,
        [appToken]: token
      }
      console.log('[BaseToken] Token saved for app:', appToken, 'Token length:', token.length)
    } else {
      // 删除时也创建新对象
      const newTokens = { ...baseTokens.value }
      delete newTokens[appToken]
      baseTokens.value = newTokens
      console.log('[BaseToken] Token removed for app:', appToken)
    }
    saveBaseTokens()
    console.log('[BaseToken] Current tokens:', Object.keys(baseTokens.value))
  }

  /**
   * 获取指定表格的授权码
   * @param {string} appToken - 多维表格的 app_token
   * @returns {string}
   */
  function getBaseToken(appToken) {
    if (!appToken) return ''
    return baseTokens.value[appToken] || ''
  }

  /**
   * 检查指定表格是否已配置授权码
   * @param {string} appToken - 多维表格的 app_token
   * @returns {boolean}
   */
  function hasBaseTokenFor(appToken) {
    if (!appToken) return false
    return !!baseTokens.value[appToken]
  }

  /**
   * 清除指定表格的授权码
   * @param {string} appToken - 多维表格的 app_token
   */
  function clearBaseToken(appToken) {
    if (!appToken) {
      console.warn('[BaseToken] appToken is required')
      return
    }
    const newTokens = { ...baseTokens.value }
    delete newTokens[appToken]
    baseTokens.value = newTokens
    saveBaseTokens()
    console.log('[BaseToken] Token cleared for app:', appToken)
  }

  /**
   * 清除所有授权码
   */
  function clearAllBaseTokens() {
    baseTokens.value = {}
    localStorage.removeItem(STORAGE_KEY)
    console.log('[BaseToken] All tokens cleared')
  }

  /**
   * 获取已配置授权码的表格数量
   * @returns {number}
   */
  function getConfiguredCount() {
    return Object.keys(baseTokens.value).length
  }

  return {
    // 状态
    currentBaseToken,
    hasBaseToken,
    baseTokens,
    
    // 方法
    setCurrentAppToken,
    setBaseToken,
    getBaseToken,
    hasBaseTokenFor,
    clearBaseToken,
    clearAllBaseTokens,
    getConfiguredCount
  }
}
