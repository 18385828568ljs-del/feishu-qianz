<!--
  文件上传组件
  用于普通附件字段的文件上传
-->
<script setup>
import { ref, defineProps, defineEmits } from 'vue'

const props = defineProps({
  accept: {
    type: String,
    default: 'image/*,.pdf,.doc,.docx,.xls,.xlsx'
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['select'])

const selectedFile = ref(null)
const previewUrl = ref('')
const fileInputRef = ref(null)

function handleClick() {
  if (!props.disabled) {
    fileInputRef.value?.click()
  }
}

function handleFileChange(event) {
  const file = event.target.files?.[0]
  if (file) {
    selectedFile.value = file
    
    // 如果是图片，生成预览
    if (file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = (e) => {
        previewUrl.value = e.target.result
      }
      reader.readAsDataURL(file)
    } else {
      previewUrl.value = ''
    }
    
    emit('select', file)
  }
}

function clearFile() {
  selectedFile.value = null
  previewUrl.value = ''
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
  emit('select', null)
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<template>
  <div class="file-upload" :class="{ disabled }">
    <input 
      ref="fileInputRef"
      type="file" 
      :accept="accept"
      @change="handleFileChange"
      class="file-input"
    />
    
    <!-- 未选择文件时 -->
    <div v-if="!selectedFile" class="upload-area" @click="handleClick">
      <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="17 8 12 3 7 8"/>
        <line x1="12" y1="3" x2="12" y2="15"/>
      </svg>
      <p class="upload-text">点击选择文件</p>
      <p class="upload-hint">支持图片、PDF、Word、Excel</p>
    </div>
    
    <!-- 已选择文件时 -->
    <div v-else class="file-preview">
      <!-- 图片预览 -->
      <div v-if="previewUrl" class="image-preview">
        <img :src="previewUrl" alt="预览" />
      </div>
      
      <!-- 非图片文件 -->
      <div v-else class="file-info-box">
        <svg class="file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
      </div>
      
      <div class="file-details">
        <p class="file-name">{{ selectedFile.name }}</p>
        <p class="file-size">{{ formatFileSize(selectedFile.size) }}</p>
      </div>
      
      <button class="clear-btn" @click.stop="clearFile">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 6 6 18M6 6l12 12"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.file-upload {
  width: 100%;
}

.file-upload.disabled {
  opacity: 0.5;
  pointer-events: none;
}

.file-input {
  display: none;
}

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  border: 2px dashed #d1d1d6;
  border-radius: 12px;
  background: #fafafa;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-area:hover {
  border-color: #007aff;
  background: #f0f7ff;
}

.upload-icon {
  width: 48px;
  height: 48px;
  color: #86868b;
  margin-bottom: 12px;
}

.upload-text {
  font-size: 15px;
  font-weight: 500;
  color: #1d1d1f;
  margin: 0 0 4px;
}

.upload-hint {
  font-size: 12px;
  color: #86868b;
  margin: 0;
}

.file-preview {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border: 2px solid #e5e5ea;
  border-radius: 12px;
  background: #fff;
}

.image-preview {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
}

.image-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.file-info-box {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  background: #f5f5f7;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.file-icon {
  width: 32px;
  height: 32px;
  color: #86868b;
}

.file-details {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
  margin: 0 0 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: 12px;
  color: #86868b;
  margin: 0;
}

.clear-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: #f5f5f7;
  border-radius: 50%;
  color: #86868b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s;
}

.clear-btn svg {
  width: 16px;
  height: 16px;
}

.clear-btn:hover {
  background: #ff3b30;
  color: #fff;
}
</style>
