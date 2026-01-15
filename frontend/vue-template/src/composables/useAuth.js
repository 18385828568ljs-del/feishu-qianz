/**
 * 授权组合式函数
 * 封装飞书授权逻辑
 */
import { ref } from 'vue'
import { authStart, authStatus } from '@/services/api'

// 响应式状态
const sessionId = ref('')
const authorized = ref(false)

/**
 * 发起飞书授权
 * @param {Function} showToast - Toast 通知函数
 * @returns {Promise<void>}
 */
async function startAuth(showToast) {
    try {
        console.log('[Auth] Starting auth flow...')
        const { auth_url } = await authStart()
        console.log('[Auth] Got auth_url:', auth_url)

        // 打开新窗口进行飞书用户授权
        const win = window.open(auth_url, '_blank', 'width=720,height=720')
        if (!win) {
            showToast?.('无法打开授权窗口，请检查浏览器弹窗设置', 'error', 3000)
            return
        }

        const handler = async (ev) => {
            console.log('[Auth] Received message:', ev.data)
            if (!ev?.data || ev.data.type !== 'feishu-auth-done' || !ev.data.session_id) {
                console.log('[Auth] Message ignored:', ev.data)
                return
            }
            sessionId.value = ev.data.session_id
            console.log('[Auth] Got session_id:', sessionId.value)
            window.removeEventListener('message', handler)

            // 查询授权状态（带重试机制，因为可能存在时序问题）
            let retryCount = 0
            const maxRetries = 3
            const checkAuthStatus = async () => {
                try {
                    console.log(`[Auth] Checking auth status (attempt ${retryCount + 1}/${maxRetries})...`)
                    const st = await authStatus(sessionId.value)
                    console.log('[Auth] Auth status response:', st)
                    authorized.value = !!st.authorized
                    if (authorized.value) {
                        showToast?.('已授权，可将文件上传到个人空间', 'success')
                    } else {
                        // 如果未授权且还有重试次数，延迟后重试
                        if (retryCount < maxRetries - 1) {
                            retryCount++
                            console.log(`[Auth] Not authorized yet, retrying in 500ms...`)
                            setTimeout(checkAuthStatus, 500)
                        } else {
                            console.error('[Auth] Auth status check failed after retries')
                            showToast?.('授权状态异常，请重新授权', 'warning')
                        }
                    }
                } catch (e) {
                    console.error('[Auth] Status check error:', e)
                    // 如果还有重试次数，延迟后重试
                    if (retryCount < maxRetries - 1) {
                        retryCount++
                        console.log(`[Auth] Error occurred, retrying in 500ms...`)
                        setTimeout(checkAuthStatus, 500)
                    } else {
                        showToast?.('授权状态检查失败，但 session_id 已保存', 'warning')
                    }
                }
            }
            // 延迟100ms后开始检查，确保后端已处理完回调
            setTimeout(checkAuthStatus, 100)
            if (win && !win.closed) win.close()
        }
        window.addEventListener('message', handler)

        // 设置超时
        setTimeout(() => {
            if (!authorized.value && !sessionId.value) {
                console.warn('[Auth] Timeout waiting for auth callback')
                showToast?.('授权超时，请检查授权窗口是否正常关闭', 'warning', 3000)
            }
        }, 30000)

        // 定时检查窗口是否关闭
        const checkWindowClosed = setInterval(() => {
            if (win && win.closed) {
                clearInterval(checkWindowClosed)
            }
        }, 500)
    } catch (e) {
        console.error('[Auth] Error:', e)
        showToast?.('打开授权页失败：' + (e?.message || e), 'error')
    }
}

/**
 * 重置授权状态
 */
function resetAuth() {
    sessionId.value = ''
    authorized.value = false
}

export function useAuth() {
    return {
        sessionId,
        authorized,
        startAuth,
        resetAuth
    }
}
