/**
 * 授权组合式函数
 * 封装飞书授权逻辑
 */
import { ref } from 'vue'
import { authStart, authStatus } from '@/services/api'

// localStorage 键名
const SESSION_ID_KEY = 'feishu_session_id'

// 响应式状态
const sessionId = ref('')
const authorized = ref(false)

// 初始化标志，确保只初始化一次
let initialized = false

/**
 * 从 localStorage 加载 sessionId
 */
function loadSessionIdFromStorage() {
    try {
        const stored = localStorage.getItem(SESSION_ID_KEY)
        if (stored) {
            sessionId.value = stored
            // 验证 sessionId 是否仍然有效
            verifySessionId()
        }
    } catch (e) {
        console.warn('[Auth] Failed to load sessionId from localStorage:', e)
    }
}

/**
 * 保存 sessionId 到 localStorage
 */
function saveSessionIdToStorage(sid) {
    try {
        if (sid) {
            localStorage.setItem(SESSION_ID_KEY, sid)
        } else {
            localStorage.removeItem(SESSION_ID_KEY)
        }
    } catch (e) {
        console.warn('[Auth] Failed to save sessionId to localStorage:', e)
    }
}

/**
 * 验证 sessionId 是否仍然有效
 */
async function verifySessionId() {
    if (!sessionId.value) {
        authorized.value = false
        return
    }
    
    try {
        const st = await authStatus(sessionId.value)
        authorized.value = !!st.authorized
        // 如果 sessionId 无效，清除它
        if (!authorized.value) {
            console.warn('[Auth] SessionId is invalid, clearing it')
            sessionId.value = ''
            saveSessionIdToStorage('')
        }
    } catch (e) {
        console.warn('[Auth] Failed to verify sessionId:', e)
        // 验证失败时不清除，可能是网络问题
        authorized.value = false
    }
}

/**
 * 发起飞书授权
 * @param {Function} showToast - Toast 通知函数
 * @returns {Promise<void>}
 */
async function startAuth(showToast) {
    try {
        const { auth_url } = await authStart()

        // 打开新窗口进行飞书用户授权
        const win = window.open(auth_url, '_blank', 'width=720,height=720')
        if (!win) {
            showToast?.('无法打开授权窗口，请检查浏览器弹窗设置', 'error', 3000)
            return
        }

        const handler = async (ev) => {
            if (!ev?.data || ev.data.type !== 'feishu-auth-done' || !ev.data.session_id) {
                return
            }
            sessionId.value = ev.data.session_id
            // 保存到 localStorage
            saveSessionIdToStorage(sessionId.value)
            window.removeEventListener('message', handler)

            // 查询授权状态（带重试机制，因为可能存在时序问题）
            let retryCount = 0
            const maxRetries = 3
            const checkAuthStatus = async () => {
                try {
                    const st = await authStatus(sessionId.value)
                    authorized.value = !!st.authorized
                    if (authorized.value) {
                        showToast?.('已授权，可将文件上传到个人空间', 'success')
                    } else {
                        // 如果未授权且还有重试次数，延迟后重试
                        if (retryCount < maxRetries - 1) {
                            retryCount++
                            setTimeout(checkAuthStatus, 500)
                        } else {
                            showToast?.('授权状态异常，请重新授权', 'warning')
                        }
                    }
                } catch (e) {
                    // 如果还有重试次数，延迟后重试
                    if (retryCount < maxRetries - 1) {
                        retryCount++
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
        showToast?.('打开授权页失败：' + (e?.message || e), 'error')
    }
}

/**
 * 重置授权状态
 */
function resetAuth() {
    sessionId.value = ''
    authorized.value = false
    saveSessionIdToStorage('')
}

/**
 * 初始化授权状态（从 localStorage 恢复）
 */
function initAuth() {
    loadSessionIdFromStorage()
}

export function useAuth() {
    // 首次调用时自动加载保存的 sessionId
    if (!initialized) {
        initAuth()
        initialized = true
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
