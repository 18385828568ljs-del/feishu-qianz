<!--
  Toast 通知组件
  居中显示的 Toast 提示，支持 success/error/warning/info 类型
-->
<script setup>
import { defineProps } from 'vue'

defineProps({
  message: {
    type: String,
    default: ''
  },
  type: {
    type: String,
    default: 'info',
    validator: (value) => ['success', 'error', 'warning', 'info'].includes(value)
  }
})
</script>

<template>
  <Transition name="toast-fade">
    <div v-if="message" class="toast-overlay">
      <div class="toast-card">
        <!-- Success -->
        <svg v-if="type === 'success'" class="toast-icon success" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        <!-- Error -->
        <svg v-else-if="type === 'error'" class="toast-icon error" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
        <!-- Warning - 感叹号三角形 -->
        <svg v-else-if="type === 'warning'" class="toast-icon warning" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
          <line x1="12" y1="9" x2="12" y2="13"></line>
          <circle cx="12" cy="17" r="0.5" fill="currentColor"></circle>
        </svg>
        <!-- Info -->
        <svg v-else class="toast-icon info" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="16" x2="12" y2="12"></line>
          <line x1="12" y1="8" x2="12.01" y2="8"></line>
        </svg>
        <p>{{ message }}</p>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
/* Toast 遮罩层 */
.toast-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  pointer-events: none;
}

/* Toast 卡片 */
.toast-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px 32px;
  background: rgba(0, 0, 0, 0.85);
  border-radius: 16px;
  color: #fff;
  text-align: center;
  max-width: 280px;
  backdrop-filter: blur(10px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.toast-card p {
  margin: 0;
  font-size: 15px;
  font-weight: 500;
  line-height: 1.4;
}

/* Toast 图标 */
.toast-icon {
  width: 44px;
  height: 44px;
  stroke-width: 2.5;
}

.toast-icon.success {
  color: #34c759;
}

.toast-icon.error {
  color: #ff3b30;
}

.toast-icon.warning {
  color: #ff9500;
}

.toast-icon.info {
  color: #007aff;
}

/* 动画 */
.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: scale(0.9);
}
</style>
