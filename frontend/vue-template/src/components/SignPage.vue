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
        <div 
          v-if="formConfig?.description" 
          class="form-description markdown-content"
          v-html="parseMarkdown(formConfig.description)"
        ></div>

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
          <!-- 文本输入 (所见即所得编辑器) -->
          <div v-if="field.input_type === 'text'" class="textarea-wrapper">
             <div 
               class="rich-editor"
               contenteditable="true"
               :data-placeholder="field.placeholder || `请输入${field.label}`"
               @input="(e) => handleRichInput(e, field.field_id)"
               @blur="(e) => handleRichBlur(e, field.field_id)"
               @focus="(e) => handleRichFocus(e, field.field_id)"
               v-html="getFieldHtml(field.field_id)"
             ></div>
          </div>
          
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
          
          <!-- 附件输入 -->
          <div v-else-if="field.input_type === 'attachment'" class="signature-section">
            
            <!-- 调试信息（开发时可见） -->
            <!-- <div style="font-size: 10px; color: #999; padding: 4px;">
              Debug: existingAttachments[{{ field.field_id }}] = {{ existingAttachments[field.field_id] }}
            </div> -->
            
            <!-- 现有附件展示：简洁的文件信息卡片 -->
            <div v-if="existingAttachments[field.field_id] && existingAttachments[field.field_id].length > 0" class="existing-attachments-simple">
              <div class="existing-label">原始附件:</div>
              <div v-for="(file, idx) in existingAttachments[field.field_id]" :key="idx" class="file-card-simple">
                <svg class="file-icon-blue" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z"/>
                  <path d="M14 2v6h6"/>
                </svg>
                <div class="file-info-simple">
                  <div class="file-name-simple">{{ file?.name || '未命名文件' }}</div>
                  <div class="file-type-simple">{{ file?.type || 'unknown' }}</div>
                  <div class="file-status-simple">该记录已有附件，无需重复上传</div>
                </div>
              </div>
            </div>

            <!-- 输入区域：始终显示，允许用户覆盖 -->
            <div class="attachment-input-area" :class="{ 'has-existing': existingAttachments[field.field_id]?.length > 0 }">
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
              <div v-if="!uploadMode[field.field_id]" class="canvas-container" :ref="setContainerRef(field.field_id)">
                <canvas 
                  :ref="setCanvasRef(field.field_id)"
                  @mousedown="(e) => startDrawing(e, field.field_id)"
                  @mousemove="(e) => draw(e, field.field_id)"
                  @mouseup="() => stopDrawing(field.field_id)"
                  @mouseleave="() => stopDrawing(field.field_id)"
                  @touchstart.prevent="(e) => handleTouchStart(e, field.field_id)"
                  @touchmove.prevent="(e) => handleTouchMove(e, field.field_id)"
                  @touchend="() => stopDrawing(field.field_id)"
                ></canvas>
                <button type="button" class="clear-btn" @click="() => clearCanvas(field.field_id)">
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
          </div>
          
          <!-- 默认：文本区域 (支持 Markdown 预览和自动高度) -->
          <div v-else class="textarea-wrapper">
             <!-- Markdown 预览（当有内容时显示） -->
             <div 
               v-if="formData[field.field_id]" 
               class="markdown-preview"
               v-html="parseMarkdown(formData[field.field_id])"
             ></div>
             
             <!-- 输入框（始终显示，自动调整高度） -->
             <textarea
              :id="field.field_id"
              :ref="el => { if (el) textareaRefs[field.field_id] = el }"
              v-model="formData[field.field_id]"
              :placeholder="field.placeholder || `请输入${field.label}`"
              class="form-textarea auto-resize"
              @input="autoResize"
            ></textarea>
          </div>
          
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
import { ref, onMounted, nextTick, computed, watch, reactive } from 'vue'
import { getFormRecordData } from '@/services/api'
import { marked } from 'marked'
import { htmlToMarkdown } from '@/utils/htmlToMarkdown'


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
// 现有附件数据
const existingAttachments = ref({})

// 显示 Toast
function showToast(msg, type = 'info', duration = 2000) {
  toastMessage.value = msg
  toastType.value = type
  setTimeout(() => {
    toastMessage.value = ''
  }, duration)
}

// 解析 Markdown
function parseMarkdown(text) {
  if (!text) return ''
  try {
    // 确保 marked 已加载
    if (!marked || typeof marked.parse !== 'function') {
      console.warn('[SignPage] marked library not loaded correctly', marked)
      return text
    }
    return marked.parse(String(text))
  } catch (e) {
    console.error('[SignPage] Markdown parsing error:', e)
    return text
  }
}

// 检查是否为图片
function isImage(file) {
  if (!file) return false

  const name = String(file.name || '')
  const type = String(file.type || '')
  const url = String(file.url || '')

  if (type && type.startsWith('image/')) return true
  if (/\.(jpg|jpeg|png|gif|webp|bmp|svg)$/i.test(name)) return true

  const urlPath = url.split('?')[0].split('#')[0]
  return /\.(jpg|jpeg|png|gif|webp|bmp|svg)$/i.test(urlPath)
}

// 自动调整文本域高度
function autoResize(event) {
  const el = event?.target
  if (!el) return
  el.style.height = 'auto'
  el.style.height = el.scrollHeight + 'px'
}

// 调整所有文本域高度
function resizeAllTextareas() {
  nextTick(() => {
    setTimeout(() => {
      console.log('[SignPage] Resizing all textareas...')
      let count = 0
      
      // 使用 refs 调整高度
      Object.entries(textareaRefs).forEach(([fieldId, el]) => {
        if (el && el.tagName === 'TEXTAREA') {
          const oldHeight = el.style.height
          el.style.height = 'auto'
          el.style.height = el.scrollHeight + 'px'
          console.log(`[SignPage] Resized textarea ${fieldId}: ${oldHeight} -> ${el.style.height}, scrollHeight: ${el.scrollHeight}`)
          count++
        }
      })
      
      // 备用：使用 querySelector
      document.querySelectorAll('textarea.form-textarea').forEach(el => {
        if (!el.style.height || el.style.height === 'auto') {
          el.style.height = 'auto'
          el.style.height = el.scrollHeight + 'px'
          console.log(`[SignPage] Resized textarea (querySelector): ${el.id}, height: ${el.style.height}`)
          count++
        }
      })
      
      console.log(`[SignPage] Total textareas resized: ${count}`)
    }, 200)
  })
}

// 画布相关（按字段独立维护，避免多个附件字段互相影响）
const canvasRefs = ref({})
const containerRefs = ref({})
const canvasCtx = ref({})
const drawingState = ref({})
const hasSignatureMap = ref({})

const textareaRefs = reactive({})
const editingRichFields = ref({})
// 存储每个字段的当前 HTML 显示内容，避免编辑时被重置
const fieldHtmlContent = ref({})

// 获取字段 HTML
function getFieldHtml(fieldId) {
  // 如果首次加载还没有 HTML 内容，且有 Markdown 数据，则生成
  if (fieldHtmlContent.value[fieldId] === undefined) {
      const md = formData.value[fieldId] || ''
      fieldHtmlContent.value[fieldId] = parseMarkdown(md)
  }
  return fieldHtmlContent.value[fieldId] || ''
}

function handleRichFocus(e, fieldId) {
  editingRichFields.value[fieldId] = true
}

function handleRichBlur(e, fieldId) {
  editingRichFields.value[fieldId] = false
  // 失去焦点时，根据最新的 markdown 重新生成 HTML，实现"格式化"效果 (Snap format)
  const md = formData.value[fieldId] || ''
  fieldHtmlContent.value[fieldId] = parseMarkdown(md)
}

function handleRichInput(e, fieldId) {
  const html = e.target.innerHTML
  
  // 更新 Markdown 数据 (Model)
  const md = htmlToMarkdown(html)
  formData.value[fieldId] = md
  // 注意：此处不要更新 fieldHtmlContent，否则会重置光标
}

function getHasSignature(fieldId) {
  return !!hasSignatureMap.value[fieldId]
}

function setHasSignature(fieldId, val) {
  hasSignatureMap.value[fieldId] = !!val
}

function ensureDrawingState(fieldId) {
  if (!drawingState.value[fieldId]) {
    drawingState.value[fieldId] = { isDrawing: false }
  }
  return drawingState.value[fieldId]
}

function setCanvasRef(fieldId) {
  return (el) => {
    if (el) canvasRefs.value[fieldId] = el
  }
}

function setContainerRef(fieldId) {
  return (el) => {
    if (el) containerRefs.value[fieldId] = el
  }
}

function getCanvasElement(fieldId) {
  return canvasRefs.value[fieldId] || null
}

function getContainerElement(fieldId) {
  return containerRefs.value[fieldId] || null
}

function getCtx(fieldId) {
  return canvasCtx.value[fieldId] || null
}

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
    if (formConfig.value.show_data && formConfig.value.record_index > 0) {
      try {
        const recordDataResult = await getFormRecordData(formId)
        
        if (recordDataResult && recordDataResult.success && recordDataResult.data) {
          const recordData = recordDataResult.data
          
          formConfig.value.fields?.forEach(field => {
            if (recordData.hasOwnProperty(field.field_id)) {
              const value = recordData[field.field_id]
              
              if (field.input_type === 'multiselect') {
                formData.value[field.field_id] = Array.isArray(value) ? value : (value ? [value] : [])
              } else if (field.input_type === 'checkbox') {
                formData.value[field.field_id] = Boolean(value)
              } else if (field.input_type === 'attachment') {
                // 处理附件字段：如果有现有数据，保存到 existingAttachments
                console.log(`[SignPage] Loading attachment for field ${field.field_id}:`, value)
                if (value && Array.isArray(value) && value.length > 0) {
                  existingAttachments.value[field.field_id] = value
                  console.log(`[SignPage] Existing attachments set for field ${field.field_id}:`, existingAttachments.value[field.field_id])
                }
              } else {
                formData.value[field.field_id] = value !== null && value !== undefined ? String(value) : ''
                // 预填充时同时生成 HTML
                if (field.input_type === 'text') {
                   fieldHtmlContent.value[field.field_id] = parseMarkdown(formData.value[field.field_id])
                }
              }
            }
          })
          
          // 数据填充后立即调整文本域高度
          resizeAllTextareas()
        } 
      } catch (e) {
        console.error('[SignPage] 预填充数据失败:', e)
        const errorMsg = e.response?.data?.detail || e.message || '加载记录数据失败'
        showToast(`预填充数据失败: ${errorMsg}`, 'warning')
      }
    }
    
    loading.value = false
    
    // 调整所有文本域高度
    resizeAllTextareas()

    // 初始化每个附件字段的画布（只初始化签名模式的字段）
    const attachFields = (formConfig.value?.fields || []).filter(f => f.input_type === 'attachment')
    for (const field of attachFields) {
      const fieldId = field.field_id
      
      // 如果该字段没有现有附件，且不是上传模式，则初始化画布
      const hasExisting = existingAttachments.value[fieldId]?.length > 0
      const isUploadMode = uploadMode.value[fieldId] === true
      
      if (!hasExisting && !isUploadMode) {
        console.log(`[SignPage] Initializing canvas for field: ${fieldId}`)
        initCanvas(fieldId)
      }
    }
  } catch (e) {
    error.value = { title: '加载失败', message: e.message }
    loading.value = false
  }
}

// 初始化画布
function initCanvas(fieldId) {
  const tryInitCanvas = (attempt = 0) => {
    if (attempt > 10) {
      console.warn(`[SignPage] Failed to initialize canvas for field ${fieldId} after 10 attempts`)
      return
    }

    const cvs = getCanvasElement(fieldId)
    const container = getContainerElement(fieldId)

    if (!cvs || !container) {
      console.log(`[SignPage] Canvas or container not found for field ${fieldId}, attempt ${attempt}`)
      setTimeout(() => tryInitCanvas(attempt + 1), 100)
      return
    }

    if (container.clientWidth === 0) {
      console.log(`[SignPage] Container width is 0 for field ${fieldId}, attempt ${attempt}`)
      setTimeout(() => tryInitCanvas(attempt + 1), 100)
      return
    }

    cvs.width = container.clientWidth
    cvs.height = 200

    const ctx = cvs.getContext('2d')
    if (!ctx) {
      console.error(`[SignPage] Failed to get 2d context for field ${fieldId}`)
      return
    }

    canvasCtx.value[fieldId] = ctx

    ctx.strokeStyle = '#1d1d1f'
    ctx.lineWidth = 2
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'

    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, cvs.width, cvs.height)
    
    console.log(`[SignPage] Canvas initialized successfully for field ${fieldId}`)
  }

  setTimeout(() => tryInitCanvas(0), 150)
}

function getPos(e, fieldId) {
  const cvs = getCanvasElement(fieldId)
  if (!cvs) return { x: 0, y: 0 }
  const rect = cvs.getBoundingClientRect()
  return {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top
  }
}

function startDrawing(e, fieldId) {
  const ctx = getCtx(fieldId)
  if (!ctx) return

  const st = ensureDrawingState(fieldId)
  st.isDrawing = true
  setHasSignature(fieldId, true)

  const pos = getPos(e, fieldId)
  ctx.beginPath()
  ctx.moveTo(pos.x, pos.y)
}

function draw(e, fieldId) {
  const ctx = getCtx(fieldId)
  const st = ensureDrawingState(fieldId)
  if (!st.isDrawing || !ctx) return

  const pos = getPos(e, fieldId)
  ctx.lineTo(pos.x, pos.y)
  ctx.stroke()
}

function stopDrawing(fieldId) {
  const st = ensureDrawingState(fieldId)
  st.isDrawing = false
}

function handleTouchStart(e, fieldId) {
  const cvs = getCanvasElement(fieldId)
  const ctx = getCtx(fieldId)
  if (!cvs || !ctx) return

  const touch = e.touches[0]
  const rect = cvs.getBoundingClientRect()
  const st = ensureDrawingState(fieldId)

  st.isDrawing = true
  setHasSignature(fieldId, true)

  ctx.beginPath()
  ctx.moveTo(touch.clientX - rect.left, touch.clientY - rect.top)
}

function handleTouchMove(e, fieldId) {
  const ctx = getCtx(fieldId)
  const st = ensureDrawingState(fieldId)
  if (!st.isDrawing || !ctx) return

  const cvs = getCanvasElement(fieldId)
  if (!cvs) return

  const touch = e.touches[0]
  const rect = cvs.getBoundingClientRect()
  ctx.lineTo(touch.clientX - rect.left, touch.clientY - rect.top)
  ctx.stroke()
}

function clearCanvas(fieldId) {
  const cvs = getCanvasElement(fieldId)
  const ctx = getCtx(fieldId)
  if (!ctx || !cvs) return

  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, cvs.width, cvs.height)
  setHasSignature(fieldId, false)
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

  const attachFields = (formConfig.value?.fields || []).filter(f => f.input_type === 'attachment')

  // 手工验证：两个附件字段分别校验 / 阻断
  if (attachFields.length === 2) {
    for (const field of attachFields) {
      if (!field.required) continue

      const hasExisting = (existingAttachments.value[field.field_id]?.length || 0) > 0
      if (hasExisting) continue

      const isUpload = !!uploadMode.value[field.field_id]
      if (isUpload) {
        if (!selectedFiles.value[field.field_id]) {
          fieldErrors.value[field.field_id] = '请选择文件'
          valid = false
        }
      } else {
        if (!getHasSignature(field.field_id)) {
          fieldErrors.value[field.field_id] = '请签名'
          valid = false
        }
      }
    }
  }

  for (const field of formConfig.value?.fields || []) {
    if (field.input_type === 'attachment') continue

    if (field.required) {
      const val = formData.value[field.field_id]

      if (field.input_type === 'multiselect') {
        if (!val || val.length === 0) {
          fieldErrors.value[field.field_id] = '请选择至少一项'
          valid = false
        }
      } else if (field.input_type === 'checkbox') {
      } else {
        if (!val && val !== 0) {
          fieldErrors.value[field.field_id] = `请填写${field.label}`
          valid = false
        }
      }
    }

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



function getFileUrl(fileOrUrl) {
  // 如果传入的是 file 对象
  if (typeof fileOrUrl === 'object' && fileOrUrl !== null) {
      // 优先使用临时下载链接（如果有）
      if (fileOrUrl.temp_url) {
          console.log('[getFileUrl] Using temp_url:', fileOrUrl.temp_url)
          return fileOrUrl.temp_url
      }
      
      if (fileOrUrl.file_token) {
          // 使用后端代理 (需要 formId 来获取授权)
          const proxyUrl = `${API_BASE}/api/form/proxy/media/${formId}/${fileOrUrl.file_token}`
          console.log('[getFileUrl] Using proxy for file_token:', fileOrUrl.file_token, '-> URL:', proxyUrl)
          return proxyUrl
      }
      // 如果对象有 url 属性，递归处理
      if (fileOrUrl.url) {
          console.log('[getFileUrl] No file_token, using url:', fileOrUrl.url)
          return getFileUrl(fileOrUrl.url)
      }
      return ''
  }

  const url = fileOrUrl
  if (!url) return ''
  if (url.startsWith('http') || url.startsWith('//') || url.startsWith('blob:')) {
    return url
  }
  // Remove leading slash if present to avoid double slashes
  const cleanUrl = url.startsWith('/') ? url.slice(1) : url
  return `${API_BASE}/${cleanUrl}`
}

// 提交表单
async function submitForm() {
  if (!validateForm()) return
  
  submitting.value = true
  submitProgress.value = '准备数据...'
  
  try {
    const fd = new FormData()
    
    // 获取附件字段（支持多个）
    const attachFields = formConfig.value?.fields?.filter(f => f.input_type === 'attachment') || []

    // 对每个附件字段，按各自的模式提交对应文件/签名
    for (const attachField of attachFields) {
      const fieldId = attachField.field_id
      const isUpload = !!uploadMode.value[fieldId]

      if (isUpload && selectedFiles.value[fieldId]) {
        submitProgress.value = '正在上传文件...'
        fd.append(`attachment_${fieldId}`, selectedFiles.value[fieldId])
      } else if (!isUpload && getHasSignature(fieldId)) {
        const cvs = getCanvasElement(fieldId)
        if (cvs) {
          submitProgress.value = '正在上传签名...'
          const blob = await new Promise(resolve => {
            cvs.toBlob(resolve, 'image/png')
          })
          if (blob) {
            fd.append(`attachment_${fieldId}`, blob, `signature_${fieldId}.png`)
          }
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

// 监听表单数据变化，自动调整文本域高度
watch(formData, () => {
  resizeAllTextareas()
}, { deep: true })

watch(uploadMode, (newVal, oldVal) => {
  // 当任何字段从上传模式切换到签名模式时，初始化该字段的画布
  for (const fieldId in newVal) {
    const wasUpload = oldVal[fieldId] === true
    const isSignature = newVal[fieldId] === false
    
    if (wasUpload && isSignature) {
      // 从上传切换到签名，需要初始化画布
      nextTick(() => {
        console.log(`[SignPage] Initializing canvas for field: ${fieldId}`)
        initCanvas(fieldId)
      })
    }
  }
}, { deep: true })

onMounted(() => {
  loadFormConfig()
  
  // 确保在挂载后也调整一次
  setTimeout(() => {
    resizeAllTextareas()
  }, 500)
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

/* 新增样式 */
.textarea-wrapper {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 富文本编辑器 */
.rich-editor {
  width: 100%;
  min-height: 80px;         /* Match form-textarea minimum height */
  overflow-y: hidden;       /* Hide scrollbar as it auto-expands */
  padding: 12px 14px;       /* Match form-textarea padding */
  border: 1px solid #e5e6eb; /* Match form-textarea border */
  border-radius: 8px;       /* Match form-textarea radius */
  font-size: 15px;          /* Match form-textarea font size */
  color: #1d1d1f;           /* Match form-textarea color */
  background: #f5f6f7;      /* Match form-textarea background */
  transition: all 0.2s;
  outline: none;
  line-height: 1.6;
  box-sizing: border-box;
}

.rich-editor:focus {
  border-color: #3370ff;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(51, 112, 255, 0.1);
}

.rich-editor:empty:before {
  content: attr(data-placeholder);
  color: #9ca3af;
  pointer-events: none;
  display: block;
}

/* 编辑器内部 Markdown 样式适配 */
.rich-editor h1, .rich-editor h2, .rich-editor h3 { 
  margin-top: 0.5em; 
  margin-bottom: 0.5em; 
  font-weight: 600; 
  color: #1f2329;
}
.rich-editor p { margin-bottom: 0.5em; }
.rich-editor ul, .rich-editor ol { padding-left: 20px; margin-bottom: 0.5em; }
.rich-editor li { list-style-type: disc; }
.rich-editor blockquote {
  border-left: 4px solid #ddd;
  padding-left: 10px;
  color: #666;
  margin: 10px 0;
}

/* Removed duplicate .form-textarea rule - see unified rule below */

/* 附件展示 - 简洁版 */
.existing-attachments-simple {
  margin-bottom: 16px;
}

.existing-label {
  font-size: 13px;
  color: #86868b;
  margin-bottom: 8px;
}

.file-card-simple {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: #fff;
  border: 1px solid #e5e5ea;
  border-radius: 12px;
  margin-bottom: 12px;
}

.file-icon-blue {
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  color: #007aff;
}

.file-info-simple {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-name-simple {
  font-size: 15px;
  font-weight: 500;
  color: #1d1d1f;
  word-break: break-all;
}

.file-type-simple {
  font-size: 13px;
  color: #86868b;
}

.file-status-simple {
  font-size: 13px;
  color: #34c759;
  margin-top: 4px;
}

.attachment-input-area.has-existing {
  margin-top: 0;
}
.image-preview {
  cursor: pointer;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e5e5ea;
  transition: all 0.2s;
  max-width: 100%;
}
.image-preview:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  transform: translateY(-2px);
}
.image-preview img {
  width: auto;
  max-width: 100%;
  height: auto;
  max-height: 300px;
  display: block;
  object-fit: contain;
  background: #fff;
}
.image-error {
  display: block;
  padding: 20px;
  color: #ff4d4f;
  font-size: 13px;
  text-align: center;
}
.file-link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: #f5f5f7;
  border-radius: 8px;
  text-decoration: none;
  color: #1d1d1f;
  transition: all 0.2s;
  width: 100%;
}
.file-link:hover {
  background: #e8e8ed;
}
.file-link.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.file-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  color: #86868b;
}
.file-name {
  font-size: 14px;
  word-break: break-all;
}
.file-note {
  font-size: 12px;
  color: #999;
  margin-left: 8px;
}

/* 文件信息卡片 */
.file-info-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: #fff;
  border-radius: 12px;
  border: 2px solid #e5e5ea;
  width: 100%;
}

/* 图片预览包装器 */
.image-preview-wrapper {
  width: 100%;
  border-radius: 12px;
  overflow: hidden;
  border: 2px solid #e5e5ea;
  background: #fff;
}
.attachment-image {
  width: 100%;
  height: auto;
  max-height: 400px;
  object-fit: contain;
  display: block;
}

.image-preview img:hover {
  /* 移除transform，已在父元素处理 */
}
.file-link {
  display: flex;
  align-items: center;
  font-size: 14px;
  color: #007aff;
  text-decoration: none;
  background: #fff;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid #e5e5ea;
  transition: background 0.2s;
  max-width: 100%;
}
.file-link:hover {
  background: #f2f2f7;
}
.file-link.is-disabled {
  color: #86868b;
  cursor: not-allowed;
}
.file-name {
  display: block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-icon {
  width: 18px;
  height: 18px;
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
  min-height: 80px;
  max-height: none;
  overflow-y: hidden;
  resize: none; /* 禁用手动调整，使用自动调整 */
  line-height: 1.6;
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
/* Markdown 内容样式 */
.markdown-content {
  font-size: 14px;
  color: #86868b;
  line-height: 1.6;
  text-align: left;
  margin-top: 8px;
}

.markdown-content p {
  margin-bottom: 8px;
}

.markdown-content ul, .markdown-content ol {
  padding-left: 20px;
  margin-bottom: 8px;
}

.markdown-content a {
  color: #007aff;
  text-decoration: none;
}

.markdown-content a:hover {
  text-decoration: underline;
}

.markdown-content blockquote {
  border-left: 4px solid #e5e5ea;
  padding-left: 12px;
  color: #86868b;
  margin: 8px 0;
}
</style>
