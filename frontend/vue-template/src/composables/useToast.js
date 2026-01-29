/**
 * Toast 通知组合式函数
 * 提供全局 Toast 通知功能 (基于 Element Plus ElMessage)
 */
import { ElMessage } from 'element-plus'

/**
 * 显示 Toast 通知
 * @param {string} message - 消息内容
 * @param {'success'|'error'|'warning'|'info'} type - 消息类型
 * @param {number} duration - 显示时长（毫秒）
 */
function showToast(message, type = 'info', duration = 2000) {
    ElMessage({
        message,
        type,
        duration,
        grouping: true,
        showClose: true
    })
}

/**
 * 清除 Toast (ElMessage 自动管理，保留函数仅为兼容)
 */
function clearToast() {
    ElMessage.closeAll()
}

export function useToast() {
    return {
        showToast,
        clearToast,
        // 保留空ref以兼容旧代码解构，虽然不再使用
        toastMessage: { value: '' },
        toastType: { value: 'info' }
    }
}
