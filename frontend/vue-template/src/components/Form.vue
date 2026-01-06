<script setup>
import { bitable } from '@lark-base-open/js-sdk'
import { ref, onMounted, computed, onUnmounted } from 'vue'
import SignaturePad from './SignaturePad.vue'
import { ElButton, ElDialog, ElInput, ElTag } from 'element-plus'
import { 
  uploadSignature, authStart, authStatus, 
  getQuota, redeemInvite, getPricingPlans, createOrder, mockPay,
  createShareForm, getTableFields
} from '@/services/api'

const state = ref({
  tableId: '',
  recordId: '',
  attachFieldId: '',
  loading: false,
})

// 用户信息（用于配额管理）
const userInfo = ref({
  openId: '',
  tenantKey: '',
})

// 使用个人空间上传（user_access_token）
const sessionId = ref('')
const authorized = ref(false)

// 配额相关
const quota = ref({
  remaining: 20,
  totalUsed: 0,
  inviteActive: false,
  inviteExpireAt: null,
})

// 弹窗状态
const showInviteDialog = ref(false)
const showRechargeDialog = ref(false)
const showShareFormDialog = ref(false)
const activeButton = ref('')  // 当前选中的按钮
const toastMessage = ref('')  // 自定义 Toast 消息
const toastType = ref('info') // Toast 类型
const inviteCode = ref('')
// 套餐列表（从 API 加载）
const pricingPlans = ref([])
const loadingPlans = ref(false)
const currentOrder = ref(null)

// 分享表单相关
const shareFormName = ref('')
const shareFormDesc = ref('')
const generatedShareUrl = ref('')

// 字段选择器相关
const availableFields = ref([])   // 可选字段列表
const selectedFields = ref([])    // 已选字段列表
const loadingFields = ref(false)  // 加载状态
const showFieldSelector = ref(false) // 是否显示字段选择步骤
const currentAppToken = ref('')   // 当前表格 app_token

// 监听器卸载函数
let offSelectionChange = null

// 格式化日期
function formatDate(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp * 1000)
  return date.toLocaleDateString('zh-CN')
}

// 检查是否可以签名
const canSign = computed(() => {
  return quota.value.inviteActive || quota.value.remaining > 0
})

// 检查是否有选中记录
const hasSelection = computed(() => {
  return !!state.value.recordId
})

async function init() {
  try {
    const selection = await bitable.base.getSelection()
    state.value.tableId = selection.tableId || ''
    state.value.recordId = selection.recordId || ''

    // 监听选中变化
    offSelectionChange = bitable.base.onSelectionChange((event) => {
      if (event.data.recordId) {
        state.value.recordId = event.data.recordId
        // 如果切换了表，也需要更新tableId
        if (event.data.tableId) {
          state.value.tableId = event.data.tableId
          // 重新获取字段信息（可能切换到了不同的表）
          refreshFieldInfo()
        }
      } else {
        state.value.recordId = ''
      }
    })

    if (!state.value.tableId) {
      showToast('请在多维表格中打开插件后再试', 'warning')
      return
    }

    await refreshFieldInfo()
    
    // 获取用户信息
    try {
      const bridgeInfo = await bitable.bridge.getUserInfo?.() || {}
      userInfo.value.openId = bridgeInfo.openId || 'anonymous'
      userInfo.value.tenantKey = bridgeInfo.tenantKey || 'anonymous'
    } catch {
      userInfo.value.openId = 'anonymous'
      userInfo.value.tenantKey = 'anonymous'
    }
    
    // 加载配额信息
    await loadQuota()
  } catch (e) {
    // 初始化错误仅在开发环境输出
    if (import.meta.env.DEV) console.error('[Init]', e)
  }
}

async function refreshFieldInfo() {
  if (!state.value.tableId) return
  try {
    const table = await bitable.base.getTableById(state.value.tableId)
    const fields = await table.getFieldMetaList()
    // 优先选择名称包含"签名/Signature"的附件字段，否则取第一个附件字段
    let attach = fields.find(f => (f.type === 'Attachment' || f.type === 17) && /签名|sign/i.test(f.name || ''))
    if (!attach) attach = fields.find(f => f.type === 'Attachment' || f.type === 17)
    state.value.attachFieldId = attach?.id || ''
  } catch (e) {
    if (import.meta.env.DEV) console.error('[Field]', e)
  }
}

async function loadQuota() {
  try {
    const data = await getQuota(userInfo.value.openId, userInfo.value.tenantKey)
    quota.value = {
      remaining: data.remaining || 0,
      totalUsed: data.total_used || 0,
      inviteActive: data.invite_active || false,
      inviteExpireAt: data.invite_expire_at || null,
    }
  } catch (e) {
    if (import.meta.env.DEV) console.warn('[Quota]', e)
  }
}

onMounted(init)

onUnmounted(() => {
  if (offSelectionChange) {
    offSelectionChange()
  }
})

async function startAuth() {
  try {
    const { auth_url } = await authStart()
    // 打开新窗口进行飞书用户授权
    const win = window.open(auth_url, '_blank', 'width=720,height=720')
    if (!win) {
      showToast('无法打开授权窗口，请检查浏览器弹窗设置', 'error', 3000)
      return
    }
    
    const handler = async (ev) => {
      if (!ev?.data || ev.data.type !== 'feishu-auth-done' || !ev.data.session_id) {
        return
      }
      sessionId.value = ev.data.session_id
      window.removeEventListener('message', handler)
      // 可选查询一次状态
      try {
        const st = await authStatus(sessionId.value)
        authorized.value = !!st.authorized
        if (authorized.value) {
          showToast('已授权，可将文件上传到个人空间', 'success')
        } else {
          showToast('授权状态异常，请重新授权', 'warning')
        }
      } catch (e) {
        if (import.meta.env.DEV) console.error('[Auth]', e)
        showToast('授权状态检查失败，但 session_id 已保存', 'warning')
      }
      if (win && !win.closed) win.close()
      activeButton.value = ''  // 授权完成后取消高亮
    }
    window.addEventListener('message', handler)
    
    // 设置超时，如果30秒内没有收到消息，提示用户
    setTimeout(() => {
      if (!authorized.value && !sessionId.value) {
        console.warn('[Auth] Timeout waiting for auth callback')
        showToast('授权超时，请检查授权窗口是否正常关闭', 'warning', 3000)
        activeButton.value = ''  // 超时后取消高亮
      }
    }, 30000)
    
    // 定时检查窗口是否关闭
    const checkWindowClosed = setInterval(() => {
      if (win && win.closed) {
        clearInterval(checkWindowClosed)
        activeButton.value = ''  // 窗口关闭后取消高亮
      }
    }, 500)
  } catch (e) {
    console.error('[Auth] Error:', e)
    showToast('打开授权页失败：' + (e?.message || e), 'error')
  }
}

async function onConfirm(blob) {
  if (!state.value.tableId) {
    showToast('未获取到表信息，请在多维表格环境中打开插件', 'warning')
    return
  }
  if (!state.value.attachFieldId) {
    showToast('当前表未检测到"附件/签名"字段', 'error', 2000)
    return
  }

  // 必须选中记录
  if (!state.value.recordId) {
    showToast('请先在表格中点击选择一行记录', 'warning')
    return
  }

  // 个人空间上传：需要完成授权
  if (!authorized.value || !sessionId.value) {
    showToast('请先点击上方"授权登录"，完成授权后再试', 'warning')
    return
  }
  
  // 检查配额
  if (!canSign.value) {
    ElMessage.warning('签名次数已用完，请充值或使用邀请码')
    showRechargeDialog.value = true
    return
  }

  try {
    state.value.loading = true
    
    const fileName = `signature_${Date.now()}.png`
    const table = await bitable.base.getTableById(state.value.tableId)
    
    // 直接使用 Field.createCell 方法（跳过后端上传，速度更快）
    const attachField = await table.getFieldById(state.value.attachFieldId)
    
    // 将 blob 转换为 File 对象
    const file = new File([blob], fileName, { type: 'image/png' })
    
    // 使用 Field 的 createCell 方法创建附件单元格
    const cell = await attachField.createCell(file)
    
    // 更新现有记录
    await table.setCellValue(state.value.attachFieldId, state.value.recordId, cell.val)
    ElMessage.success('签名完成')
    
    // 更新配额显示（不管是否消耗，都刷新一次）
    await loadQuota()
    
    // 异步备份到后端（不阻塞主流程）
    if (authorized.value && sessionId.value) {
      uploadSignature({
        blob,
        fileName,
        sessionId: sessionId.value,
        useUserToken: 1,
        folderToken: undefined,
      }).catch(() => {
        // 备份失败不影响主流程
      })
    }
    
    // 成功完成，直接返回
  } catch (e) {
    if (import.meta.env.DEV) console.error('[Upload]', e)
    const errorMsg = e?.response?.data?.detail || e?.message || String(e)
    showToast(`上传失败：${errorMsg}`, 'error', 3000)
  } finally {
    state.value.loading = false
  }
}

// 邀请码兑换
async function handleRedeemInvite() {
  if (!inviteCode.value.trim()) {
    ElMessage.warning('请输入邀请码')
    return
  }
  try {
    const result = await redeemInvite(inviteCode.value.trim(), userInfo.value.openId, userInfo.value.tenantKey)
    if (result.success) {
      ElMessage.success(`邀请码兑换成功！${result.benefit_days}天内可免费使用`)
      showInviteDialog.value = false
      inviteCode.value = ''
      await loadQuota()
    }
  } catch (e) {
    ElMessage.error('邀请码无效或已被使用')
  }
}

// 关闭所有弹窗（不清空 activeButton，由弹窗关闭事件处理）
function closeAllDialogs() {
  showInviteDialog.value = false
  showRechargeDialog.value = false
  showShareFormDialog.value = false
}

// 关闭弹窗时清空高亮
function onDialogClose() {
  activeButton.value = ''
}

// 显示居中 Toast
function showToast(msg, type = 'info', duration = 2000) {
  toastMessage.value = msg
  toastType.value = type
  setTimeout(() => {
    toastMessage.value = ''
  }, duration)
}

// 打开充值弹窗
async function openRechargeDialog() {
  closeAllDialogs()
  showRechargeDialog.value = true
  loadingPlans.value = true
  try {
    const plans = await getPricingPlans()
    if (plans && plans.length > 0) {
      pricingPlans.value = plans
    } else {
      showToast('加载套餐失败，请稍后重试', 'warning')
    }
  } catch (e) {
    showToast('加载套餐失败，请稍后重试', 'error')
    if (import.meta.env.DEV) console.error('[Pricing]', e)
  } finally {
    loadingPlans.value = false
  }
}

// 选择套餐并创建订单
async function selectPlan(plan) {
  try {
    const result = await createOrder(plan.id, userInfo.value.openId, userInfo.value.tenantKey)
    if (result.success) {
      currentOrder.value = result
      showToast(`订单已创建，金额：¥${(plan.price / 100).toFixed(2)}`, 'success')
    }
  } catch (e) {
    showToast('创建订单失败', 'error')
  }
}

// 模拟支付（测试用）
async function handleMockPay() {
  if (!currentOrder.value?.order_id) {
    showToast('请先选择套餐', 'warning')
    return
  }
  try {
    const result = await mockPay(currentOrder.value.order_id)
    if (result.success) {
      showToast(`支付成功！已增加 ${result.quota_added} 次签名额度`, 'success')
      showRechargeDialog.value = false
      currentOrder.value = null
      await loadQuota()
    }
  } catch (e) {
    showToast('支付失败', 'error')
  }
}

// 打开分享表单弹窗时加载字段
async function openShareFormDialog() {
  closeAllDialogs()
  showShareFormDialog.value = true
  showFieldSelector.value = false
  generatedShareUrl.value = ''
  shareFormName.value = ''
  shareFormDesc.value = ''
  selectedFields.value = []
  
  // 加载表格字段
  await loadTableFields()
}

// 加载多维表格字段列表
async function loadTableFields() {
  try {
    loadingFields.value = true
    const selection = await bitable.base.getSelection()
    currentAppToken.value = selection.baseId || ''
    
    if (!currentAppToken.value || !state.value.tableId) {
      showToast('无法获取表格信息', 'warning')
      return
    }
    
    const result = await getTableFields(
      currentAppToken.value,
      state.value.tableId,
      sessionId.value
    )
    
    if (result.success && result.fields) {
      availableFields.value = result.fields
    } else {
      availableFields.value = []
    }
  } catch (e) {
    console.error('加载字段失败:', e)
    showToast('加载字段列表失败', 'error')
    availableFields.value = []
  } finally {
    loadingFields.value = false
  }
}

// 切换字段选中状态
function toggleFieldSelection(field) {
  const idx = selectedFields.value.findIndex(f => f.field_id === field.field_id)
  if (idx >= 0) {
    selectedFields.value.splice(idx, 1)
  } else {
    selectedFields.value.push({ 
      ...field, 
      required: false 
    })
  }
}

// 检查字段是否已选中
function isFieldSelected(fieldId) {
  return selectedFields.value.some(f => f.field_id === fieldId)
}

// 切换必填状态
function toggleRequired(fieldId) {
  const field = selectedFields.value.find(f => f.field_id === fieldId)
  if (field) {
    field.required = !field.required
  }
}

// 进入字段选择步骤
function goToFieldSelector() {
  if (!shareFormName.value.trim()) {
    showToast('请输入表单名称', 'warning')
    return
  }
  showFieldSelector.value = true
}

// 返回基本信息步骤
function goBackToBasicInfo() {
  showFieldSelector.value = false
}

// 创建分享签名表单
async function handleCreateShareForm() {
  if (!shareFormName.value.trim()) {
    showToast('请输入表单名称', 'warning')
    return
  }
  
  // 检查是否已授权
  if (!authorized.value || !sessionId.value) {
    showToast('请先点击"授权"按钮完成飞书授权', 'warning')
    return
  }
  
  if (selectedFields.value.length === 0) {
    showToast('请至少选择一个字段', 'warning')
    return
  }
  
  try {
    // 查找签名字段（附件类型）
    const signatureField = selectedFields.value.find(f => f.input_type === 'attachment')
    
    const result = await createShareForm({
      name: shareFormName.value.trim(),
      description: shareFormDesc.value.trim() || null,
      app_token: currentAppToken.value,
      table_id: state.value.tableId,
      signature_field_id: signatureField?.field_id || null,
      fields: selectedFields.value,
      created_by: `${userInfo.value.openId}::${userInfo.value.tenantKey}`,
      session_id: sessionId.value
    })
    
    if (result.success) {
      const baseUrl = window.location.origin || 'http://localhost:5173'
      generatedShareUrl.value = `${baseUrl}/sign?id=${result.form_id}`
      
      if (result.has_auth) {
        showToast('分享表单创建成功！', 'success')
      } else {
        showToast('表单已创建，但授权信息保存失败', 'warning')
      }
    }
  } catch (e) {
    console.error('创建分享表单失败:', e)
    showToast('创建失败: ' + (e.response?.data?.detail || e.message), 'error')
  }
}

// 复制分享链接
function copyShareUrl() {
  if (!generatedShareUrl.value) return
  
  // 方案1: 使用 clipboard API
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(generatedShareUrl.value).then(() => {
      showToast('链接已复制到剪贴板', 'success')
    }).catch(() => {
      fallbackCopy(generatedShareUrl.value)
    })
  } else {
    // 方案2: 降级方案
    fallbackCopy(generatedShareUrl.value)
  }
}

// 降级复制方案
function fallbackCopy(text) {
  try {
    const textArea = document.createElement('textarea')
    textArea.value = text
    textArea.style.position = 'fixed'
    textArea.style.left = '-9999px'
    textArea.style.top = '-9999px'
    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()
    
    const successful = document.execCommand('copy')
    document.body.removeChild(textArea)
    
    if (successful) {
      showToast('链接已复制到剪贴板', 'success')
    } else {
      showToast('复制失败，请手动复制', 'error')
    }
  } catch (err) {
    showToast('复制失败，请手动复制', 'error')
  }
}

// 获取字段类型显示名称
function getFieldTypeName(inputType) {
  const typeNames = {
    'text': '文本',
    'number': '数字',
    'select': '单选',
    'multiselect': '多选',
    'date': '日期',
    'checkbox': '复选框',
    'phone': '电话',
    'email': '邮箱',
    'url': '链接',
    'attachment': '附件/签名'
  }
  return typeNames[inputType] || inputType
}
</script>

<template>
  <div class="app-container">
    <!-- 签字区域 -->
    <div class="main-card" :class="{ 'disabled-card': !hasSelection }">
      <div class="card-header">
        <div class="header-left">
          <svg class="header-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17 3a2.85 2.85 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
          </svg>
          <span class="header-title">签名区域</span>
        </div>
        <span class="status-chip" :class="{ 'status-ready': hasSelection }">
          {{ hasSelection ? '就绪' : '未选中' }}
        </span>
      </div>
      
      <div class="canvas-area">
        <SignaturePad @confirm="onConfirm" />
      </div>
      
      <!-- 未选中遮罩 -->
      <div class="overlay" v-if="!hasSelection">
        <div class="overlay-box">
          <svg class="overlay-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <path d="M9 9h.01M15 9h.01M9 15h6"/>
          </svg>
          <p class="overlay-text">请先选中表格中的一行</p>
        </div>
      </div>
      
      <div class="warning-bar" v-if="!state.attachFieldId">
        <svg class="warning-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/><path d="M12 8v4m0 4h.01"/>
        </svg>
        <span>未检测到附件字段，请新增名为"签名"的附件列</span>
      </div>
    </div>

    <!-- 操作栏 -->
    <div class="actions-row">
      <button class="action-btn" :class="{ active: activeButton === 'invite' }" @click="activeButton = 'invite'; closeAllDialogs(); showInviteDialog = true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-6"/>
          <path d="M12 12V3m0 0L8 7m4-4 4 4"/>
        </svg>
        <span>兑换码</span>
      </button>
      <button class="action-btn" :class="{ active: activeButton === 'auth' }" @click="activeButton = 'auth'; closeAllDialogs(); startAuth()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M12 2a10 10 0 0 0-6.88 17.23l1.15-2.88A7 7 0 1 1 19 12h-3l4 4 4-4h-3A10 10 0 0 0 12 2Z"/>
        </svg>
        <span>{{ authorized ? '已授权' : '授权' }}</span>
        <span class="dot" :class="{ 'dot-active': authorized }"></span>
      </button>
      <button class="action-btn" :class="{ active: activeButton === 'recharge' }" @click="activeButton = 'recharge'; openRechargeDialog()" v-if="!quota.inviteActive">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48 2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48 2.83-2.83"/>
        </svg>
        <span>充值</span>
      </button>
      <button class="action-btn" :class="{ active: activeButton === 'share' }" @click="activeButton = 'share'; openShareFormDialog()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><path d="M16 6l-4-4-4 4"/><path d="M12 2v13"/>
        </svg>
        <span>分享</span>
      </button>
    </div>

    <!-- 额度信息 -->
    <div class="quota-bar">
      <div class="quota-info" v-if="quota.inviteActive">
        <svg class="vip-icon" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2L9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61z"/>
        </svg>
        <span class="vip-text">VIP · {{ formatDate(quota.inviteExpireAt) }} 到期</span>
      </div>
      <div class="quota-info" v-else>
        <span class="quota-label">剩余额度</span>
        <span class="quota-count">{{ quota.remaining }}</span>
      </div>
    </div>
    
    <!-- 邀请码弹窗 -->
    <el-dialog v-model="showInviteDialog" width="92%" center :show-close="false" @close="onDialogClose">
      <template #header>
        <div class="dialog-header">
          <div class="dialog-icon invite-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20 12v10H4V12"/><path d="M2 7h20v5H2z"/><path d="M12 22V7"/><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"/><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/>
            </svg>
          </div>
          <div class="dialog-title-text">兑换邀请码</div>
          <button class="close-btn" @click="showInviteDialog = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12"/></svg>
          </button>
        </div>
      </template>
      <div class="dialog-content">
        <p class="dialog-subtitle">输入邀请码，解锁一年无限签名</p>
        <el-input v-model="inviteCode" placeholder="请输入邀请码" size="large" class="styled-input" />
        <el-button type="primary" @click="handleRedeemInvite" size="large" class="main-btn">
          立即兑换
        </el-button>
      </div>
    </el-dialog>
    
    <!-- 充值弹窗 -->
    <el-dialog v-model="showRechargeDialog" width="92%" center :show-close="false" @close="onDialogClose">
      <template #header>
        <div class="dialog-header">
          <div class="dialog-icon recharge-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48 2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48 2.83-2.83"/>
            </svg>
          </div>
          <div class="dialog-title-text">补充额度</div>
          <button class="close-btn" @click="showRechargeDialog = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12"/></svg>
          </button>
        </div>
      </template>
      <div class="dialog-content">
        <p class="dialog-subtitle">选择适合你的套餐</p>
        <div class="pricing-grid">
          <div v-for="plan in pricingPlans" :key="plan.id" class="plan-card" 
               :class="{ selected: currentOrder?.plan_id === plan.id }"
               @click="selectPlan(plan)">
            <div class="hot-badge" v-if="plan.count >= 100">热门</div>
            <div class="plan-amount">{{ plan.count }}</div>
            <div class="plan-unit">次签名</div>
            <div class="plan-divider"></div>
            <div class="plan-price-row">
              <span class="price-symbol">¥</span>
              <span class="price-value">{{ (plan.price / 100).toFixed(0) }}</span>
            </div>
            <div class="plan-avg">约 ¥{{ (plan.price / 100 / plan.count).toFixed(2) }}/次</div>
            <div class="selected-mark" v-if="currentOrder?.plan_id === plan.id">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6 9 17l-5-5"/></svg>
            </div>
          </div>
        </div>
        
        <el-button type="success" size="large" @click="handleMockPay" :disabled="!currentOrder" class="pay-btn">
          <svg class="wechat-svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.17 4.203 3.002 5.55a.59.59 0 0 1 .213.665l-.39 1.48c-.019.07-.048.141-.048.213 0 .163.13.295.29.295a.32.32 0 0 0 .167-.054l1.903-1.114a.86.86 0 0 1 .717-.098 10.16 10.16 0 0 0 2.837.403c.275 0 .547-.012.816-.031a5.91 5.91 0 0 1-.24-1.65c0-3.575 3.375-6.477 7.541-6.477.385 0 .764.027 1.136.078-.635-3.586-4.416-6.602-8.753-6.602zM12.445 19.031c2.63 0 4.778-.732 6.44-1.95a11.08 11.08 0 0 0 1.86.146c.636 0 1.262-.063 1.87-.17l1.255.733a.21.21 0 0 0 .11.035.193.193 0 0 0 .19-.189c0-.046-.018-.091-.03-.137l-.256-.972a.383.383 0 0 1 .14-.433c1.218-.878 1.976-2.228 1.976-3.72 0-2.666-2.69-4.83-6.014-4.83-3.325 0-6.015 2.164-6.015 4.83 0 2.667 2.69 4.831 6.015 4.831-.002-.002 0 1.826 0 1.826z"/>
          </svg>
          微信支付
        </el-button>
        <p class="secure-note">
          <svg class="lock-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
          安全支付 · 即时到账
        </p>
      </div>
    </el-dialog>
    
    <!-- 分享表单弹窗 -->
    <el-dialog v-model="showShareFormDialog" width="92%" center :show-close="false" @close="onDialogClose">
      <template #header>
        <div class="dialog-header">
          <div class="dialog-icon share-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><path d="M16 6l-4-4-4 4"/><path d="M12 2v13"/>
            </svg>
          </div>
          <div class="dialog-title-text">{{ showFieldSelector ? '选择表单字段' : '创建分享表单' }}</div>
          <button class="close-btn" @click="showShareFormDialog = false; generatedShareUrl = ''">
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
            <button class="copy-btn" @click="copyShareUrl">复制</button>
          </div>
          <p class="result-hint">分享此链接给外部用户，他们可以直接填写表单</p>
        </div>
        
        <!-- 步骤1：基本信息 -->
        <div v-else-if="!showFieldSelector">
          <p class="dialog-subtitle">创建一个可分享的表单，外部用户无需登录即可填写</p>
          <el-input v-model="shareFormName" placeholder="请输入表单名称" size="large" class="styled-input" />
          <el-input v-model="shareFormDesc" placeholder="表单描述（可选）" size="large" class="styled-input" style="margin-top: 12px;" />
          <el-button type="primary" @click="goToFieldSelector" size="large" class="main-btn">
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
            <el-button type="primary" @click="handleCreateShareForm" size="large" :disabled="selectedFields.length === 0">
              创建表单
            </el-button>
          </div>
        </div>
      </div>
    </el-dialog>
    
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

<style scoped>
/* 简洁设计系统 */
.app-container {
  padding: 16px;
  background: #f5f5f7;
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  color: #1d1d1f;
}

/* 主卡片 */
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

.canvas-area {
  background: #fafafa;
}

/* 遮罩 */
.disabled-card .canvas-area {
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

/* 操作栏 */
.actions-row {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 12px;
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  font-size: 13px;
  color: #1d1d1f;
  cursor: pointer;
  transition: all 0.15s;
  position: relative;
}

.action-btn:hover {
  background: #fafafa;
  border-color: #d1d1d6;
}

.action-btn.active {
  background: #007aff;
  border-color: #007aff;
  color: #fff;
}

.action-btn.active:hover {
  background: #0066d6;
}

.action-btn svg {
  width: 16px;
  height: 16px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #c7c7cc;
}

.dot-active {
  background: #34c759;
}

/* 额度栏 */
.quota-bar {
  margin-top: 12px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}

.quota-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.vip-icon {
  width: 16px;
  height: 16px;
  color: #ff9500;
}

.vip-text {
  font-size: 13px;
  font-weight: 500;
  color: #ff9500;
}

.quota-label {
  font-size: 12px;
  color: #86868b;
}

.quota-count {
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
  margin-left: auto;
}

/* ========== 弹窗样式 ========== */

/* 弹窗头部 */
.dialog-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 16px;
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
  color: #fff;
}

.dialog-icon svg {
  width: 24px;
  height: 24px;
}

.invite-icon {
  background: #f5f5f7;
  color: #ff9500;
}

.recharge-icon {
  background: #f5f5f7;
  color: #007aff;
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

/* 输入框样式优化 */
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

.styled-input :deep(.el-input__inner::placeholder) {
  color: #aeaeb2;
}

.main-btn {
  width: 100%;
  height: 48px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
}

/* ========== 套餐卡片 ========== */
.pricing-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 24px;
}

.plan-card {
  background: #fff;
  border: 2px solid #e5e5ea;
  border-radius: 16px;
  padding: 20px 12px;
  text-align: center;
  cursor: pointer;
  position: relative;
  transition: all 0.2s ease;
}

.plan-card:hover {
  border-color: #007aff;
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 122, 255, 0.12);
}

.plan-card.selected {
  border-color: #007aff;
  background: linear-gradient(180deg, #f0f7ff 0%, #fff 100%);
}

.hot-badge {
  position: absolute;
  top: -1px;
  right: -1px;
  background: linear-gradient(135deg, #ff3b30 0%, #ff6b52 100%);
  color: #fff;
  font-size: 10px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 0 14px 0 10px;
}

.plan-amount {
  font-size: 32px;
  font-weight: 700;
  color: #1d1d1f;
  line-height: 1;
}

.plan-unit {
  font-size: 12px;
  color: #86868b;
  margin-top: 4px;
}

.plan-divider {
  width: 40px;
  height: 2px;
  background: #e5e5ea;
  margin: 12px auto;
  border-radius: 1px;
}

.plan-price-row {
  color: #007aff;
  margin-bottom: 4px;
}

.price-symbol {
  font-size: 14px;
  font-weight: 500;
}

.price-value {
  font-size: 24px;
  font-weight: 700;
}

.plan-avg {
  font-size: 11px;
  color: #aeaeb2;
}

.selected-mark {
  position: absolute;
  bottom: 8px;
  right: 10px;
  width: 22px;
  height: 22px;
  background: #007aff;
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

/* ========== 支付按钮 ========== */
.pay-btn {
  width: 100%;
  height: 52px;
  border-radius: 14px;
  font-size: 17px;
  font-weight: 600;
  background: linear-gradient(135deg, #07c160 0%, #06ad56 100%);
  border: none;
  box-shadow: 0 4px 16px rgba(7, 193, 96, 0.3);
}

.pay-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(7, 193, 96, 0.4);
}

.pay-btn:disabled {
  background: #c7c7cc;
  box-shadow: none;
}

.wechat-svg {
  width: 20px;
  height: 20px;
  margin-right: 8px;
}

.secure-note {
  text-align: center;
  margin-top: 16px;
  font-size: 12px;
  color: #aeaeb2;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.lock-svg {
  width: 14px;
  height: 14px;
}

.selected-mark svg {
  width: 12px;
  height: 12px;
}

.close-btn:hover {
  background: #e5e5e7;
  color: #1d1d1f;
}

/* Element Plus 弹窗样式覆盖 */
:deep(.el-dialog) {
  border-radius: 16px;
  overflow: hidden;
}

:deep(.el-dialog__header) {
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
  margin-right: 0;
}

:deep(.el-dialog__title) {
  font-size: 16px;
  font-weight: 600;
  color: #1d1d1f;
}

:deep(.el-dialog__body) {
  padding: 10px 20px 20px;
}

:deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #e5e5e5 inset;
}

:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #c7c7cc inset;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px #007aff inset;
}

:deep(.el-button--primary) {
  background: #007aff;
  border-color: #007aff;
}

:deep(.el-button--primary:hover) {
  background: #0066d6;
  border-color: #0066d6;
}

:deep(.el-button--success) {
  background: #07c160;
  border-color: #07c160;
}

:deep(.el-button.is-round) {
  border-radius: 22px;
}

/* 分享表单弹窗 */
.share-icon {
  background: #f5f5f7;
  color: #34c759;
}

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

/* ========== 字段选择器样式 ========== */
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
}

/* 居中 Toast 提示 */
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
}

.toast-icon {
  width: 40px;
  height: 40px;
}

.toast-icon.success { color: #34c759; }
.toast-icon.error { color: #ff3b30; }
.toast-icon.warning { color: #ff9500; }
.toast-icon.info { color: #007aff; }

.toast-card p {
  margin: 0;
  font-size: 15px;
  color: #fff;
  text-align: center;
  line-height: 1.5;
}

/* Toast 动画 */
.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: all 0.3s ease;
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: scale(0.9);
}
</style>

