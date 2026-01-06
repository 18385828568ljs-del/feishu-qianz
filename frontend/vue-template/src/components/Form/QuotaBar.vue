<!--
  额度显示栏组件
  显示 VIP 状态或剩余额度
-->
<script setup>
import { defineProps } from 'vue'

defineProps({
  quota: {
    type: Object,
    required: true,
    default: () => ({
      remaining: 0,
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
    
    <!-- 普通额度 -->
    <div class="quota-info" v-else>
      <span class="quota-label">剩余额度</span>
      <span class="quota-count">{{ quota.remaining }}</span>
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

.quota-label {
  font-size: 12px;
  color: #86868b;
}

.quota-count {
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
  margin-left: auto;
}
</style>
