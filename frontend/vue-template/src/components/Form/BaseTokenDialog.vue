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
  },
  appToken: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'close', 'saved'])

// Composables
const { currentBaseToken, setBaseToken, hasBaseToken, getBaseToken, setCurrentAppToken: setCurrentAppTokenInComposable } = useBaseToken()

// State
const inputToken = ref('')

// 计算当前是否已配置（基于 appToken）
const isConfigured = computed(() => {
  if (!props.appToken) return false
  return !!getBaseToken(props.appToken)
})

// Watchers
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    // 当弹窗打开时，加载当前表格的授权码
    inputToken.value = props.appToken ? getBaseToken(props.appToken) : currentBaseToken.value
  }
})

// Actions
function handleSave() {
  const token = inputToken.value.trim()
  if (!props.appToken) {
    console.warn('[BaseTokenDialog] No appToken provided')
    return
  }
  
  console.log('[BaseTokenDialog] Saving token for appToken:', props.appToken)
  setBaseToken(props.appToken, token)
  
  // 保存后立即设置为当前表格
  setCurrentAppTokenInComposable(props.appToken)
  
  console.log('[BaseTokenDialog] Token saved and currentAppToken set')
  
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
          <p class="info-desc">授权码是针对每个多维表格的，切换表格后需要重新配置</p>
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
      <div v-if="!isConfigured" class="status-tip warning">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4m0-4h.01"/></svg>
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
  gap: 6px;
}

.input-hint {
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0;
}

.info-desc {
  font-size: 13px;
  color: #646a73;
  line-height: 1.5;
  margin: 0;
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
