<!--
  表单主组件
  整合所有子组件，管理全局状态
  仅支持签名模式
-->
<script setup>
import { bitable } from '@lark-base-open/js-sdk'
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { uploadSignature, consumeQuota, initUser } from '@/services/api'

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
import BatchSelectDialog from './BatchSelectDialog.vue'

// 使用 Composables
const { toastMessage, toastType, showToast } = useToast()
const { authorized, startAuth } = useAuth()
const { quota, canSign, loadQuota } = useQuota()
const { hasBaseToken, setCurrentAppToken } = useBaseToken()

// 表格状态
const state = ref({
  tableId: '',
  recordId: '',
  attachFieldId: '',
  loading: false,
})

// 用户信息
const userOpenId = ref('')

// 当前 app_token
const currentAppToken = ref('')

// 弹窗状态
const showInviteDialog = ref(false)
const showRechargeDialog = ref(false)
const showShareFormDialog = ref(false)
const showBaseTokenDialog = ref(false)
const showBatchSelectDialog = ref(false) // 批量选择弹窗
const batchCandidateRecords = ref([]) // 待选记录列表
const batchSelectLoading = ref(false)
const currentBatchBlob = ref(null) // 暂存的签名Blob
const activeButton = ref('')

// 批量操作进度状态
const showBatchProgressDialog = ref(false)
const batchProgress = ref({ current: 0, total: 0 })
const batchCancelled = ref(false)

// 监听器卸载函数
let offSelectionChange = null

// 计算属性
const hasSelection = computed(() => !!state.value.recordId)

// 生成设备指纹
function generateFingerprint() {
  const components = [
    navigator.userAgent,
    navigator.language,
    screen.width + 'x' + screen.height,
    screen.colorDepth,
    new Date().getTimezoneOffset(),
    !!window.sessionStorage,
    !!window.localStorage
  ]
  
  const fingerprint = components.join('|')
  
  // 简单的哈希函数
  let hash = 0
  for (let i = 0; i < fingerprint.length; i++) {
    const char = fingerprint.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash
  }
  
  return 'fp_' + Math.abs(hash).toString(36)
}

// 初始化
async function init() {
  try {
    const selection = await bitable.base.getSelection()
    
    state.value.tableId = selection.tableId || ''
    state.value.recordId = selection.recordId || ''
    currentAppToken.value = selection.baseId || ''
    
    // 设置当前表格的 app_token，用于获取对应的授权码
    if (currentAppToken.value) {
      setCurrentAppToken(currentAppToken.value)
    }

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
              // 如果选中的不是附件字段，清空附件字段ID并给出提示
              state.value.attachFieldId = ''
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
    
    // 获取用户信息（从飞书SDK）
    let openId = null
    let tenantKey = null
    
    try {
      // 检查是否在飞书环境中
      if (!bitable || !bitable.bridge || !bitable.bridge.getUserInfo) {
        console.warn('[Init] Not in Feishu environment, using development mode')
        
        // 开发模式：使用模拟数据
        if (import.meta.env.DEV) {
          openId = 'dev_user_' + Math.random().toString(36).substring(2, 10)
          tenantKey = 'dev_tenant_' + Math.random().toString(36).substring(2, 10)
          console.log('[Init] Development mode - using mock user:', { openId, tenantKey })
        } else {
          // 生产环境：必须在飞书中打开
          ElMessageBox.alert(
            '请在飞书客户端中打开此插件\n\n此插件必须在飞书多维表格中使用，无法在浏览器中直接访问。',
            '环境错误',
            {
              confirmButtonText: '我知道了',
              type: 'error',
              showClose: false,
            }
          )
          return
        }
      } else {
        // 正常模式：从飞书SDK获取
        const info = await bitable.bridge.getUserInfo()
        console.log('[Init] getUserInfo result:', info)
        
        if (info) {
          openId = info.userId || info.openId
          tenantKey = info.tenantKey
        }
      }
      
      // 验证必须字段
      if (!openId || !tenantKey) {
        const missingFields = []
        if (!openId) missingFields.push('用户ID')
        if (!tenantKey) missingFields.push('租户Key')
        
        const errorMsg = `无法获取${missingFields.join('和')}，请确保：\n1. 在飞书客户端中打开此插件\n2. 已登录飞书账号\n3. 拥有该多维表格的访问权限\n\n调试信息：\n- openId: ${openId || '未获取'}\n- tenantKey: ${tenantKey || '未获取'}`
        
        ElMessageBox.alert(errorMsg, '身份验证失败', {
          confirmButtonText: '我知道了',
          type: 'error',
          showClose: false,
        })
        
        console.error('[Init] Missing required user info:', { openId, tenantKey })
        return
      }

      console.log('[Init] User identity verified:', {
        openId: openId.substring(0, 8) + '***',
        tenantKey: tenantKey.substring(0, 8) + '***'
      })

      // 保存用户ID用于显示
      userOpenId.value = openId
      console.log('[Init] userOpenId set to:', userOpenId.value)

      // =========================================================
      // 核心流程：JWT Token 初始化
      // =========================================================
      
      // 检查是否已有有效的 Token
      const existingToken = localStorage.getItem('feishu_plugin_jwt_token')
      const tokenExpiry = localStorage.getItem('feishu_plugin_jwt_expiry')
      
      let needInit = true
      if (existingToken && tokenExpiry) {
        const expiryTime = parseInt(tokenExpiry)
        const now = Date.now()
        // 如果 token 还有超过1小时有效期，则不需要重新初始化
        if (expiryTime > now + 3600000) {
          console.log('[Init] Using existing valid token')
          needInit = false
        }
      }
      
      if (needInit) {
        console.log('[Init] Initializing user and obtaining JWT token...')
        
        // 生成设备指纹
        const fingerprint = generateFingerprint()
        
        try {
          // 调用后端初始化接口
          const initResult = await initUser(openId, tenantKey, fingerprint)
          
          // 保存 JWT Token
          localStorage.setItem('feishu_plugin_jwt_token', initResult.token)
          
          // 保存过期时间（当前时间 + expires_in 秒）
          const expiryTime = Date.now() + (initResult.expires_in * 1000)
          localStorage.setItem('feishu_plugin_jwt_expiry', expiryTime.toString())
          
          console.log('[Init] JWT token obtained successfully, expires in:', initResult.expires_in, 'seconds')
          
        } catch (error) {
          console.error('[Init] Failed to initialize user:', error)
          
          // 如果初始化失败，显示错误提示
          ElMessageBox.alert(
            '用户初始化失败，请刷新页面重试。如果问题持续存在，请联系管理员。',
            '初始化失败',
            {
              confirmButtonText: '刷新页面',
              type: 'error',
              showClose: false,
              callback: () => {
                window.location.reload()
              }
            }
          )
          
          throw error
        }
      }

    } catch (e) {
      console.error('[Init] Fatal error getting user info:', e)
      // 阻止继续执行
      return
    }
    
    // 加载配额信息
    await loadQuota()
  } catch (e) {
    console.error('[Init] Initialization failed:', e)
    showToast('插件初始化失败，请刷新后重试', 'error')
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
        await consumeQuota('local_upload', fileName)
      } catch (err) {
        console.warn('[Quota] Failed to consume quota:', err)
      }
    }
    
    showToast('签名成功！', 'success', 2000)
    
    await loadQuota()
    
    // 异步备份
    if (authorized.value) {
      uploadSignature({
        blob: fileOrBlob,
        fileName,
        folderToken: state.value.attachFieldId, // 使用字段ID作为文件夹标识
        appToken: currentAppToken.value
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

// 批量签名确认
// 批量签名确认
async function onBatchConfirm(blob) {
  if (!state.value.tableId || !state.value.attachFieldId) {
    showToast('未获取到表信息或附件字段', 'warning')
    return
  }
  if (!authorized.value) {
    showToast('请先点击上方"授权码"按钮，配置您的授权码', 'warning')
    return
  }
  
  // 检查额度
  if (!canSign.value) {
    showToast('您的额度已用完，无法执行批量操作', 'error')
    showRechargeDialog.value = true
    return
  }

  try {
    batchSelectLoading.value = true
    const table = await bitable.base.getTableById(state.value.tableId)
    
    // 获取当前视图（优先使用视图下的记录，保持筛选结果）
    const selection = await bitable.base.getSelection()
    let recordIdList = []
    let isViewOrder = false
    
    if (selection && selection.viewId) {
      try {
        const view = await table.getView(selection.viewId)
        recordIdList = await view.getVisibleRecordIdList()
        isViewOrder = true
      } catch (e) {
        console.warn('获取视图失败', e)
      }
    } 
    
    // 如果获取视图失败，尝试使用第一个视图
    if (!isViewOrder) {
        try {
            const viewList = await table.getViewList()
            if (viewList.length > 0) {
               const firstView = viewList[0]
               recordIdList = await firstView.getVisibleRecordIdList()
               console.log('Using first view as fallback')
            } else {
               recordIdList = await table.getRecordIdList()
            }
        } catch (e) {
            recordIdList = await table.getRecordIdList()
        }
    }
    
    // 如果还是没有获取到，或者回退到了全表，提示用户
    // 其实 getRecordIdList 往往是乱序的，所以我们尽量避免
    
    if (recordIdList.length === 0) {
      batchSelectLoading.value = false
      showToast('当前视图中没有记录', 'warning')
      return
    }

    // 限制加载数量防止卡顿
    const MAX_LOAD = 500
    const targetIds = recordIdList.slice(0, MAX_LOAD)
    
    // 生成序号名称 (记录条1, 记录条2...)
    const loadedRecords = targetIds.map((rid, index) => ({
      id: rid, 
      name: `记录条${index + 1}`
    }))
    
    batchCandidateRecords.value = loadedRecords
    
    // 暂存 Blob
    currentBatchBlob.value = blob
    
    // 打开选择弹窗
    batchSelectLoading.value = false
    showBatchSelectDialog.value = true

  } catch (e) {
    batchSelectLoading.value = false
    console.error('Batch Prepare Error:', e)
    showToast('准备批量数据失败', 'error')
  }
}

// 处理选择完成
function handleBatchSelectionConfirmed(selectedRecordIds) {
  if (!selectedRecordIds || selectedRecordIds.length === 0) return
  
  // 再次检查额度是否足够
  if (!quota.value.inviteActive && !quota.value.isUnlimited) {
      if (quota.value.remaining < selectedRecordIds.length) {
          ElMessage.error(`您的剩余额度 (${quota.value.remaining}) 不足于支付本次批量操作 (${selectedRecordIds.length} 条)`)
          showRechargeDialog.value = true
          return
      }
  }
  
  executeBatchFill(selectedRecordIds, currentBatchBlob.value)
}

// 执行批量填充
async function executeBatchFill(recordIdList, blob) {
  try {
    // 重置状态
    batchCancelled.value = false
    batchProgress.value = { current: 0, total: recordIdList.length }
    showBatchProgressDialog.value = true

    state.value.loading = true
    const table = await bitable.base.getTableById(state.value.tableId)
    
    const fileName = `signature_batch_${Date.now()}.png`
    const file = new File([blob], fileName, { type: 'image/png' })
    
    const attachField = await table.getFieldById(state.value.attachFieldId)
    const cell = await attachField.createCell(file)
    
    let successCount = 0
    let failCount = 0
    
    // 批量填充
    for (let i = 0; i < recordIdList.length; i++) {
        // 检查是否取消
        if (batchCancelled.value) {
            break
        }

        try {
            await table.setCellValue(state.value.attachFieldId, recordIdList[i], cell.val)
            successCount++
        } catch (e) {
            console.error(`[Batch] Failed to fill record ${recordIdList[i]}:`, e)
            failCount++
        }
        
        // 更新进度
        batchProgress.value.current = i + 1
    }
    
    state.value.loading = false
    showBatchProgressDialog.value = false
    
    // 消耗配额（批量操作按成功次数计算）
    if (!quota.value.inviteActive && successCount > 0) {
      try {
        await consumeQuota('batch_upload', 'batch_records', successCount)
      } catch (err) {
        console.warn('[Quota] Failed to consume quota:', err)
      }
    }
    
    // 显示结果摘要
    if (batchCancelled.value) {
      showToast(`批量填充已取消！已完成 ${successCount} 行`, 'info', 3000)
    } else if (failCount > 0) {
      showToast(`批量填充完成！成功 ${successCount} 行，失败 ${failCount} 行`, 'warning', 3000)
    } else {
      showToast(`批量填充成功！已填充 ${successCount} 行`, 'success', 3000)
    }
    
    await loadQuota()
    
    // 异步备份
    if (authorized.value) {
      uploadSignature({
        blob,
        fileName,
        folderToken: state.value.attachFieldId,
        hasQuota: true, // 批量操作已扣除配额，上传时不需再次扣除
        appToken: currentAppToken.value
      }).catch(err => console.warn('[Backup] Backup failed:', err))
    }
  } catch (e) {
    state.value.loading = false
    showBatchProgressDialog.value = false
    if (e !== false) {
      console.error('[Batch] Error:', e)
      const errorMsg = e?.response?.data?.detail || e?.message || String(e)
      showToast(`批量填充失败：${errorMsg}`, 'error', 3000)
    }
  }
}

// 刷新配额
async function refreshQuota() {
  await loadQuota()
}

// 取消批量操作
function cancelBatchOperation() {
  batchCancelled.value = true
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
      :user-id="userOpenId"
      mode="signature"
      field-name="签名区域"
      @confirm="onConfirm"
      @batch-confirm="onBatchConfirm"
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
      @close="onDialogClose"
      @success="refreshQuota"
      @toast="handleToast"
    />
    
    <!-- 充值弹窗 -->
    <RechargeDialog 
      v-model="showRechargeDialog"
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
      :app-token="currentAppToken"
      @close="onDialogClose"
      @saved="() => showToast('授权码已保存', 'success')"
    />

    <!-- 批量记录选择弹窗 -->
    <BatchSelectDialog
      v-model="showBatchSelectDialog"
      :records="batchCandidateRecords"
      :loading="batchSelectLoading"
      @confirm="handleBatchSelectionConfirmed"
    />

    <!-- 顶部状态栏 -->

    <!-- 批量填充进度对话框 -->
    <el-dialog
      v-model="showBatchProgressDialog"
      title="批量填充进度"
      width="400px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
      align-center
      append-to-body
    >
      <div style="text-align: center; padding: 20px 0;">
        <el-progress 
          :percentage="Math.round((batchProgress.current / batchProgress.total) * 100)" 
          :color="batchCancelled ? '#909399' : '#07c160'"
        />
        <p style="margin-top: 16px; font-size: 14px; color: #606266;">
          {{ batchCancelled ? '正在取消...' : `正在填充: ${batchProgress.current} / ${batchProgress.total}` }}
        </p>
      </div>
      <template #footer>
        <el-button @click="cancelBatchOperation" :disabled="batchCancelled">
          {{ batchCancelled ? '取消中...' : '取消操作' }}
        </el-button>
      </template>
    </el-dialog>

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
