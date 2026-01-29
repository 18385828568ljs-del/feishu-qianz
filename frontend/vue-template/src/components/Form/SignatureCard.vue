<!--
  附件区域卡片组件
  支持两种模式：签名模式（显示签字板）和上传模式（显示文件选择器）
-->
<script setup>
import { computed } from 'vue'
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
    default: 'signature', // 'signature' | 'upload'
    validator: (value) => ['signature', 'upload'].includes(value)
  },
  fieldName: {
    type: String,
    default: '签名区域'
  }
})

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

function handleConfirm(blob) {
  emit('confirm', blob)
}

function handleBatchConfirm(blob) {
  emit('batchConfirm', blob)
}

function handleFileSelect(file) {
  emit('fileSelect', file)
}
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
      <span class="status-chip" :class="{ 'status-ready': hasSelection && hasAttachField }">
        {{ (hasSelection && hasAttachField) ? '就绪' : (!hasAttachField ? '不可用' : '未选中') }}
      </span>
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
