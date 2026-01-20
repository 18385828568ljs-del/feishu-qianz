<!--
  额度显示栏组件
  显示 VIP 状态、不限次数或剩余额度进度条
-->
<script setup>
import { defineProps, computed } from 'vue'

const props = defineProps({
  quota: {
    type: Object,
    required: true,
    default: () => ({
      remaining: 0,
      planQuota: null,
      isUnlimited: false,
      inviteActive: false,
      inviteExpireAt: null
    })
  }
})

// 格式化日期
function formatDate(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp * 1000)
  return date.toLocaleDateString('zh-CN')
}

// 计算进度百分比
const progressPercent = computed(() => {
  if (props.quota.isUnlimited || props.quota.inviteActive) return 100
  const total = props.quota.planQuota || 10  // 默认免费试用额度
  const remaining = props.quota.remaining || 0
  return Math.min(100, Math.max(0, (remaining / total) * 100))
})

// 进度条颜色：根据剩余百分比变化
const progressColor = computed(() => {
  const percent = progressPercent.value
  if (percent > 50) return '#34c759'       // 绿色：充足
  if (percent > 20) return '#ff9500'       // 橙色：偏低
  return '#ff3b30'                          // 红色：即将用尽
})
</script>

<template>
  <div class="quota-bar">
    <!-- VIP 状态 -->
    <div class="quota-info" v-if="quota.inviteActive">
      <svg class="vip-icon" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2L9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61z"/>
      </svg>
      <span class="vip-text">VIP · {{ formatDate(quota.inviteExpireAt) }} 到期</span>
    </div>
    
    <!-- 不限次数 -->
    <div class="quota-info unlimited" v-else-if="quota.isUnlimited">
      <div class="unlimited-row">
        <svg class="unlimited-icon" viewBox="0 0 24 24" fill="currentColor">
          <path d="M18.6 6.62c-1.44 0-2.8.56-3.77 1.53L12 10.66 10.48 12h.01L7.8 14.39c-.64.64-1.49.99-2.4.99-1.87 0-3.39-1.51-3.39-3.38S3.53 8.62 5.4 8.62c.91 0 1.76.35 2.44 1.03l1.13 1 1.51-1.34L9.22 8.2C8.2 7.18 6.84 6.62 5.4 6.62 2.42 6.62 0 9.04 0 12s2.42 5.38 5.4 5.38c1.44 0 2.8-.56 3.77-1.53l2.83-2.5.01.01L13.52 12h-.01l2.69-2.39c.64-.64 1.49-.99 2.4-.99 1.87 0 3.39 1.51 3.39 3.38s-1.52 3.38-3.39 3.38c-.9 0-1.76-.35-2.44-1.03l-1.14-1.01-1.51 1.34 1.27 1.12c1.02 1.01 2.37 1.57 3.82 1.57 2.98 0 5.4-2.41 5.4-5.38s-2.42-5.37-5.4-5.37z"/>
        </svg>
        <span class="unlimited-text">无限次数</span>
        <span v-if="quota.planExpiresAt" class="expire-text">· {{ formatDate(quota.planExpiresAt) }} 到期</span>
      </div>
    </div>
    
    <!-- 普通额度进度条 -->
    <div class="quota-progress-wrapper" v-else>
      <div class="quota-header">
        <span class="quota-label">剩余额度</span>
        <span v-if="quota.planExpiresAt" class="expire-center">{{ formatDate(quota.planExpiresAt) }} 到期</span>
        <span class="quota-count">{{ quota.remaining }} / {{ quota.planQuota || 10 }}</span>
      </div>
      <div class="quota-progress-bar">
        <div 
          class="quota-progress-fill" 
          :style="{ width: progressPercent + '%', backgroundColor: progressColor }"
        ></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.quota-bar {
  margin-top: 12px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}

.quota-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.vip-icon {
  width: 16px;
  height: 16px;
  color: #ff9500;
}

.vip-text {
  font-size: 13px;
  font-weight: 500;
  color: #ff9500;
}

.unlimited-icon {
  width: 18px;
  height: 18px;
  color: #007aff;
}

.unlimited-text {
  font-size: 13px;
  font-weight: 500;
  color: #007aff;
}

/* 进度条样式 */
.quota-progress-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.quota-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
}

.quota-label {
  font-size: 12px;
  color: #86868b;
}

.quota-count {
  font-size: 13px;
  font-weight: 600;
  color: #1d1d1f;
}

.quota-progress-bar {
  height: 6px;
  background: #e5e5e5;
  border-radius: 3px;
  overflow: hidden;
}

.quota-progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease, background-color 0.3s ease;
}

/* 到期时间样式（居中） */
.expire-center {
  font-size: 12px;
  color: #86868b;
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.unlimited-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.expire-text {
  font-size: 12px;
  color: #86868b;
  font-weight: 400;
}
</style>
