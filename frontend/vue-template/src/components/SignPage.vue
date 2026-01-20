<template>
  <div class="sign-page">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>
    
    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <svg class="error-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/><path d="M12 8v4m0 4h.01"/>
      </svg>
      <h2>{{ error.title }}</h2>
      <p>{{ error.message }}</p>
    </div>
    
    <!-- 成功状态 -->
    <div v-else-if="submitted" class="success-state">
      <div class="success-icon-wrap">
        <svg class="success-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M20 6 9 17l-5-5"/>
        </svg>
      </div>
      <h2>提交成功</h2>
      <p>您的签名已成功提交</p>
    </div>
    
    <!-- 表单主体 -->
    <div v-else class="form-container">
      <!-- 飞书风格顶部装饰 -->
      <header class="form-header">
        <div class="header-pattern"></div>
        <h1>{{ formConfig?.name || '表单' }}</h1>
        <p v-if="formConfig?.description">{{ formConfig.description }}</p>
      </header>
      
      <div class="form-body">
        <!-- 动态表单字段 -->
        <div 
          v-for="field in formConfig?.fields || []" 
          :key="field.field_id" 
          class="form-group"
          :class="{ 'has-error': fieldErrors[field.field_id] }"
        >
          <label :for="field.field_id">
            {{ field.label }}
            <span v-if="field.required" class="required">*</span>
          </label>
          
          <!-- 文本输入 -->
          <input 
            v-if="field.input_type === 'text'"
            :id="field.field_id"
            v-model="formData[field.field_id]"
            type="text"
            :placeholder="field.placeholder || `请输入${field.label}`"
            class="form-input"
          />
          
          <!-- 数字输入 -->
          <input 
            v-else-if="field.input_type === 'number'"
            :id="field.field_id"
            v-model="formData[field.field_id]"
            type="number"
            :placeholder="field.placeholder || `请输入${field.label}`"
            class="form-input"
          />
          
          <!-- 电话输入 -->
          <input 
            v-else-if="field.input_type === 'phone'"
            :id="field.field_id"
            v-model="formData[field.field_id]"
            type="tel"
            :placeholder="field.placeholder || '请输入手机号'"
            class="form-input"
          />
          
          <!-- 邮箱输入 -->
          <input 
            v-else-if="field.input_type === 'email'"
            :id="field.field_id"
            v-model="formData[field.field_id]"
            type="email"
            :placeholder="field.placeholder || '请输入邮箱'"
            class="form-input"
          />
          
          <!-- URL 输入 -->
          <input 
            v-else-if="field.input_type === 'url'"
            :id="field.field_id"
            v-model="formData[field.field_id]"
            type="url"
            :placeholder="field.placeholder || '请输入链接'"
            class="form-input"
          />
          
          <!-- 日期选择 -->
          <input 
            v-else-if="field.input_type === 'date'"
            :id="field.field_id"
            v-model="formData[field.field_id]"
            type="date"
            class="form-input date-input"
          />
          
          <!-- 单选 -->
          <div v-else-if="field.input_type === 'select'" class="select-wrapper">
            <select 
              :id="field.field_id"
              v-model="formData[field.field_id]"
              class="form-select"
            >
              <option value="" disabled>请选择{{ field.label }}</option>
              <option v-for="opt in field.options" :key="opt" :value="opt">{{ opt }}</option>
            </select>
          </div>
          
          <!-- 多选 -->
          <div v-else-if="field.input_type === 'multiselect'" class="checkbox-group">
            <label 
              v-for="opt in field.options" 
              :key="opt" 
              class="checkbox-item"
            >
              <input 
                type="checkbox" 
                :value="opt"
                v-model="formData[field.field_id]"
              />
              <span class="checkbox-label">{{ opt }}</span>
            </label>
          </div>
          
          <!-- 复选框 -->
          <label v-else-if="field.input_type === 'checkbox'" class="toggle-item">
            <input 
              type="checkbox" 
              v-model="formData[field.field_id]"
            />
            <span class="toggle-switch"></span>
            <span class="toggle-text">{{ field.label }}</span>
          </label>
          
          <div v-else-if="field.input_type === 'attachment'" class="signature-section">
            <!-- 模式切换 -->
            <div class="mode-toggle">
              <button 
                type="button" 
                class="mode-btn" 
                :class="{ active: !uploadMode[field.field_id] }"
                @click="uploadMode[field.field_id] = false"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17 3a2.85 2.85 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
                </svg>
                签名
              </button>
              <button 
                type="button" 
                class="mode-btn" 
                :class="{ active: uploadMode[field.field_id] }"
                @click="uploadMode[field.field_id] = true"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
                </svg>
                上传
              </button>
            </div>
            
            <!-- 签名模式 -->
            <div v-if="!uploadMode[field.field_id]" class="canvas-container" ref="containerRef">
              <canvas 
                ref="canvasRef"
                @mousedown="startDrawing"
                @mousemove="draw"
                @mouseup="stopDrawing"
                @mouseleave="stopDrawing"
                @touchstart.prevent="handleTouchStart"
                @touchmove.prevent="handleTouchMove"
                @touchend="stopDrawing"
              ></canvas>
              <button type="button" class="clear-btn" @click="clearCanvas">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
                清除
              </button>
              <p class="hint">请在上方区域签名</p>
            </div>
            
            <!-- 上传模式 -->
            <div v-else class="upload-area">
              <input 
                type="file" 
                :id="'file-' + field.field_id"
                @change="handleFileSelect($event, field.field_id)"
                accept="image/*,.pdf,.doc,.docx"
                class="file-input"
              />
              <label :for="'file-' + field.field_id" class="upload-box">
                <template v-if="!selectedFiles[field.field_id]">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="17 8 12 3 7 8"/>
                    <line x1="12" y1="3" x2="12" y2="15"/>
                  </svg>
                  <span>点击选择文件</span>
                  <small>支持图片、PDF、Word</small>
                </template>
                <template v-else>
                  <div class="file-preview">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                    </svg>
                    <span>{{ selectedFiles[field.field_id].name }}</span>
                    <button type="button" class="remove-file" @click.prevent="removeFile(field.field_id)">×</button>
                  </div>
                </template>
              </label>
            </div>
          </div>
          
          <!-- 默认：文本区域 -->
          <textarea
            v-else
            :id="field.field_id"
            v-model="formData[field.field_id]"
            :placeholder="field.placeholder || `请输入${field.label}`"
            class="form-textarea"
            rows="3"
          ></textarea>
          
          <!-- 错误提示 -->
          <span v-if="fieldErrors[field.field_id]" class="error-msg">
            {{ fieldErrors[field.field_id] }}
          </span>
        </div>
      </div>
      
      <footer class="form-footer">
        <!-- 进度提示（提交时显示） -->
        <div v-if="submitting" class="progress-hint">
          <div class="progress-spinner"></div>
          <span>{{ submitProgress || '处理中...' }}</span>
        </div>
        <!-- 提交按钮（非提交时显示） -->
        <button 
          v-else
          class="submit-btn" 
          @click="submitForm"
        >
          提交
        </button>
      </footer>
    </div>

    <!-- 居中 Toast 提示 -->
    <Transition name="toast-fade">
      <div v-if="toastMessage" class="toast-overlay">
        <div class="toast-card">
          <!-- Success -->
          <svg v-if="toastType === 'success'" class="toast-icon success" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <!-- Error -->
          <svg v-else-if="toastType === 'error'" class="toast-icon error" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
          <!-- Warning -->
          <svg v-else-if="toastType === 'warning'" class="toast-icon warning" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <!-- Info -->
          <svg v-else class="toast-icon info" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="16" x2="12" y2="12"></line>
            <line x1="12" y1="8" x2="12.01" y2="8"></line>
          </svg>
          <p>{{ toastMessage }}</p>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed, watch } from 'vue'
import { getFormRecordData } from '@/services/api'

// 从 URL 获取表单 ID
const formId = new URLSearchParams(window.location.search).get('id') || ''
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

// 状态
const loading = ref(true)
const error = ref(null)
const submitted = ref(false)
const submitting = ref(false)
const submitProgress = ref('')  // 提交进度提示
const formConfig = ref(null)
const formData = ref({})
const fieldErrors = ref({})
const toastMessage = ref('')
const toastType = ref('info')

// 上传模式状态（每个附件字段独立）
const uploadMode = ref({})
const selectedFiles = ref({})

// 显示 Toast
function showToast(msg, type = 'info', duration = 2000) {
  toastMessage.value = msg
  toastType.value = type
  setTimeout(() => {
    toastMessage.value = ''
  }, duration)
}

// 画布相关
const canvasRef = ref(null)
const containerRef = ref(null)
let ctx = null
let isDrawing = false
let hasSignature = false

// 是否包含附件字段
const hasAttachmentField = computed(() => {
  return formConfig.value?.fields?.some(f => f.input_type === 'attachment') || false
})

// 加载表单配置
async function loadFormConfig() {
  if (!formId) {
    error.value = { title: '参数错误', message: '缺少表单ID' }
    loading.value = false
    return
  }
  
  try {
    const resp = await fetch(`${API_BASE}/api/form/${formId}/config`)
    if (!resp.ok) {
      const data = await resp.json()
      throw new Error(data.detail || '表单不存在')
    }
    formConfig.value = await resp.json()
    
    // 初始化表单数据
    formConfig.value.fields?.forEach(field => {
      if (field.input_type === 'multiselect') {
        formData.value[field.field_id] = []
      } else if (field.input_type === 'checkbox') {
        formData.value[field.field_id] = false
      } else {
        formData.value[field.field_id] = ''
      }
    })
    
    // 如果启用了显示数据功能，预填充记录数据
    console.log('[SignPage] 检查预填充条件:', {
      show_data: formConfig.value.show_data,
      record_index: formConfig.value.record_index,
      form_id: formId
    })
    
    if (formConfig.value.show_data && formConfig.value.record_index > 0) {
      try {
        console.log('[SignPage] 开始加载记录数据...')
        const recordDataResult = await getFormRecordData(formId)
        console.log('[SignPage] 记录数据响应:', recordDataResult)
        
        if (recordDataResult && recordDataResult.success && recordDataResult.data) {
          const recordData = recordDataResult.data
          console.log('[SignPage] 解析后的记录数据:', recordData)
          console.log('[SignPage] 记录数据中的所有字段ID:', Object.keys(recordData))
          console.log('[SignPage] 表单字段列表:', formConfig.value.fields?.map(f => ({ id: f.field_id, label: f.label, type: f.input_type })))
          
          let filledCount = 0
          // 填充数据到表单
          formConfig.value.fields?.forEach(field => {
            // 检查字段ID是否存在于记录数据中
            const fieldExists = recordData.hasOwnProperty(field.field_id)
            console.log(`[SignPage] 检查字段 ${field.field_id} (${field.label}): 存在=${fieldExists}, 值=`, recordData[field.field_id])
            
            if (fieldExists) {
              const value = recordData[field.field_id]
              console.log(`[SignPage] 填充字段 ${field.field_id} (${field.label}):`, value)
              
              // 根据字段类型处理数据
              if (field.input_type === 'multiselect') {
                // 多选：确保是数组
                formData.value[field.field_id] = Array.isArray(value) ? value : (value ? [value] : [])
              } else if (field.input_type === 'checkbox') {
                // 复选框：布尔值
                formData.value[field.field_id] = Boolean(value)
              } else if (field.input_type === 'attachment') {
                // 附件：如果有数据，显示提示（不实际预填充文件）
                if (value && Array.isArray(value) && value.length > 0) {
                  // 附件字段已有数据，但不预填充文件，用户仍需上传
                  // 可以在这里添加提示信息
                }
              } else {
                // 文本、数字、日期、单选等：直接赋值
                formData.value[field.field_id] = value !== null && value !== undefined ? String(value) : ''
              }
              filledCount++
            } else {
              console.log(`[SignPage] 字段 ${field.field_id} (${field.label}) 在记录数据中不存在`)
            }
          })
          
          console.log(`[SignPage] 预填充完成，共填充 ${filledCount} 个字段`)
          console.log('[SignPage] 最终表单数据:', formData.value)
        } else {
          console.warn('[SignPage] 记录数据格式不正确:', recordDataResult)
        }
      } catch (e) {
        console.error('[SignPage] 预填充数据失败:', e)
        console.error('[SignPage] 错误详情:', e.response?.data || e.message)
        console.error('[SignPage] 错误堆栈:', e.stack)
        // 显示错误提示给用户
        const errorMsg = e.response?.data?.detail || e.message || '加载记录数据失败'
        showToast(`预填充数据失败: ${errorMsg}`, 'warning')
        // 预填充失败不影响表单正常使用，只记录警告
      }
    } else {
      console.log('[SignPage] 未启用显示数据功能，跳过预填充')
    }
    
    loading.value = false
    
    await nextTick()
    initCanvas()
  } catch (e) {
    error.value = { title: '加载失败', message: e.message }
    loading.value = false
  }
}

// 初始化画布
function initCanvas() {
  // 使用 requestAnimationFrame 确保 DOM 完全渲染后再初始化
  const tryInitCanvas = (attempt = 0) => {
    if (attempt > 10) {
      return
    }
    
    // ref 在 v-for 中可能是数组
    const cvs = Array.isArray(canvasRef.value) ? canvasRef.value[0] : canvasRef.value
    const container = Array.isArray(containerRef.value) ? containerRef.value[0] : containerRef.value
    
    if (!cvs || !container) {
      // 如果 canvas 还不存在，可能是因为默认进入了上传模式，跳过
      return
    }
    
    // 确保容器有宽度
    if (container.clientWidth === 0) {
      setTimeout(() => tryInitCanvas(attempt + 1), 100)
      return
    }
    
    cvs.width = container.clientWidth
    cvs.height = 200
    
    ctx = cvs.getContext('2d')
    if (!ctx) {
      console.warn('Failed to get canvas 2d context')
      return
    }
    
    ctx.strokeStyle = '#1d1d1f'
    ctx.lineWidth = 2
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    
    // 白色背景
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, cvs.width, cvs.height)
    

  }
  
  // 延迟初始化
  setTimeout(() => tryInitCanvas(0), 150)
}

// 获取 canvas 元素
function getCanvasElement() {
  return Array.isArray(canvasRef.value) ? canvasRef.value[0] : canvasRef.value
}

function getPos(e) {
  const cvs = getCanvasElement()
  if (!cvs) return { x: 0, y: 0 }
  const rect = cvs.getBoundingClientRect()
  return {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top
  }
}

function startDrawing(e) {
  if (!ctx) return
  isDrawing = true
  hasSignature = true
  const pos = getPos(e)
  ctx.beginPath()
  ctx.moveTo(pos.x, pos.y)
}

function draw(e) {
  if (!isDrawing || !ctx) return
  const pos = getPos(e)
  ctx.lineTo(pos.x, pos.y)
  ctx.stroke()
}

function stopDrawing() {
  isDrawing = false
}

function handleTouchStart(e) {
  const cvs = getCanvasElement()
  if (!cvs || !ctx) return
  const touch = e.touches[0]
  const rect = cvs.getBoundingClientRect()
  isDrawing = true
  hasSignature = true
  ctx.beginPath()
  ctx.moveTo(touch.clientX - rect.left, touch.clientY - rect.top)
}

function handleTouchMove(e) {
  if (!isDrawing || !ctx) return
  const cvs = getCanvasElement()
  if (!cvs) return
  const touch = e.touches[0]
  const rect = cvs.getBoundingClientRect()
  ctx.lineTo(touch.clientX - rect.left, touch.clientY - rect.top)
  ctx.stroke()
}

function clearCanvas() {
  const cvs = getCanvasElement()
  if (!ctx || !cvs) return
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, cvs.width, cvs.height)
  hasSignature = false
}

// 选择文件
function handleFileSelect(event, fieldId) {
  const file = event.target.files?.[0]
  if (file) {
    selectedFiles.value[fieldId] = file
  }
}

// 移除已选文件
function removeFile(fieldId) {
  delete selectedFiles.value[fieldId]
}

// 验证表单
function validateForm() {
  fieldErrors.value = {}
  let valid = true
  
  for (const field of formConfig.value?.fields || []) {
    if (field.required) {
      const val = formData.value[field.field_id]
      
      if (field.input_type === 'multiselect') {
        if (!val || val.length === 0) {
          fieldErrors.value[field.field_id] = '请选择至少一项'
          valid = false
        }
      } else if (field.input_type === 'attachment') {
        // 检查签名模式或上传模式是否有内容
        const isUpload = uploadMode.value[field.field_id]
        if (isUpload) {
          if (!selectedFiles.value[field.field_id]) {
            fieldErrors.value[field.field_id] = '请选择文件'
            valid = false
          }
        } else {
          if (!hasSignature) {
            fieldErrors.value[field.field_id] = '请签名'
            valid = false
          }
        }
      } else if (field.input_type === 'checkbox') {
        // 复选框不强制必选
      } else {
        if (!val && val !== 0) {
          fieldErrors.value[field.field_id] = `请填写${field.label}`
          valid = false
        }
      }
    }
    
    // 格式验证
    const val = formData.value[field.field_id]
    if (val) {
      if (field.input_type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val)) {
        fieldErrors.value[field.field_id] = '请输入有效的邮箱地址'
        valid = false
      }
      if (field.input_type === 'phone' && !/^1[3-9]\d{9}$/.test(val)) {
        fieldErrors.value[field.field_id] = '请输入有效的手机号'
        valid = false
      }
    }
  }
  
  return valid
}

// 提交表单
async function submitForm() {
  if (!validateForm()) return
  
  submitting.value = true
  submitProgress.value = '准备数据...'
  
  try {
    const fd = new FormData()
    
    // 获取附件字段
    const attachField = formConfig.value?.fields?.find(f => f.input_type === 'attachment')
    
    if (attachField) {
      const isUpload = uploadMode.value[attachField.field_id]
      
      if (isUpload && selectedFiles.value[attachField.field_id]) {
        // 文件上传模式
        submitProgress.value = '正在上传文件...'
        fd.append('signature', selectedFiles.value[attachField.field_id])
      } else if (!isUpload && hasSignature) {
        // 签名模式
        const cvs = getCanvasElement()
        if (cvs) {
          submitProgress.value = '正在上传签名...'
          const blob = await new Promise(resolve => {
            cvs.toBlob(resolve, 'image/png')
          })
          fd.append('signature', blob, 'signature.png')
        }
      }
    }
    
    // 添加表单数据
    fd.append('form_data', JSON.stringify(formData.value))
    
    submitProgress.value = '正在提交表单...'
    const resp = await fetch(`${API_BASE}/api/form/${formId}/submit`, {
      method: 'POST',
      body: fd
    })
    
    if (!resp.ok) {
      const data = await resp.json()
      throw new Error(data.detail || '提交失败')
    }
    
    submitProgress.value = '提交成功！'
    submitted.value = true
  } catch (e) {
    showToast(e.message || '提交失败', 'error')
  } finally {
    submitting.value = false
    submitProgress.value = ''
  }
}

// 监听上传模式切换，当切换到签名模式时重新初始化画布
watch(uploadMode, (newVal, oldVal) => {
  // 遍历所有字段，检查是否有从 true 切换到 false（即从上传模式切换到签名模式）
  for (const fieldId in newVal) {
    if (oldVal[fieldId] === true && newVal[fieldId] === false) {
      // 需要异步等待 DOM 更新后再初始化画布
      nextTick(() => {
        initCanvas()
      })
      break
    }
  }
}, { deep: true })

onMounted(() => {
  loadFormConfig()
})
</script>

<style scoped>
/* 简洁风格表单 */
.sign-page {
  min-height: 100vh;
  background: #f5f5f7;
  padding: 20px;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Segoe UI', sans-serif;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  color: #1d1d1f;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e5e5ea;
  border-top-color: #3370ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 错误状态 */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  color: #1d1d1f;
  text-align: center;
}

.error-icon {
  width: 64px;
  height: 64px;
  margin-bottom: 16px;
  color: #ff3b30;
}

.error-state h2 {
  font-size: 24px;
  margin-bottom: 8px;
  color: #1d1d1f;
}

.error-state p {
  color: #86868b;
}

/* 成功状态 */
.success-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  color: #1d1d1f;
  text-align: center;
}

.success-icon-wrap {
  width: 80px;
  height: 80px;
  background: #e8f5e9;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.success-icon {
  width: 40px;
  height: 40px;
  color: #34c759;
}

.success-state h2 {
  font-size: 28px;
  margin-bottom: 8px;
  color: #1d1d1f;
}

.success-state p {
  color: #86868b;
}

/* 表单容器 */
.form-container {
  max-width: 500px;
  margin: 0 auto;
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}

.form-header {
  position: relative;
  padding: 32px 24px 24px;
  background: linear-gradient(135deg, #4a9ff5 0%, #6bb5ff 100%);
  color: #fff;
  overflow: hidden;
  text-align: center;
}

.header-pattern {
  position: absolute;
  top: -50%;
  right: -20%;
  width: 200px;
  height: 200px;
  background: rgba(255,255,255,0.1);
  border-radius: 50%;
}

.form-header h1 {
  position: relative;
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 6px;
}

.form-header p {
  position: relative;
  font-size: 14px;
  opacity: 0.9;
}

.form-body {
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group.has-error .form-input,
.form-group.has-error .form-select,
.form-group.has-error .form-textarea {
  border-color: #ff4d4f;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
  margin-bottom: 8px;
}

.required {
  color: #ff4d4f;
  margin-left: 2px;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  font-size: 15px;
  color: #1d1d1f;
  background: #f5f6f7;
  transition: all 0.2s;
  box-sizing: border-box;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: #3370ff;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(51, 112, 255, 0.1);
}

.form-textarea {
  resize: none;
  min-height: 80px;
}

.date-input {
  cursor: pointer;
}

/* 下拉选择 */
.select-wrapper {
  position: relative;
}

.form-select {
  appearance: none;
  cursor: pointer;
  padding-right: 36px;
}

.select-wrapper::after {
  content: '';
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  border: 5px solid transparent;
  border-top-color: #86868b;
  pointer-events: none;
}

/* 多选框组 */
.checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.checkbox-item {
  display: flex;
  align-items: center;
  padding: 10px 14px;
  background: #f5f6f7;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.checkbox-item:hover {
  background: #eee;
}

.checkbox-item input {
  display: none;
}

.checkbox-item input:checked + .checkbox-label {
  color: #3370ff;
}

.checkbox-item:has(input:checked) {
  background: #e8f0ff;
  border-color: #3370ff;
}

.checkbox-label {
  font-size: 14px;
  color: #1d1d1f;
}

/* 开关 */
.toggle-item {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.toggle-item input {
  display: none;
}

.toggle-switch {
  width: 44px;
  height: 24px;
  background: #e5e6eb;
  border-radius: 12px;
  position: relative;
  transition: all 0.2s;
}

.toggle-switch::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  background: #fff;
  border-radius: 50%;
  transition: all 0.2s;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.toggle-item input:checked + .toggle-switch {
  background: #3370ff;
}

.toggle-item input:checked + .toggle-switch::after {
  left: 22px;
}

.toggle-text {
  font-size: 14px;
  color: #1d1d1f;
}

/* 签名区域 */
.signature-section {
  margin-top: 4px;
}

/* 模式切换 */
.mode-toggle {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.mode-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px;
  background: #f5f6f7;
  border: 2px solid transparent;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #86868b;
  cursor: pointer;
  transition: all 0.2s;
}

.mode-btn svg {
  width: 18px;
  height: 18px;
}

.mode-btn:hover {
  background: #e5e6eb;
  color: #1d1d1f;
}

.mode-btn.active {
  background: #e8f0ff;
  border-color: #3370ff;
  color: #3370ff;
}

/* 文件上传区域 */
.upload-area {
  margin-top: 8px;
}

.file-input {
  display: none;
}

.upload-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px 20px;
  border: 2px dashed #d1d1d6;
  border-radius: 8px;
  background: #fafafa;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}

.upload-box:hover {
  border-color: #3370ff;
  background: #f0f7ff;
}

.upload-box svg {
  display: block;
  width: 40px;
  height: 40px;
  color: #86868b;
  margin: 0 auto 12px auto;
}

.upload-box span {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
  margin-bottom: 4px;
}

.upload-box small {
  display: block;
  font-size: 12px;
  color: #86868b;
}

.file-preview {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.file-preview svg {
  width: 32px;
  height: 32px;
  color: #3370ff;
  flex-shrink: 0;
  margin: 0;
}

.file-preview span {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
}

.remove-file {
  width: 24px;
  height: 24px;
  border: none;
  background: #ff4d4f;
  color: #fff;
  border-radius: 50%;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.canvas-container {
  position: relative;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}

.canvas-container canvas {
  display: block;
  width: 100%;
  touch-action: none;
}

.clear-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: rgba(0,0,0,0.05);
  border: none;
  border-radius: 6px;
  font-size: 12px;
  color: #86868b;
  cursor: pointer;
  transition: all 0.2s;
}

.clear-btn:hover {
  background: rgba(0,0,0,0.1);
}

.clear-btn svg {
  width: 14px;
  height: 14px;
}

.hint {
  font-size: 12px;
  color: #86868b;
  margin-top: 8px;
}

.error-msg {
  display: block;
  font-size: 12px;
  color: #ff4d4f;
  margin-top: 6px;
}

/* 底部 */
.form-footer {
  padding: 20px 24px 24px;
  border-top: 1px solid #f0f0f5;
}

.submit-btn {
  width: 100%;
  height: 48px;
  background: #3370ff;
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s;
}

.submit-btn:hover:not(:disabled) {
  background: #2860e1;
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-loading {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

/* 进度提示 */
.progress-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 12px 16px;
  margin-bottom: 12px;
  background: linear-gradient(135deg, #e8f4ff 0%, #f0f7ff 100%);
  border-radius: 8px;
  color: #3370ff;
  font-size: 14px;
  font-weight: 500;
}

.progress-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(51, 112, 255, 0.2);
  border-top-color: #3370ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* Toast 样式 */
.toast-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  pointer-events: none;
}

.toast-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px 32px;
  background: rgba(0, 0, 0, 0.85);
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
  color: #fff;
  font-size: 15px;
  font-weight: 500;
  pointer-events: auto;
}

.toast-icon {
  width: 40px;
  height: 40px;
}

.toast-icon.success { color: #34c759; }
.toast-icon.error { color: #ff3b30; }
.toast-icon.warning { color: #ff9500; }
.toast-icon.info { color: #007aff; }

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: scale(0.9);
}
</style>
