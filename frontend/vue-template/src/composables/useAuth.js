/**
 * 授权组合式函数
 * 简化版本：使用授权码模式，不再需要 OAuth 流程
 */
import { ref, computed } from 'vue'
import { useBaseToken } from './useBaseToken'

// 响应式状态
const sessionId = ref('')

/**
 * 授权组合式函数
 */
export function useAuth() {
    const { hasBaseToken } = useBaseToken()
    
    // 授权状态现在基于是否配置了授权码
    const authorized = computed(() => hasBaseToken.value)
    
    /**
     * 发起授权（打开授权码配置弹窗）
     * @param {Function} showToast - Toast 通知函数
     */
    function startAuth(showToast) {
        // 在授权码模式下，提示用户去配置授权码
        showToast?.('请点击上方“授权码”按钮配置您的授权码', 'info', 3000)
    }
    
    /**
     * 重置授权状态
     */
    function resetAuth() {
        sessionId.value = ''
    }
    
    /**
     * 初始化授权状态
     */
    function initAuth() {
        // 授权码模式下无需初始化
    }
    
    /**
     * 验证 sessionId
     */
    async function verifySessionId() {
        // 授权码模式下无需验证
    }
    
    return {
        sessionId,
        authorized,
        startAuth,
        resetAuth,
        initAuth,
        verifySessionId
    }
}
