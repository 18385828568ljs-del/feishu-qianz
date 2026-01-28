<!--
  表单主组件
  整合所有子组件，管理全局状态
  仅支持签名模式
-->
<script setup>
import { bitable } from '@lark-base-open/js-sdk'
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadSignature, consumeQuota } from '@/services/api'

// 导入 Composables
import { useToast } from '@/composables/useToast'
import { useAuth } from '@/composables/useAuth'
import { useQuota } from '@/composables/useQuota'
import { useBaseToken } from '@/composables/useBaseToken'

// 导入子组件
import SignatureCard from './SignatureCard.vue'
import ActionBar from './ActionBar.vue'
import QuotaBar from './QuotaBar.vue'
import InviteDialog from './InviteDialog.vue'
import RechargeDialog from './RechargeDialog.vue'
import ShareFormDialog from './ShareFormDialog.vue'
import BaseTokenDialog from './BaseTokenDialog.vue'
import ToastNotification from '../common/ToastNotification.vue'

// 使用 Composables
const { toastMessage, toastType, showToast } = useToast()
const { authorized, startAuth } = useAuth()
const { quota, canSign, loadQuota } = useQuota()
const { hasBaseToken } = useBaseToken()

// 表格状态
const state = ref({
  tableId: '',
  recordId: '',
  attachFieldId: '',
  loading: false,
})

// 用户信息
const userInfo = ref({
  openId: '',
  tenantKey: '',
})

// 当前 app_token
const currentAppToken = ref('')

// 弹窗状态
const showInviteDialog = ref(false)
const showRechargeDialog = ref(false)
const showShareFormDialog = ref(false)
const showBaseTokenDialog = ref(false)
const activeButton = ref('')

// 监听器卸载函数
let offSelectionChange = null

// 计算属性
const hasSelection = computed(() => !!state.value.recordId)
const userKey = computed(() => `${userInfo.value.openId}::${userInfo.value.tenantKey}`)

// 初始化
async function init() {
  try {
    const selection = await bitable.base.getSelection()
    
    state.value.tableId = selection.tableId || ''
    state.value.recordId = selection.recordId || ''
    currentAppToken.value = selection.baseId || ''

    // 如果初始化时就有选中的字段，检查是否是附件字段
    if (selection.fieldId && selection.tableId) {
      try {
        const table = await bitable.base.getTableById(selection.tableId)
        const field = await table.getFieldMetaById(selection.fieldId)
        if (field && (field.type === 'Attachment' || field.type === 17)) {
          state.value.attachFieldId = selection.fieldId
          // 初始选中附件字段
        }
      } catch (e) {
        console.warn('[Init] 获取初始字段信息失败:', e)
      }
    }

    // 监听选中变化
    offSelectionChange = bitable.base.onSelectionChange(async (event) => {
      
      if (event.data.recordId) {
        state.value.recordId = event.data.recordId
        if (event.data.tableId) {
          state.value.tableId = event.data.tableId
          // 只有当tableId变化时才重新查找默认字段
          // await refreshFieldInfo()  // 暂时注释，避免覆盖用户选择
        }
        
        // 检测选中的字段类型
        if (event.data.fieldId) {
          try {
            const table = await bitable.base.getTableById(state.value.tableId)
            const field = await table.getFieldMetaById(event.data.fieldId)

            
            // 如果选中的是附件字段，则使用该字段作为签名目标
            if (field && (field.type === 'Attachment' || field.type === 17)) {
              state.value.attachFieldId = event.data.fieldId
              // 使用用户选中的附件字段
            } else {
              // 如果选中的不是附件字段，给出提示
              showToast('请选择附件/签名列后再进行签名！', 'warning', 2000)
            }
          } catch (e) {
            console.error('[Selection] 获取字段信息失败:', e)
          }
        }
      } else {
        state.value.recordId = ''
      }
    })

    if (!state.value.tableId) {
      showToast('请在多维表格中打开插件后再试', 'warning')
      return
    }

    // 如果初始化时没有选中附件字段，才执行自动查找
    if (!state.value.attachFieldId) {
      await refreshFieldInfo()
    }
    
    // 获取用户信息
    try {
      const bridgeInfo = await bitable.bridge.getUserInfo?.() || {}
      userInfo.value.openId = bridgeInfo.openId || 'anonymous'
      userInfo.value.tenantKey = bridgeInfo.tenantKey || 'anonymous'
    } catch {
      userInfo.value.openId = 'anonymous'
      userInfo.value.tenantKey = 'anonymous'
    }
    
    // 加载配额
    await loadQuota(userInfo.value.openId, userInfo.value.tenantKey)
  } catch (e) {
    console.error(e)
  }
}

// 刷新字段信息（仅查找签名字段）
async function refreshFieldInfo() {
  if (!state.value.tableId) return
  try {
    const table = await bitable.base.getTableById(state.value.tableId)
    const fields = await table.getFieldMetaList()
    
    // 优先找"签名"字段，否则找第一个附件字段
    let attach = fields.find(f => (f.type === 'Attachment' || f.type === 17) && /签名|sign/i.test(f.name || ''))
    if (!attach) attach = fields.find(f => f.type === 'Attachment' || f.type === 17)
    state.value.attachFieldId = attach?.id || ''
  } catch (e) {
    console.error('Failed to refresh field info:', e)
  }
}

// 签名确认
async function onConfirm(blob) {
  await uploadToField(blob, `signature_${Date.now()}.png`, 'image/png')
}

// 上传到字段
async function uploadToField(fileOrBlob, fileName, mimeType) {
  if (!state.value.tableId) {
    showToast('未获取到表信息，请在多维表格环境中打开插件', 'warning')
    return
  }
  if (!state.value.attachFieldId) {
    showToast('请选择一个附件字段', 'error', 2000)
    return
  }
  if (!state.value.recordId) {
    showToast('请先在表格中点击选择一行记录', 'warning')
    return
  }
  if (!authorized.value) {
    showToast('请先点击上方“授权码”按钮，配置您的授权码', 'warning')
    return
  }
  if (!canSign.value) {
    ElMessage.warning('使用次数已用完，请充值或使用邀请码')
    showRechargeDialog.value = true
    return
  }

  try {
    state.value.loading = true
    
    const table = await bitable.base.getTableById(state.value.tableId)
    const attachField = await table.getFieldById(state.value.attachFieldId)
    
    // 创建 File 对象
    let file
    if (fileOrBlob instanceof File) {
      file = fileOrBlob
    } else {
      file = new File([fileOrBlob], fileName, { type: mimeType })
    }
    
    const cell = await attachField.createCell(file)
    
    await table.setCellValue(state.value.attachFieldId, state.value.recordId, cell.val)
    
    // 消耗配额（非 VIP 用户需要扣减）
    if (!quota.value.inviteActive) {
      try {
        await consumeQuota(userInfo.value.openId, userInfo.value.tenantKey, 'local_upload', fileName)
      } catch (err) {
        console.warn('[Quota] Failed to consume quota:', err)
      }
    }
    
    showToast('签名成功！', 'success', 2000)
    
    await loadQuota(userInfo.value.openId, userInfo.value.tenantKey)
    
    // 异步备份（带上用户信息）
    if (authorized.value) {
      uploadSignature({
        blob: fileOrBlob,
        fileName,
        openId: userInfo.value.openId,
        tenantKey: userInfo.value.tenantKey,
      }).catch(err => console.warn('[Backup] Backup failed:', err))
    }
  } catch (e) {
    console.error('[Upload] Error:', e)
    const errorMsg = e?.response?.data?.detail || e?.message || String(e)
    showToast(`上传失败：${errorMsg}`, 'error', 3000)
  } finally {
    state.value.loading = false
  }
}

// 操作栏事件处理
function handleInvite() {
  closeAllDialogs()
  showInviteDialog.value = true
}

function handleAuth() {
  closeAllDialogs()
  showBaseTokenDialog.value = true
}

function handleRecharge() {
  closeAllDialogs()
  showRechargeDialog.value = true
}

function handleShare() {
  closeAllDialogs()
  showShareFormDialog.value = true
}

function closeAllDialogs() {
  showInviteDialog.value = false
  showRechargeDialog.value = false
  showShareFormDialog.value = false
  showBaseTokenDialog.value = false
}

function handleBaseToken() {
  closeAllDialogs()
  showBaseTokenDialog.value = true
}

function onDialogClose() {
  activeButton.value = ''
}

// 处理 Toast 事件
function handleToast(event) {
  showToast(event.message, event.type, event.duration || 2000)
}

// 刷新配额
async function refreshQuota() {
  await loadQuota(userInfo.value.openId, userInfo.value.tenantKey)
}

onMounted(init)

onUnmounted(() => {
  if (offSelectionChange) {
    offSelectionChange()
  }
})
</script>

<template>
  <div class="app-container">
    <!-- 签名区域（仅签名模式） -->
    <SignatureCard 
      :has-selection="hasSelection"
      :has-attach-field="!!state.attachFieldId"
      mode="signature"
      field-name="签名区域"
      @confirm="onConfirm"
    />

    <!-- 操作栏 -->
    <ActionBar 
      :authorized="authorized"
      :active-button="activeButton"
      :show-recharge-button="!quota.inviteActive"
      @update:active-button="activeButton = $event"
      @invite="handleInvite"
      @auth="handleAuth"
      @recharge="handleRecharge"
      @share="handleShare"
    />

    <!-- 额度信息 -->
    <QuotaBar :quota="quota" />
    
    <!-- 邀请码弹窗 -->
    <InviteDialog 
      v-model="showInviteDialog"
      :user-info="userInfo"
      @close="onDialogClose"
      @success="refreshQuota"
      @toast="handleToast"
    />
    
    <!-- 充值弹窗 -->
    <RechargeDialog 
      v-model="showRechargeDialog"
      :user-info="userInfo"
      :quota-info="quota"
      @close="onDialogClose"
      @success="refreshQuota"
      @toast="handleToast"
    />
    
    <!-- 分享表单弹窗 -->
    <ShareFormDialog 
      v-model="showShareFormDialog"
      :app-token="currentAppToken"
      :table-id="state.tableId"
      :user-key="userKey"
      @close="onDialogClose"
      @toast="handleToast"
    />

    <!-- 授权码配置弹窗 -->
    <BaseTokenDialog 
      v-model="showBaseTokenDialog"
      @close="onDialogClose"
      @saved="() => showToast('授权码已保存', 'success')"
    />

    <!-- Toast 通知 -->
    <ToastNotification :message="toastMessage" :type="toastType" />
  </div>
</template>

<style scoped>
.app-container {
  padding: 16px;
  background: #f5f5f7;
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
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

:deep(.el-dialog__body) {
  padding: 10px 20px 20px;
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
</style>
