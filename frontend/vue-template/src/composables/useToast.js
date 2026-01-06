/**
 * Toast 通知组合式函数
 * 提供全局 Toast 通知功能
 */
import { ref } from 'vue'

// 响应式状态
const toastMessage = ref('')
const toastType = ref('info') // 'success' | 'error' | 'warning' | 'info'

/**
 * 显示 Toast 通知
 * @param {string} message - 消息内容
 * @param {'success'|'error'|'warning'|'info'} type - 消息类型
 * @param {number} duration - 显示时长（毫秒）
 */
function showToast(message, type = 'info', duration = 2000) {
    toastMessage.value = message
    toastType.value = type
    setTimeout(() => {
        toastMessage.value = ''
    }, duration)
}

/**
 * 清除 Toast
 */
function clearToast() {
    toastMessage.value = ''
}

export function useToast() {
    return {
        toastMessage,
        toastType,
        showToast,
        clearToast
    }
}
