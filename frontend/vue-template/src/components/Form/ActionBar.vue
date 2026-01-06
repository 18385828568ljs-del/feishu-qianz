<!--
  操作按钮栏组件
  包含：兑换码、授权、充值、分享 四个操作按钮
-->
<script setup>
import { defineProps, defineEmits } from 'vue'

defineProps({
  authorized: {
    type: Boolean,
    default: false
  },
  activeButton: {
    type: String,
    default: ''
  },
  showRechargeButton: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['invite', 'auth', 'recharge', 'share', 'update:activeButton'])

function handleInvite() {
  emit('update:activeButton', 'invite')
  emit('invite')
}

function handleAuth() {
  emit('update:activeButton', 'auth')
  emit('auth')
}

function handleRecharge() {
  emit('update:activeButton', 'recharge')
  emit('recharge')
}

function handleShare() {
  emit('update:activeButton', 'share')
  emit('share')
}
</script>

<template>
  <div class="actions-row">
    <!-- 兑换码按钮 -->
    <button 
      class="action-btn" 
      :class="{ active: activeButton === 'invite' }" 
      @click="handleInvite"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-6"/>
        <path d="M12 12V3m0 0L8 7m4-4 4 4"/>
      </svg>
      <span>兑换码</span>
    </button>
    
    <!-- 授权按钮 -->
    <button 
      class="action-btn" 
      :class="{ active: activeButton === 'auth' }" 
      @click="handleAuth"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M12 2a10 10 0 0 0-6.88 17.23l1.15-2.88A7 7 0 1 1 19 12h-3l4 4 4-4h-3A10 10 0 0 0 12 2Z"/>
      </svg>
      <span>{{ authorized ? '已授权' : '授权' }}</span>
      <span class="dot" :class="{ 'dot-active': authorized }"></span>
    </button>
    
    <!-- 充值按钮 -->
    <button 
      v-if="showRechargeButton"
      class="action-btn" 
      :class="{ active: activeButton === 'recharge' }" 
      @click="handleRecharge"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48 2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48 2.83-2.83"/>
      </svg>
      <span>充值</span>
    </button>
    
    <!-- 分享按钮 -->
    <button 
      class="action-btn" 
      :class="{ active: activeButton === 'share' }" 
      @click="handleShare"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><path d="M16 6l-4-4-4 4"/><path d="M12 2v13"/>
      </svg>
      <span>分享</span>
    </button>
  </div>
</template>

<style scoped>
.actions-row {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 12px;
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  font-size: 13px;
  color: #1d1d1f;
  cursor: pointer;
  transition: all 0.15s;
  position: relative;
}

.action-btn:hover {
  background: #fafafa;
  border-color: #d1d1d6;
}

.action-btn.active {
  background: #007aff;
  border-color: #007aff;
  color: #fff;
}

.action-btn.active:hover {
  background: #0066d6;
}

.action-btn svg {
  width: 16px;
  height: 16px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #c7c7cc;
}

.dot-active {
  background: #34c759;
}
</style>
