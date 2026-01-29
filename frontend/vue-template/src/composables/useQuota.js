/**
 * 配额管理组合式函数
 * 封装用户配额加载和状态管理
 */
import { ref, computed } from 'vue'
import { getQuota } from '@/services/api'

// 响应式状态
const quota = ref({
    remaining: 20,
    planQuota: null,       // 套餐总配额（用于进度条）
    isUnlimited: false,    // 是否不限次数
    totalUsed: 0,
    inviteActive: false,
    inviteExpireAt: null,
    planExpiresAt: null,   // 套餐到期时间
})

// 计算属性：是否可以签名
const canSign = computed(() => {
    return quota.value.inviteActive || quota.value.isUnlimited || quota.value.remaining > 0
})

/**
 * 加载配额信息
 * @param {string} openId - 用户 openId
 * @param {string} tenantKey - 租户 key
 */
async function loadQuota(openId, tenantKey) {
    try {
        const data = await getQuota(openId, tenantKey)
        quota.value = {
            remaining: data.remaining || 0,
            planQuota: data.plan_quota || 100,  // 默认免费试用 100 次
            isUnlimited: data.is_unlimited || false,
            totalUsed: data.total_used || 0,
            inviteActive: data.invite_active || false,
            inviteExpireAt: data.invite_expire_at || null,
            planExpiresAt: data.plan_expires_at || null,  // 套餐到期时间
        }
    } catch (e) {
        console.warn('[Quota] Failed to load quota:', e)
    }
}

/**
 * 格式化日期
 * @param {number} timestamp - Unix 时间戳（秒）
 * @returns {string}
 */
function formatDate(timestamp) {
    if (!timestamp) return ''
    const date = new Date(timestamp * 1000)
    return date.toLocaleDateString('zh-CN')
}

export function useQuota() {
    return {
        quota,
        canSign,
        loadQuota,
        formatDate
    }
}
