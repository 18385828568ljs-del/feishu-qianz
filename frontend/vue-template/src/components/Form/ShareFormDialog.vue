<!--
  分享表单弹窗组件
  包含表单基本信息输入和字段选择
-->
<script setup>
import { defineProps, defineEmits, watch, ref, computed } from 'vue'
import { ElDialog, ElInput, ElButton, ElMessageBox } from 'element-plus'
import { useShareForm } from '@/composables/useShareForm'
import { getRecordCount } from '@/services/api'

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
  selectedRecordIndex,
  showData,
  loadTableFields,
  toggleFieldSelection,
  isFieldSelected,
  toggleRequired,
  goToFieldSelector,
  goBackToBasicInfo,
  handleCreateShareForm,
  copyShareUrl,
  getFieldTypeName,
  resetShareForm,
  formList,
  loadingList,
  loadHistory
} = useShareForm()

const activeTab = ref('create') // 'create' | 'list'

function switchTab(tab) {
  activeTab.value = tab
  if (tab === 'list') {
    loadHistory(props.userKey)
  }
}

function formatDate(ts) {
  if (!ts) return ''
  return new Date(ts * 1000).toLocaleString()
}

// 列表中的复制
function copyLink(formId) {
  // 生成正确的分享链接
  const shareUrl = `${window.location.protocol}//${window.location.host}/sign?id=${formId}`
  
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(shareUrl).then(() => {
        showToast('链接已复制', 'success')
    }).catch(() => {
       showToast('复制失败', 'error') 
    })
  } else {
     // 简单回退
     showToast('请手动复制链接', 'warning')
  }
}

// 清空表单列表
async function clearAllForms() {
  if (formList.value.length === 0) return
  
  try {
    await ElMessageBox.confirm(
      `确定要清空所有表单记录（共 ${formList.value.length} 条）吗？此操作不可恢复！`,
      '清空确认',
      {
        confirmButtonText: '确定清空',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    // 调用后端API删除所有表单
    const { clearAllForms: clearAllFormsAPI } = await import('@/services/api')
    await clearAllFormsAPI(props.userKey)
    
    // 清空前端显示
    formList.value = []
    showToast('列表已清空', 'success')
  } catch (e) {
    // 用户取消或出错
    if (e !== 'cancel') {
      console.error('清空失败:', e)
      showToast('清空失败', 'error')
    }
  }
}

// 记录数量
const recordCount = ref(0)
const loadingRecordCount = ref(false)

// 动态生成记录条选项
const recordOptions = computed(() => {
  const count = recordCount.value || 0
  // 添加“新增记录”选项（value=0表示创建新记录）
  const options = [
    { value: 0, label: '新增一条记录', isCreateNew: true }
  ]
  // 添加现有记录选项
  for (let i = 0; i < count; i++) {
    options.push({
      value: i + 1,
      label: `记录条${i + 1}`
    })
  }
  return options
})

// 自定义下拉框状态
const isDropdownOpen = ref(false)

// 切换下拉框
function toggleDropdown() {
  if (loadingRecordCount.value || recordOptions.value.length === 0) return
  isDropdownOpen.value = !isDropdownOpen.value
}

// 选择记录
function selectRecord(value) {
  selectedRecordIndex.value = value
  isDropdownOpen.value = false
}

// 获取当前选中的标签
function getSelectedLabel() {
  const option = recordOptions.value.find(opt => opt.value === selectedRecordIndex.value)
  return option ? option.label : '请选择'
}

// 显示 Toast
function showToast(message, type) {
  emit('toast', { message, type })
}

// 加载记录数量
async function loadRecordCount() {
  if (!props.appToken || !props.tableId) {
    return
  }
  
  try {
    loadingRecordCount.value = true
    const result = await getRecordCount(props.appToken, props.tableId)
    if (result.success && result.count !== undefined) {
      recordCount.value = result.count
      // 如果当前选择的记录索引超出范围，重置为1
      if (selectedRecordIndex.value > result.count || selectedRecordIndex.value < 1) {
        selectedRecordIndex.value = 1
      }
    }
  } catch (e) {
    console.error('加载记录数量失败:', e)
    // 失败时使用默认值，不显示错误提示，避免干扰用户体验
    recordCount.value = 0
  } finally {
    loadingRecordCount.value = false
  }
}

// 加载字段
async function loadFields() {
  await Promise.all([
    loadTableFields(props.appToken, props.tableId, showToast),
    loadRecordCount()
  ])
}

// 进入字段选择
function handleGoToFieldSelector() {
  goToFieldSelector(showToast)
}

// 创建表单
async function handleCreate() {
  const success = await handleCreateShareForm({
    tableId: props.tableId,
    userKey: props.userKey
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
    recordCount.value = 0
  }, 300)
}

// 监听弹窗打开
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    // 默认打开创建页，但如果上次是在列表页且想保持状态也可以
    // 这里选择每次打开重置为创建页，或者根据需求保留
    activeTab.value = 'create' 
    resetShareForm()
    loadFields()
  }
})

// 监听 recordOptions 变化，确保选中值在有效范围内
watch(recordOptions, (newOptions) => {
  if (newOptions.length > 0 && selectedRecordIndex.value) {
    // 确保 selectedRecordIndex 在有效范围内
    if (selectedRecordIndex.value < 1 || selectedRecordIndex.value > newOptions.length) {
      selectedRecordIndex.value = 1
    }
  }
}, { immediate: true })
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
    class="share-form-dialog"
  >
    <template #header>
      <div class="dialog-header-clean">
        <!-- 简单的 Tab 切换 -->
        <div class="header-tabs">
          <div 
            class="header-tab" 
            :class="{ active: activeTab === 'create' }"
            @click="switchTab('create')"
          >
            创建表单
          </div>
          <div 
            class="header-tab" 
            :class="{ active: activeTab === 'list' }"
            @click="switchTab('list')"
          >
            表单队列
          </div>
        </div>
        
        <button class="close-btn-clean" @click="handleClose">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6 6 18M6 6l12 12"/>
          </svg>
        </button>
      </div>
    </template>
    
    <div class="dialog-content-clean">
      <!-- 历史列表视图 -->
      <div v-if="activeTab === 'list'" class="history-view">
         <!-- 清空按钮 -->
         <div v-if="formList.length > 0" class="list-header">
           <button class="clear-all-btn" @click="clearAllForms">
             清空列表
           </button>
         </div>
         
         <div v-if="loadingList" class="loading-fields">
            <div class="spinner-small"></div>
            <span>加载历史记录...</span>
         </div>
         <div v-else-if="formList.length === 0" class="no-fields">
            <p>暂无已创建的表单</p>
         </div>
         <div v-else class="history-list">
            <div v-for="form in formList" :key="form.form_id" class="history-item">
              <div class="history-info">
                <div class="history-name">{{ form.name }}</div>
                <div class="history-meta">
                  {{ formatDate(form.created_at) }} · {{ form.submit_count }} 次提交
                </div>
              </div>
              <button 
                class="copy-btn-small" 
                @click="copyLink(form.form_id)"
              >
                复制链接
              </button>
            </div>
         </div>
      </div>

      <!-- 成功结果 -->
      <div v-else-if="generatedShareUrl" class="share-result">
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
      <div v-else-if="activeTab === 'create' && !showFieldSelector">
        <p class="dialog-subtitle">创建一个可分享的表单，外部用户无需登录即可填写</p>
        <el-input v-model="shareFormName" placeholder="请输入表单名称" size="large" class="styled-input" />
        <el-input v-model="shareFormDesc" placeholder="表单描述（可选）" size="large" class="styled-input" style="margin-top: 12px;" />
        <el-button type="primary" @click="handleGoToFieldSelector" size="large" class="main-btn">
          下一步：选择字段
        </el-button>
      </div>
      
      <!-- 步骤2：字段选择 -->
      <div v-else class="field-selector-clean">
        
        <!-- 顶部配置区域：记录选择 + 数据显示 -->
        <div class="config-section">
          <!-- 记录选择 -->
          <div class="config-item">
            <div class="config-label-row">
              <span class="config-label">关联记录</span>
              <span class="config-sub" v-if="recordOptions.length > 0">{{ recordOptions.length }} 条记录可用</span>
            </div>
            
            <div 
              class="modern-select" 
              :class="{ 'is-open': isDropdownOpen, 'is-disabled': loadingRecordCount || recordOptions.length === 0 }"
              v-click-outside="() => isDropdownOpen = false"
            >
              <div class="modern-select-trigger" @click="toggleDropdown">
                <span class="modern-select-value" :class="{'placeholder': !getSelectedLabel()}">
                  {{ loadingRecordCount ? '加载中...' : (getSelectedLabel() || (recordOptions.length === 0 ? '暂无记录' : '请选择')) }}
                </span>
                <svg class="modern-select-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </div>
              
              <div class="modern-select-dropdown" v-show="isDropdownOpen">
                <div 
                  v-for="option in recordOptions" 
                  :key="option.value"
                  class="modern-select-option"
                  :class="{ 
                    'is-selected': selectedRecordIndex === option.value,
                    'is-create-new': option.isCreateNew 
                  }"
                  @click="selectRecord(option.value)"
                >
                  <span class="option-label">{{ option.label }}</span>
                  <svg v-if="selectedRecordIndex === option.value" class="check-icon" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                  </svg>
                </div>
              </div>
            </div>
          </div>

          <!-- 显示数据开关 (仅当选择了具体记录时显示) -->
          <div class="config-item switch-row" v-if="selectedRecordIndex && selectedRecordIndex > 0">
            <div class="switch-info">
              <span class="switch-label">预填数据</span>
              <span class="switch-desc">将会把选中记录的数据填充到表单中</span>
            </div>
            <label class="modern-switch">
              <input type="checkbox" v-model="showData">
              <span class="slider"></span>
            </label>
          </div>
        </div>
        
        <!-- 字段列表头部 -->
        <div class="field-list-header">
           <span class="list-title">表单字段</span>
           <span class="list-count" v-if="selectedFields.length > 0">已选 {{ selectedFields.length }}</span>
        </div>

        <!-- 加载中 -->
        <div v-if="loadingFields" class="loading-fields">
          <div class="spinner-small"></div>
          <span>加载字段中...</span>
        </div>
        
        <!-- 字段列表 -->
        <div v-else class="field-list-modern">
          <div 
            v-for="field in availableFields" 
            :key="field.field_id" 
            class="field-card" 
            :class="{ 'is-active': isFieldSelected(field.field_id) }"
            @click="toggleFieldSelection(field)"
          >
            <!-- 选中状态指示条 -->
            <div class="active-indicator"></div>

            <!-- 复选框 -->
            <div class="card-check">
               <svg v-if="isFieldSelected(field.field_id)" viewBox="0 0 24 24" fill="currentColor">
                 <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
               </svg>
            </div>

            <!-- 内容 -->
            <div class="card-content">
              <div class="card-title">{{ field.label }}</div>
              <div class="card-meta">{{ getFieldTypeName(field.input_type) }}</div>
            </div>

            <!-- 必填开关 -->
            <div class="card-actions">
              <div 
                 v-if="isFieldSelected(field.field_id)"
                 class="required-badge"
                 :class="{ 'is-required': selectedFields.find(f => f.field_id === field.field_id)?.required }"
                 @click.stop="toggleRequired(field.field_id)"
              >
                必填
              </div>
            </div>
          </div>
          
          <div v-if="availableFields.length === 0" class="no-fields">
            暂无可用字段
          </div>
        </div>
        
        <!-- 底部按钮 -->
        <div class="modern-footer">
          <button class="footer-btn cancel" @click="goBackToBasicInfo">返回</button>
          <button 
            class="footer-btn primary" 
            @click="handleCreate" 
            :disabled="selectedFields.length === 0"
          >
            创建表单
          </button>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<style scoped>
/* 覆盖 el-dialog */
:deep(.el-dialog) {
  padding: 0 !important;
  border-radius: 20px !important;
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(0,0,0,0.15) !important;
}

:deep(.el-dialog__header),
:deep(.el-dialog__body) {
  padding: 0 !important;
  margin: 0 !important;
}

/* 头部样式 */
.dialog-header-clean {
  position: relative;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #f0f0f2;
  background: #fff;
}

.header-title {
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
}

.close-btn-clean {
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  width: 30px;
  height: 30px;
  border: none;
  background: transparent;
  color: #86868b;
  border-radius: 50%;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.close-btn-clean:hover {
  background: #f5f5f7;
  color: #1d1d1f;
}

.close-btn-clean svg {
  width: 18px;
  height: 18px;
}

/* 内容区域 */
.dialog-content-clean {
  padding: 20px;
  background: #fff;
}

.dialog-subtitle {
  font-size: 14px;
  color: #86868b;
  text-align: center;
  margin: 0 0 20px 0;
}

/* 成功页 */
.share-result { padding: 20px 0; text-align: center; }
.success-icon-mini { 
  width: 56px; height: 56px; border-radius: 50%; 
  background: #e8fff0; color: #34c759;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 16px; 
}
.result-title { font-size: 18px; font-weight: 600; margin-bottom: 16px; }
.url-box { display: flex; gap: 8px; margin-bottom: 12px; }
.url-input { flex: 1; padding: 12px; background: #f5f5f7; border: none; border-radius: 10px; color: #86868b; }
.copy-btn { background: #007aff; color: #fff; border: none; padding: 0 20px; border-radius: 10px; font-weight: 600; cursor: pointer; }
.result-hint { font-size: 13px; color: #86868b; }

/* Tab 样式 */
.header-tabs {
  display: flex;
  background: #f5f5f7;
  padding: 4px;
  border-radius: 10px;
}
.header-tab {
  padding: 6px 16px;
  font-size: 14px;
  font-weight: 500;
  color: #86868b;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s;
}
.header-tab.active {
  background: #fff;
  color: #1d1d1f;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  font-weight: 600;
}

/* 历史列表样式 */
.history-view {
  min-height: 200px;
}
.history-list {
  max-height: 380px;
  overflow-y: auto;
}
.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #f0f0f2;
}
.history-item:last-child {
  border-bottom: none;
}
.history-name {
  font-weight: 600;
  font-size: 15px;
  color: #1d1d1f;
  margin-bottom: 4px;
}
.history-meta {
  font-size: 12px;
  color: #86868b;
}
.copy-btn-small {
  padding: 6px 14px;
  background: #f5f5f7;
  color: #007aff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.list-header {
  padding: 12px 16px;
  display: flex;
  justify-content: flex-end;
  border-bottom: 1px solid #f0f0f2;
}
.clear-all-btn {
  padding: 6px 14px;
  background: #fff;
  color: #f56c6c;
  border: 1px solid #f56c6c;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.clear-all-btn:hover {
  background: #fef0f0;
}

.copy-btn-small:hover {
  background: #e8f2ff;
}

/* 基础输入框 */
/* 基础输入框 */
.styled-input {
  margin-bottom: 10px;
  --el-input-border-color: transparent; /* Element Plus 变量覆盖 */
  --el-input-hover-border-color: transparent;
  --el-input-focus-border-color: transparent;
}

.styled-input :deep(.el-input__wrapper) {
  border-radius: 12px;
  padding: 4px 12px;
  box-shadow: 0 0 0 1px #e5e5ea inset !important; /* 强制覆盖 */
  background-color: #f9f9fa;
  transition: all 0.2s;
}

.styled-input :deep(.el-input__wrapper:hover) {
  background-color: #fff;
  box-shadow: 0 0 0 1px #c7c7cc inset !important;
}

.styled-input :deep(.el-input__wrapper.is-focus) {
  background-color: #fff;
  box-shadow: 0 0 0 2px rgba(0, 122, 255, 0.2) inset, 0 0 0 1px #007aff inset !important;
}

.styled-input :deep(.el-input__inner) {
  height: 36px;
  line-height: 36px;
  font-size: 15px;
  color: #1d1d1f;
  border: none !important; /* 去除原生边框 */
  box-shadow: none !important; /* 去除阴影 */
  background: transparent !important; /* 透明背景 */
  outline: none !important;
  padding: 0 !important;
}

.main-btn {
  width: 100%; height: 44px; border-radius: 12px; font-weight: 600; margin-top: 16px;
  font-size: 15px;
}

/* ======== 字段选择页面优化 ======== */
.field-selector-clean {
  display: flex;
  flex-direction: column;
}

/* 配置区域 */
.config-section {
  background: #f9f9fa;
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 20px;
  border: 1px solid #f0f0f5;
}

.config-item {
  margin-bottom: 0;
}
.config-item:not(:last-child) { margin-bottom: 16px; }

.config-label-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  align-items: center;
}

.config-label { font-size: 13px; font-weight: 600; color: #1d1d1f; }
.config-sub { font-size: 12px; color: #86868b; }

/* 现代下拉框 */
.modern-select { position: relative; }
.modern-select-trigger {
  background: #fff;
  border: 1px solid #e5e5ea;
  border-radius: 10px;
  padding: 8px 12px;
  min-height: 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}
.modern-select-trigger:hover { border-color: #c7c7cc; }
.modern-select.is-open .modern-select-trigger { border-color: #007aff; box-shadow: 0 0 0 3px rgba(0,122,255,0.1); }

.modern-select-value { font-size: 14px; font-weight: 500; color: #1d1d1f; }
.modern-select-value.placeholder { color: #86868b; font-weight: 400; }
.modern-select-arrow { width: 16px; height: 16px; color: #86868b; }

.modern-select-dropdown {
  position: absolute; top: calc(100% + 6px); left: 0; right: 0;
  background: #fff; border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.12);
  padding: 6px; z-index: 2000; max-height: 240px; overflow-y: auto;
  border: 1px solid #f0f0f2;
}

.modern-select-option {
  padding: 10px 12px; border-radius: 8px;
  display: flex; justify-content: space-between; align-items: center;
  font-size: 14px; color: #1d1d1f; cursor: pointer;
}
.modern-select-option:hover { background: #f5f5f7; }
.modern-select-option.is-selected { background: #f0f7ff; color: #007aff; font-weight: 500; }
.modern-select-option.is-create-new { color: #34c759; border-bottom: 1px solid #f9f9fa; margin-bottom: 4px; }
.modern-select-option.is-create-new:hover { background: #f0fff4; }

/* 修复：添加漏掉的 check-icon 样式 */
.modern-select-option .check-icon {
  width: 16px;
  height: 16px;
  color: #007aff;
  flex-shrink: 0;
}
.modern-select-option.is-create-new .check-icon {
  color: #34c759;
}

/* Switch 开关行 */
.switch-row {
  display: flex; justify-content: space-between; align-items: center;
  padding-top: 12px; border-top: 1px solid #ebebef; margin-top: 12px;
}
.switch-info { display: flex; flex-direction: column; gap: 2px; }
.switch-label { font-size: 13px; font-weight: 600; color: #1d1d1f; }
.switch-desc { font-size: 12px; color: #86868b; }

.modern-switch { position: relative; display: inline-block; width: 44px; height: 24px; cursor: pointer; }
.modern-switch input { opacity: 0; width: 0; height: 0; }
.slider {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background-color: #e5e5ea; transition: .4s; border-radius: 24px;
}
.slider:before {
  position: absolute; content: ""; height: 20px; width: 20px;
  left: 2px; bottom: 2px; background-color: white;
  transition: .4s; border-radius: 50%; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
input:checked + .slider { background-color: #34c759; }
input:checked + .slider:before { transform: translateX(20px); }

/* 字段列表 */
.field-list-header {
  display: flex; justify-content: space-between; align-items: baseline;
  padding: 0 4px 10px 4px;
}
.list-title { font-size: 15px; font-weight: 600; color: #1d1d1f; }
.list-count { font-size: 12px; color: #007aff; background: #f0f7ff; padding: 2px 8px; border-radius: 10px; }

.field-list-modern {
  max-height: 380px; overflow-y: auto; padding: 2px;
}

.field-card {
  display: flex; align-items: center;
  padding: 12px 14px; margin-bottom: 8px;
  background: #fff; border: 1px solid #f0f0f2;
  border-radius: 12px; cursor: pointer; transition: all 0.2s;
  position: relative; overflow: hidden;
}
.field-card:hover { border-color: #d1d1d6; background: #fafafa; }
.field-card.is-active { 
  border-color: #007aff; background: #f7faff;
  box-shadow: 0 4px 12px rgba(0,122,255,0.06);
}

.active-indicator {
  position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
  background: #007aff; opacity: 0; transition: opacity 0.2s;
}
.field-card.is-active .active-indicator { opacity: 1; }

.card-check {
  width: 22px; height: 22px; border-radius: 6px;
  border: 2px solid #d1d1d6; background: #fff;
  display: flex; align-items: center; justify-content: center;
  margin-right: 12px; color: #fff; transition: all 0.2s;
}
.field-card.is-active .card-check { background: #007aff; border-color: #007aff; }
.card-check svg { width: 14px; height: 14px; }

.card-content { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.card-title { font-size: 15px; font-weight: 500; color: #1d1d1f; }
.card-meta { font-size: 12px; color: #86868b; }

.required-badge {
  font-size: 12px; color: #98989d; background: #f2f2f7;
  padding: 4px 8px; border-radius: 6px; font-weight: 500;
  transition: all 0.2s;
}
.required-badge:hover { background: #e5e5ea; }
.required-badge.is-required { color: #ff3b30; background: #ffebeb; }

/* 底部按钮 */
.modern-footer { margin-top: 24px; display: flex; gap: 12px; }
.footer-btn {
  flex: 1; height: 44px; border-radius: 12px;
  font-size: 15px; font-weight: 600; cursor: pointer; border: none;
  transition: all 0.2s;
}
.footer-btn.cancel { background: #f5f5f7; color: #1d1d1f; }
.footer-btn.cancel:hover { background: #e5e5ea; }
.footer-btn.primary { background: #007aff; color: #fff; box-shadow: 0 4px 10px rgba(0,122,255,0.2); }
.footer-btn.primary:hover { background: #0066d6; box-shadow: 0 6px 14px rgba(0,122,255,0.25); }
.footer-btn.primary:disabled { background: #e5e5ea; color: #c7c7cc; box-shadow: none; cursor: not-allowed; }

.loading-fields { padding: 40px; text-align: center; color: #86868b; font-size: 13px; display: flex; flex-direction: column; align-items: center; gap: 12px; }
.spinner-small { width: 24px; height: 24px; border: 3px solid #e5e5ea; border-top-color: #007aff; border-radius: 50%; animation: spin 1s linear infinite; }
.no-fields { padding: 40px; text-align: center; color: #86868b; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
