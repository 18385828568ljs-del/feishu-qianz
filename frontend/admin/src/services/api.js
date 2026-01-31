import axios from 'axios'

const api = axios.create({
    baseURL: import.meta.env.VITE_API_BASE || '',  // 空字符串，让请求走 Vite 代理
    timeout: 20000,
})

function getAdminUsername() {
    return localStorage.getItem('admin_username') || ''
}

function getAdminToken() {
    return localStorage.getItem('admin_token') || ''
}

// 添加请求拦截器
api.interceptors.request.use(
    (config) => {
        const username = getAdminUsername()
        const token = getAdminToken()

        // 新认证：账号 + 密码
        if (username) {
            config.headers['X-Admin-Username'] = username
        }
        config.headers['X-Admin-Token'] = token

        return config
    },
    (error) => Promise.reject(error)
)

// ==================== 仪表盘 ====================

export async function getDashboard() {
    const { data } = await api.get('/admin/dashboard')
    return data
}

export async function getTrends(period = 'week') {
    const { data } = await api.get('/admin/dashboard/trends', {
        params: { period }
    })
    return data
}

// ==================== 用户管理 ====================

export async function getUsers(page = 1, pageSize = 20, search = '') {
    const { data } = await api.get('/admin/users', {
        params: { page, page_size: pageSize, search: search || undefined }
    })
    return data
}

export async function updateUserQuota(userId, remainingQuota) {
    const { data } = await api.put(`/admin/users/${userId}/quota`, { remaining_quota: remainingQuota })
    return data
}


export async function resetUser(userId) {
    const { data } = await api.post(`/admin/users/${userId}/reset`)
    return data
}

export async function deleteUser(userId) {
    const { data } = await api.delete(`/admin/users/${userId}`)
    return data
}

export function getUserExportUrl() {
    const token = getAdminToken()
    const baseUrl = import.meta.env.VITE_API_BASE || ''
    return `${baseUrl}/admin/users/export?token=${token}`
}

// ==================== 表单管理 ====================

export async function getForms(page = 1, pageSize = 20, search = '') {
    const { data } = await api.get('/admin/forms', {
        params: { page, page_size: pageSize, search: search || undefined }
    })
    return data
}

export async function updateFormStatus(formId, isActive) {
    const { data } = await api.put(`/admin/forms/${formId}/status`, null, {
        params: { is_active: isActive }
    })
    return data
}

export async function deleteForm(formId) {
    const { data } = await api.delete(`/admin/forms/${formId}`)
    return data
}

// ==================== 邀请码管理 ====================

export async function getInvites(page = 1, pageSize = 20) {
    const { data } = await api.get('/admin/invites', {
        params: { page, page_size: pageSize }
    })
    return data
}

export async function createInvite(maxUsage = 10, benefitDays = 365, expiresInDays = 30) {
    const { data } = await api.post('/admin/invites', {
        max_usage: maxUsage,
        benefit_days: benefitDays,
        expires_in_days: expiresInDays
    })
    return data
}

export async function updateInviteStatus(inviteId, isActive, revokeBenefits = false) {
    const { data } = await api.put(`/admin/invites/${inviteId}/status`, null, {
        params: { is_active: isActive, revoke_benefits: revokeBenefits }
    })
    return data
}

export async function deleteInvite(inviteId) {
    const { data } = await api.delete(`/admin/invites/${inviteId}`)
    return data
}

export function getInviteExportUrl() {
    const token = getAdminToken()
    const baseUrl = import.meta.env.VITE_API_BASE || ''
    return `${baseUrl}/admin/invites/export?token=${token}`
}

// ==================== 签名日志 ====================

export async function getLogs(page = 1, pageSize = 20, userKey = '', startDate = '', endDate = '') {
    const { data } = await api.get('/admin/logs', {
        params: {
            page,
            page_size: pageSize,
            user_key: userKey || undefined,
            start_date: startDate || undefined,
            end_date: endDate || undefined
        }
    })
    return data
}

export async function deleteLog(logId) {
    const { data } = await api.delete(`/admin/logs/${logId}`)
    return data
}

export async function clearLogs() {
    const { data } = await api.delete('/admin/logs/clear')
    return data
}

export function getLogExportUrl(userKey = '', startDate = '', endDate = '') {
    const token = getAdminToken()
    const baseUrl = import.meta.env.VITE_API_BASE || ''
    let url = `${baseUrl}/admin/logs/export?token=${token}`
    if (userKey) url += `&user_key=${encodeURIComponent(userKey)}`
    if (startDate) url += `&start_date=${encodeURIComponent(startDate)}`
    if (endDate) url += `&end_date=${encodeURIComponent(endDate)}`
    return url
}

// ==================== 订单管理 ====================

export async function getOrders(page = 1, pageSize = 20, status = '') {
    const { data } = await api.get('/admin/orders', {
        params: { page, page_size: pageSize, status: status || undefined }
    })
    return data
}

// ==================== 认证 ====================

export function setAdminCredentials(username, token) {
    localStorage.setItem('admin_username', username)
    localStorage.setItem('admin_token', token)
}

// 兼容旧代码：旧版只保存 token（密码）
export function setAdminToken(token) {
    localStorage.setItem('admin_token', token)
}

export function isLoggedIn() {
    return !!getAdminToken()
}

export function logout() {
    localStorage.removeItem('admin_username')
    localStorage.removeItem('admin_token')
}

// 修改密码
export async function changePassword(oldPassword, newPassword) {
    const { data } = await api.put('/admin/password', {
        old_password: oldPassword,
        new_password: newPassword
    })
    return data
}

// ==================== 套餐管理 ====================

export async function getPricing(includeInactive = false) {
    const { data } = await api.get('/admin/pricing', {
        params: { include_inactive: includeInactive }
    })
    return data
}

export async function createPricing(planData) {
    const { data } = await api.post('/admin/pricing', planData)
    return data
}

export async function updatePricing(planId, planData) {
    const { data } = await api.put(`/admin/pricing/${planId}`, planData)
    return data
}

export async function deletePricing(planId) {
    const { data } = await api.delete(`/admin/pricing/${planId}`)
    return data
}
