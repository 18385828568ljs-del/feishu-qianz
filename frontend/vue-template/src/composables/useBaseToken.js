/**
 * 授权码管理 Composable
 * 用于存储和获取用户的飞书授权码 (PersonalBaseToken)
 */
import { ref, computed } from 'vue'

// localStorage 存储键名
const STORAGE_KEY = 'feishu_base_token'

// 响应式状态
const baseToken = ref(localStorage.getItem(STORAGE_KEY) || '')

/**
 * 授权码管理 Hook
 */
export function useBaseToken() {
  /**
   * 设置授权码
   * @param {string} token - 授权码
   */
  function setBaseToken(token) {
    baseToken.value = token
    if (token) {
      localStorage.setItem(STORAGE_KEY, token)
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  /**
   * 获取授权码
   * @returns {string}
   */
  function getBaseToken() {
    return baseToken.value
  }

  /**
   * 清除授权码
   */
  function clearBaseToken() {
    baseToken.value = ''
    localStorage.removeItem(STORAGE_KEY)
  }

  /**
   * 检查是否已配置授权码
   */
  const hasBaseToken = computed(() => !!baseToken.value)

  return {
    baseToken,
    hasBaseToken,
    setBaseToken,
    getBaseToken,
    clearBaseToken
  }
}
