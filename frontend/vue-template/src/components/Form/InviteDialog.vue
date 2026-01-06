<!--
  邀请码兑换弹窗组件
-->
<script setup>
import { ref, defineProps, defineEmits } from 'vue'
import { ElDialog, ElInput, ElButton } from 'element-plus'
import { redeemInvite } from '@/services/api'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  userInfo: {
    type: Object,
    default: () => ({ openId: '', tenantKey: '' })
  }
})

const emit = defineEmits(['update:modelValue', 'close', 'success'])

const inviteCode = ref('')

async function handleRedeem() {
  if (!inviteCode.value.trim()) {
    emit('toast', { message: '请输入邀请码', type: 'warning' })
    return
  }
  try {
    const result = await redeemInvite(
      inviteCode.value.trim(), 
      props.userInfo.openId, 
      props.userInfo.tenantKey
    )
    if (result.success) {
      emit('toast', { message: `邀请码兑换成功！${result.benefit_days}天内可免费使用`, type: 'success' })
      emit('update:modelValue', false)
      emit('success')
      inviteCode.value = ''
    }
  } catch (e) {
    emit('toast', { message: '邀请码无效或已被使用', type: 'error' })
  }
}

function handleClose() {
  emit('update:modelValue', false)
  emit('close')
}
</script>

<template>
  <el-dialog 
    :model-value="modelValue" 
    @update:model-value="$emit('update:modelValue', $event)"
    width="92%" 
    center 
    :show-close="false" 
    @close="handleClose"
  >
    <template #header>
      <div class="dialog-header">
        <div class="dialog-icon invite-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 12v10H4V12"/><path d="M2 7h20v5H2z"/><path d="M12 22V7"/><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"/><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/>
          </svg>
        </div>
        <div class="dialog-title-text">兑换邀请码</div>
        <button class="close-btn" @click="handleClose">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12"/></svg>
        </button>
      </div>
    </template>
    
    <div class="dialog-content">
      <p class="dialog-subtitle">输入邀请码，解锁限时免费签名</p>
      <el-input v-model="inviteCode" placeholder="请输入邀请码" size="large" class="styled-input" />
      <el-button type="primary" @click="handleRedeem" size="large" class="main-btn">
        立即兑换
      </el-button>
    </div>
  </el-dialog>
</template>

<style scoped>
/* 弹窗头部 */
.dialog-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f5;
  position: relative;
}

.dialog-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dialog-icon svg {
  width: 24px;
  height: 24px;
}

.invite-icon {
  background: #f5f5f7;
  color: #ff9500;
}

.dialog-title-text {
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
}

.close-btn {
  position: absolute;
  right: 0;
  top: 0;
  width: 28px;
  height: 28px;
  border: none;
  background: #f5f5f7;
  border-radius: 50%;
  color: #86868b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  padding: 0;
}

.close-btn svg {
  width: 14px;
  height: 14px;
}

.close-btn:hover {
  background: #e5e5e7;
  color: #1d1d1f;
}

/* 弹窗内容 */
.dialog-content {
  padding-top: 8px;
}

.dialog-subtitle {
  font-size: 14px;
  color: #86868b;
  text-align: center;
  margin-bottom: 10px;
}

.styled-input {
  margin-bottom: 10px;
}

.styled-input :deep(.el-input__wrapper) {
  padding: 8px 16px;
  border-radius: 12px;
  box-shadow: none !important;
  border: 2px solid #e5e5ea;
  background: #fafafa;
  transition: all 0.2s;
}

.styled-input :deep(.el-input__wrapper:hover) {
  box-shadow: none !important;
  border-color: #c7c7cc;
  background: #fff;
}

.styled-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 4px rgba(0, 122, 255, 0.1) !important;
  border-color: #007aff;
  background: #fff;
}

.styled-input :deep(.el-input__inner) {
  font-size: 16px;
  height: 28px;
  color: #1d1d1f;
  border: none !important;
  outline: none !important;
  background: transparent;
}

.main-btn {
  width: 100%;
  height: 48px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
}
</style>
