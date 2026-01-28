/**
 * 授权组合式函数
 * 使用授权码模式
 */
import { computed } from 'vue'
import { useBaseToken } from './useBaseToken'

export function useAuth() {
    const { hasBaseToken } = useBaseToken()
    
    const authorized = computed(() => hasBaseToken.value)
    
    function startAuth(showToast) {
        showToast?.('请点击上方"授权码"按钮配置您的授权码', 'info', 3000)
    }
    
    return {
        authorized,
        startAuth
    }
}
