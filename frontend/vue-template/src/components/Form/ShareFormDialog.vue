<!--
  分享表单弹窗组件
  包含表单基本信息输入和字段选择
-->
<script setup>
import { defineProps, defineEmits, watch } from 'vue'
import { ElDialog, ElInput, ElButton } from 'element-plus'
import { useShareForm } from '@/composables/useShareForm'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  appToken: {
    type: String,
    default: ''
  },
  tableId: {
    type: String,
    default: ''
  },
  sessionId: {
    type: String,
    default: ''
  },
  userKey: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'close', 'success', 'toast'])

const {
  shareFormName,
  shareFormDesc,
  generatedShareUrl,
  availableFields,
  selectedFields,
  loadingFields,
  showFieldSelector,
  loadTableFields,
  toggleFieldSelection,
  isFieldSelected,
  toggleRequired,
  goToFieldSelector,
  goBackToBasicInfo,
  handleCreateShareForm,
  copyShareUrl,
  getFieldTypeName,
  resetShareForm
} = useShareForm()

// 显示 Toast
function showToast(message, type) {
  emit('toast', { message, type })
}

// 加载字段
async function loadFields() {
  await loadTableFields(props.appToken, props.tableId, props.sessionId, showToast)
}

// 进入字段选择
function handleGoToFieldSelector() {
  goToFieldSelector(showToast)
}

// 创建表单
async function handleCreate() {
  const success = await handleCreateShareForm({
    tableId: props.tableId,
    userKey: props.userKey,
    sessionId: props.sessionId
  }, showToast)
  
  if (success) {
    emit('success')
  }
}

// 复制链接
function handleCopyUrl() {
  copyShareUrl(showToast)
}

// 关闭弹窗
function handleClose() {
  emit('update:modelValue', false)
  emit('close')
  // 延迟重置，避免动画问题
  setTimeout(() => {
    resetShareForm()
  }, 300)
}

// 监听弹窗打开
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    resetShareForm()
    loadFields()
  }
})
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
        <div class="dialog-icon share-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><path d="M16 6l-4-4-4 4"/><path d="M12 2v13"/>
          </svg>
        </div>
        <div class="dialog-title-text">{{ showFieldSelector ? '选择表单字段' : '创建分享表单' }}</div>
        <button class="close-btn" @click="handleClose">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12"/></svg>
        </button>
      </div>
    </template>
    
    <div class="dialog-content">
      <!-- 成功结果 -->
      <div v-if="generatedShareUrl" class="share-result">
        <div class="success-icon-mini">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6 9 17l-5-5"/></svg>
        </div>
        <p class="result-title">表单创建成功！</p>
        <div class="url-box">
          <input type="text" :value="generatedShareUrl" readonly class="url-input" />
          <button class="copy-btn" @click="handleCopyUrl">复制</button>
        </div>
        <p class="result-hint">分享此链接给外部用户，他们可以直接填写表单</p>
      </div>
      
      <!-- 步骤1：基本信息 -->
      <div v-else-if="!showFieldSelector">
        <p class="dialog-subtitle">创建一个可分享的表单，外部用户无需登录即可填写</p>
        <el-input v-model="shareFormName" placeholder="请输入表单名称" size="large" class="styled-input" />
        <el-input v-model="shareFormDesc" placeholder="表单描述（可选）" size="large" class="styled-input" style="margin-top: 12px;" />
        <el-button type="primary" @click="handleGoToFieldSelector" size="large" class="main-btn">
          下一步：选择字段
        </el-button>
      </div>
      
      <!-- 步骤2：字段选择 -->
      <div v-else class="field-selector">
        <p class="dialog-subtitle">点击选择要包含在表单中的字段</p>
        
        <!-- 加载中 -->
        <div v-if="loadingFields" class="loading-fields">
          <div class="spinner-small"></div>
          <span>加载字段中...</span>
        </div>
        
        <!-- 字段列表 -->
        <div v-else class="field-list">
          <div 
            v-for="field in availableFields" 
            :key="field.field_id" 
            class="field-item" 
            :class="{ 'field-selected': isFieldSelected(field.field_id) }"
            @click="toggleFieldSelection(field)"
          >
            <div class="field-check">
              <svg v-if="isFieldSelected(field.field_id)" viewBox="0 0 24 24" fill="currentColor">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
              </svg>
            </div>
            <div class="field-info">
              <span class="field-name">{{ field.label }}</span>
              <span class="field-type">{{ getFieldTypeName(field.input_type) }}</span>
            </div>
            <div 
              v-if="isFieldSelected(field.field_id)" 
              class="field-required" 
              @click.stop="toggleRequired(field.field_id)"
            >
              <span :class="{ 'required-active': selectedFields.find(f => f.field_id === field.field_id)?.required }">
                必填
              </span>
            </div>
          </div>
          <div v-if="availableFields.length === 0" class="no-fields">
            暂无可用字段
          </div>
        </div>
        
        <!-- 已选字段数量 -->
        <div class="selected-count" v-if="selectedFields.length > 0">
          已选择 {{ selectedFields.length }} 个字段
        </div>
        
        <!-- 操作按钮 -->
        <div class="field-actions">
          <el-button @click="goBackToBasicInfo" size="large">返回</el-button>
          <el-button type="primary" @click="handleCreate" size="large" :disabled="selectedFields.length === 0">
            创建表单
          </el-button>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<style scoped>
/* 覆盖 el-dialog 默认样式 */
:deep(.el-dialog) {
  padding: 16px !important;
}

:deep(.el-dialog__header) {
  padding: 0 !important;
  margin: 0 !important;
}

:deep(.el-dialog__body) {
  padding: 0 !important;
  margin: 0 !important;
}

/* 弹窗头部 */
.dialog-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 12px;
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

.share-icon {
  background: #f5f5f7;
  color: #34c759;
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
  padding-top: 4px;
}

.dialog-subtitle {
  font-size: 13px;
  color: #86868b;
  text-align: center;
  margin-bottom: 8px;
  margin-top: 0;
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

/* 分享结果 */
.share-result {
  text-align: center;
  padding: 20px 0;
}

.success-icon-mini {
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #34c759 0%, #30d158 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.success-icon-mini svg {
  width: 28px;
  height: 28px;
  color: #fff;
}

.result-title {
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 16px;
}

.url-box {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.url-input {
  flex: 1;
  padding: 12px 16px;
  border: 2px solid #e5e5ea;
  border-radius: 10px;
  font-size: 13px;
  color: #1d1d1f;
  background: #fafafa;
}

.copy-btn {
  padding: 12px 20px;
  background: #007aff;
  border: none;
  border-radius: 10px;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.copy-btn:hover {
  background: #0066d6;
}

.result-hint {
  font-size: 12px;
  color: #86868b;
}

/* 字段选择器 */
.field-selector {
  padding: 0 4px;
}

.loading-fields {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px 0;
  color: #86868b;
}

.spinner-small {
  width: 20px;
  height: 20px;
  border: 2px solid #e5e5ea;
  border-top-color: #007aff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.field-list {
  max-height: 350px;
  overflow-y: auto;
  margin: 8px 0;
  padding: 2px 0;
}

.field-item {
  display: flex;
  align-items: center;
  padding: 14px 16px;
  margin-bottom: 10px;
  background: #fff;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid #e5e5ea;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.field-item:hover {
  border-color: #c7c7cc;
  background: #fafafa;
}

.field-item.field-selected {
  background: #f0f7ff;
  border-color: #3370ff;
  box-shadow: 0 2px 8px rgba(51, 112, 255, 0.15);
}

.field-check {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  background: #fff;
  border: 2px solid #d1d1d6;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 14px;
  flex-shrink: 0;
  transition: all 0.2s;
}

.field-selected .field-check {
  background: #3370ff;
  border-color: #3370ff;
}

.field-check svg {
  width: 14px;
  height: 14px;
  color: #fff;
}

.field-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.field-name {
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
}

.field-type {
  font-size: 12px;
  color: #86868b;
}

.field-required {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  background: #f0f0f5;
  color: #86868b;
  cursor: pointer;
  transition: all 0.2s;
}

.field-required:hover {
  background: #e5e5ea;
}

.field-required .required-active {
  color: #ff3b30;
  font-weight: 500;
}

.no-fields {
  text-align: center;
  padding: 40px;
  color: #86868b;
}

.selected-count {
  text-align: center;
  font-size: 13px;
  color: #3370ff;
  font-weight: 500;
  margin-bottom: 16px;
}

.field-actions {
  display: flex;
  gap: 12px;
}

.field-actions .el-button {
  flex: 1;
  height: 44px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 500;
}
</style>
