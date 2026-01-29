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

// 获取邀请码错误消息
function getInviteErrorMessage(errorCode) {
  const errorMessages = {
    'INVALID_CODE': '邀请码不存在或无效',
    'CODE_EXPIRED': '邀请码已过期',
    'CODE_USED_UP': '邀请码使用次数已用完',
    'ALREADY_USED_INVITE': '您已经使用过邀请码，每个用户只能使用一次'
  }
  return errorMessages[errorCode] || '邀请码无效或已被使用'
}

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
    const errorCode = e.response?.data?.detail || e.message
    const errorMessage = getInviteErrorMessage(errorCode)
    emit('toast', { message: errorMessage, type: 'error' })
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
    width="90%" 
    center 
    align-center
    append-to-body
    :show-close="false" 
    @close="handleClose"
  >
    <template #header>
      <div class="dialog-header-clean">
        <div class="dialog-title-text center">兑换邀请码</div>
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
.dialog-header-clean {
  display: flex;
  align-items: center;
  justify-content: center;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f5;
  position: relative;
}

.dialog-title-text {
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
}

.center {
  text-align: center;
  flex: 1;
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
