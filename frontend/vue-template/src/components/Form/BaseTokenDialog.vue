<!--
  授权码配置弹窗组件
  用于让用户配置飞书授权码 (PersonalBaseToken)
  UI 风格统一化重构
-->
<script setup>
import { defineProps, defineEmits, ref, computed, watch } from 'vue'
import { ElDialog, ElInput, ElButton } from 'element-plus'
import { useBaseToken } from '@/composables/useBaseToken'

// Props & Emits
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'close', 'saved'])

// Composables
const { baseToken, setBaseToken, hasBaseToken } = useBaseToken()

// State
const inputToken = ref(baseToken.value)

// Watchers
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    inputToken.value = baseToken.value
  }
})

// Actions
function handleSave() {
  const token = inputToken.value.trim()
  setBaseToken(token)
  emit('saved', token)
  emit('update:modelValue', false)
}

function handleClose() {
  emit('update:modelValue', false)
  emit('close')
}

function handleClear() {
  inputToken.value = ''
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
    class="base-token-dialog"
  >
    <template #header>
      <div class="dialog-header">
        <!-- 移除 header-icon-wrapper -->
        <div class="dialog-title-text center">配置授权码</div>
        <button class="close-btn" @click="handleClose">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12"/></svg>
        </button>
      </div>
    </template>
    
    <div class="dialog-content">
      <!-- 获取授权码指引 -->

      <!-- 输入区域 -->
      <div class="input-section">
        <div class="help-link-wrapper">
          <p class="input-hint">为了保护数据安全，请配置您的授权码：</p>
          <a 
            class="info-link" 
            href="https://dcnpj27i4okj.feishu.cn/docx/BP8kdlxCeoLtyQxlVBacg51Ynpe" 
            target="_blank"
          >
            如何获取授权码？查看详细教程
          </a>
        </div>
        <el-input 
          v-model="inputToken" 
          type="password"
          placeholder="请输入 PersonalBaseToken" 
          size="large" 
          class="styled-input" 
          show-password
        />
      </div>

      <!-- 状态提示 -->
      <div v-if="hasBaseToken" class="status-tip success">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6 9 17l-5-5"/></svg>
        <span>当前已配置授权码</span>
      </div>
      <div v-else class="status-tip warning">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4m0 4h.01"/></svg>
        <span>未配置，无法上传签名</span>
      </div>

      <!-- 按钮 -->
      <el-button type="primary" @click="handleSave" size="large" class="main-btn">
        保存配置
      </el-button>
    </div>
  </el-dialog>
</template>

<style scoped>
/* 头部样式统一 */
.dialog-header {
  display: flex;
  align-items: center;
  justify-content: center; /* 居中 */
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
  top: 8px;
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

.close-btn:hover {
  background: #e5e5e7;
  color: #1d1d1f;
}

.close-btn svg { width: 14px; height: 14px; }

/* 内容区域 */
.dialog-content {
  padding-top: 16px;
}

.info-card {
  background: #f9f9fa;
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 20px;
}

.info-title {
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 6px;
}

.info-desc {
  font-size: 13px;
  color: #646a73;
  line-height: 1.5;
  margin-bottom: 8px;
}

.styled-input {
  margin-bottom: 24px;
}

.help-link-wrapper {
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.input-hint {
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 4px;
}

.info-link {
  font-size: 13px;
  color: #007aff;
  text-decoration: none;
  font-weight: 500;
  width: fit-content;
  transition: opacity 0.2s;
}

.info-link:hover {
  text-decoration: underline;
  opacity: 0.8;
}


.styled-input :deep(.el-input__wrapper) {
  padding: 8px 16px;
  border-radius: 12px;
  box-shadow: none !important;
  border: 2px solid #e5e5ea;
  background: #fff;
  transition: all 0.2s;
}

.styled-input :deep(.el-input__wrapper:hover) {
  border-color: #c7c7cc;
}

.styled-input :deep(.el-input__wrapper.is-focus) {
  border-color: #007aff;
  box-shadow: 0 0 0 4px rgba(0, 122, 255, 0.1) !important;
}

.styled-input :deep(.el-input__inner) {
  font-size: 16px;
  height: 32px;
  color: #1d1d1f;
}

/* 状态提示 */
.status-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 20px;
}

.status-tip svg { width: 16px; height: 16px; }

.status-tip.success {
  background: #e8f5e9;
  color: #34c759;
}

.status-tip.warning {
  background: #fff3e0;
  color: #ff9500;
}

.main-btn {
  width: 100%;
  height: 48px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
}
</style>
