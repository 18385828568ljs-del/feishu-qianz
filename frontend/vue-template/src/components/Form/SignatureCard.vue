<!--
  附件区域卡片组件
  支持两种模式：签名模式（显示签字板）和上传模式（显示文件选择器）
-->
<script setup>
import { computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import SignaturePad from '../SignaturePad.vue'
import FileUpload from './FileUpload.vue'

const props = defineProps({
  hasSelection: {
    type: Boolean,
    default: false
  },
  hasAttachField: {
    type: Boolean,
    default: false
  },
  mode: {
    type: String,
    default: 'signature'
  },
  fieldName: {
    type: String,
    default: '签名区域'
  },
  userId: {
    type: String,
    default: ''
  }
})

// 调试：监听 userId 变化
watch(() => props.userId, (newVal) => {
  console.log('[SignatureCard] userId changed:', newVal)
}, { immediate: true })

const emit = defineEmits(['confirm', 'fileSelect', 'batchConfirm'])

// 是否为签名模式
const isSignatureMode = computed(() => props.mode === 'signature')

// 标题
const title = computed(() => {
  return isSignatureMode.value ? '签名区域' : props.fieldName || '附件上传'
})

// 图标路径
const iconPath = computed(() => {
  return isSignatureMode.value 
    ? 'M17 3a2.85 2.85 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z'
    : 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12'
})

// 格式化用户ID显示（前6位 + ***）
const formattedUserId = computed(() => {
  if (!props.userId) return ''
  if (props.userId.length <= 8) return props.userId
  return props.userId.substring(0, 6) + '***'
})

// 复制用户ID到剪贴板
const copyUserId = (event) => {
  event.stopPropagation()
  
  if (!props.userId) {
    console.warn('[SignatureCard] No userId to copy')
    return
  }
  
  console.log('[SignatureCard] Attempting to copy:', props.userId)
  
  // 直接使用 execCommand（飞书环境禁用了 Clipboard API）
  const textarea = document.createElement('textarea')
  textarea.value = props.userId
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  textarea.style.top = '0'
  textarea.setAttribute('readonly', '')
  document.body.appendChild(textarea)
  
  // iOS 兼容
  if (navigator.userAgent.match(/ipad|iphone/i)) {
    const range = document.createRange()
    range.selectNodeContents(textarea)
    const selection = window.getSelection()
    selection.removeAllRanges()
    selection.addRange(range)
    textarea.setSelectionRange(0, 999999)
  } else {
    textarea.select()
  }
  
  try {
    const successful = document.execCommand('copy')
    document.body.removeChild(textarea)
    
    if (successful) {
      console.log('[SignatureCard] Copy successful')
      showCopySuccess()
    } else {
      console.error('[SignatureCard] Copy failed')
      showManualCopyDialog()
    }
  } catch (err) {
    console.error('[SignatureCard] Copy error:', err)
    document.body.removeChild(textarea)
    showManualCopyDialog()
  }
}

// 显示手动复制对话框
const showManualCopyDialog = () => {
  ElMessage({
    message: `用户ID: ${props.userId}`,
    type: 'info',
    duration: 0,
    showClose: true,
    dangerouslyUseHTMLString: true,
    customClass: 'copy-fallback-message'
  })
}

// 显示复制成功提示
const showCopySuccess = () => {
  console.log('[SignatureCard] User ID copied:', props.userId)
  ElMessage.success({
    message: '已复制用户ID',
    duration: 1500,
    showClose: false
  })
}

function handleConfirm(blob) {
  emit('confirm', blob)
}

function handleBatchConfirm(blob) {
  emit('batchConfirm', blob)
}

function handleFileSelect(file) {
  emit('fileSelect', file)
}

import { ArrowDown, Plus, User } from '@element-plus/icons-vue'
</script>

<template>
  <div class="main-card" :class="{ 'disabled-card': !hasSelection || !hasAttachField }">
    <!-- 卡片头部 -->
    <div class="card-header">
      <div class="header-left">
        <svg class="header-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path :d="iconPath"/>
        </svg>
        <span class="header-title">{{ title }}</span>
      </div>
      
      <!-- 用户ID显示 -->
      <div v-if="userId" class="user-id-badge">
        <svg class="user-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
          <circle cx="12" cy="7" r="4"/>
        </svg>
        <span class="user-id-text" ref="userIdText" :title="`完整ID: ${userId}`">{{ formattedUserId }}</span>
        <button 
          class="copy-btn" 
          @click="copyUserId"
          :title="`点击复制完整ID`"
          type="button"
        >
          <svg class="copy-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
        </button>
      </div>
    </div>
    
    <!-- 内容区域 -->
    <div class="content-area">
      <!-- 签名模式 -->
      <div v-if="isSignatureMode" class="canvas-area">
        <SignaturePad @confirm="handleConfirm" @batchConfirm="handleBatchConfirm" />
      </div>
      
      <!-- 上传模式 -->
      <div v-else class="upload-area-wrapper">
        <FileUpload 
          :disabled="!hasSelection || !hasAttachField"
          @select="handleFileSelect"
        />
      </div>
    </div>
    
    <!-- 未选中遮罩 (仅在未选中行时显示) -->
    <div class="overlay" v-if="!hasSelection && hasAttachField">
      <div class="overlay-box">
        <svg class="overlay-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <path d="M9 9h.01M15 9h.01M9 15h6"/>
        </svg>
        <p class="overlay-text">请先选中表格中的一行</p>
      </div>
    </div>
    
    <!-- 警告栏 -->
    <div class="warning-bar" v-if="!hasAttachField">
      <svg class="warning-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/><path d="M12 8v4m0 4h.01"/>
      </svg>
      <span>未检测到附件字段，请添加附件类型的列</span>
    </div>
  </div>
</template>

<style scoped>
.main-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  position: relative;
  overflow: hidden;
}

.card-header {
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f0f0f0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-icon {
  width: 18px;
  height: 18px;
  color: #6e6e73;
}

.header-title {
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
}

/* 用户ID徽章 */
.user-id-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px 4px 10px;
  border-radius: 6px;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  transition: all 0.2s;
}

.user-id-badge:hover {
  background: #ecf0f5;
  border-color: #d3dae6;
}

.user-icon {
  width: 14px;
  height: 14px;
  color: #606266;
  flex-shrink: 0;
}

.user-id-text {
  font-size: 11px;
  color: #606266;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  letter-spacing: 0.5px;
}

.copy-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px;
  background: transparent;
  border: none;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
  color: #909399;
}

.copy-btn:hover {
  background: #dcdfe6;
  color: #606266;
}

.copy-btn:active {
  transform: scale(0.95);
}

.copy-icon {
  width: 12px;
  height: 12px;
}

.status-chip {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  background: #f5f5f7;
  color: #86868b;
}

.status-chip.status-ready {
  background: #e8f5e9;
  color: #2e7d32;
}

.content-area {
  min-height: 200px;
}

.canvas-area {
  background: #fafafa;
}

.upload-area-wrapper {
  padding: 16px;
}

/* 遮罩 */
.disabled-card .content-area {
  filter: brightness(0.97);
  pointer-events: none;
}

.overlay {
  position: absolute;
  top: 47px;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255,255,255,0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  pointer-events: all;
  cursor: not-allowed;
}

.overlay-box {
  text-align: center;
}

.overlay-icon {
  width: 48px;
  height: 48px;
  color: #c7c7cc;
  margin-bottom: 12px;
}

.overlay-text {
  font-size: 13px;
  color: #86868b;
}

/* 警告栏 */
.warning-bar {
  margin: 12px;
  padding: 10px 12px;
  background: #fff8e1;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #f57c00;
}

.warning-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}
</style>
