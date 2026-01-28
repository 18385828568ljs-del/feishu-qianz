/**
 * 分享表单组合式函数
 * 封装分享表单创建和字段选择逻辑
 */
import { ref } from 'vue'
import { createShareForm, getTableFields } from '@/services/api'

// 响应式状态
const shareFormName = ref('')
const shareFormDesc = ref('')
const generatedShareUrl = ref('')
const availableFields = ref([])
const selectedFields = ref([])
const loadingFields = ref(false)
const showFieldSelector = ref(false)
const currentAppToken = ref('')
const selectedRecordIndex = ref(1) // 记录条索引，默认选择记录条1
const showData = ref(false) // 是否在表单中显示关联记录的数据

/**
 * 加载多维表格字段列表
 * @param {string} appToken - 表格 app_token
 * @param {string} tableId - 表格 ID
 * @param {Function} showToast - Toast 通知函数
 */
async function loadTableFields(appToken, tableId, showToast) {
    try {
        loadingFields.value = true
        currentAppToken.value = appToken

        if (!appToken || !tableId) {
            showToast?.('无法获取表格信息', 'warning')
            return
        }

        const result = await getTableFields(appToken, tableId)

        if (result.success && result.fields) {
            availableFields.value = result.fields
        } else {
            availableFields.value = []
        }
    } catch (e) {
        console.error('加载字段失败:', e)
        showToast?.('加载字段列表失败', 'error')
        availableFields.value = []
    } finally {
        loadingFields.value = false
    }
}

/**
 * 切换字段选中状态
 * @param {Object} field - 字段对象
 */
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

/**
 * 检查字段是否已选中
 * @param {string} fieldId - 字段 ID
 * @returns {boolean}
 */
function isFieldSelected(fieldId) {
    return selectedFields.value.some(f => f.field_id === fieldId)
}

/**
 * 切换必填状态
 * @param {string} fieldId - 字段 ID
 */
function toggleRequired(fieldId) {
    const field = selectedFields.value.find(f => f.field_id === fieldId)
    if (field) {
        field.required = !field.required
    }
}

/**
 * 进入字段选择步骤
 * @param {Function} showToast - Toast 通知函数
 * @returns {boolean} 是否成功进入
 */
function goToFieldSelector(showToast) {
    if (!shareFormName.value.trim()) {
        showToast?.('请输入表单名称', 'warning')
        return false
    }
    showFieldSelector.value = true
    return true
}

/**
 * 返回基本信息步骤
 */
function goBackToBasicInfo() {
    showFieldSelector.value = false
}

/**
 * 创建分享签名表单
 * @param {Object} params - 参数
 * @param {string} params.tableId - 表格 ID
 * @param {string} params.userKey - 用户标识
 * @param {Function} showToast - Toast 通知函数
 */
async function handleCreateShareForm({ tableId, userKey }, showToast) {
    if (!shareFormName.value.trim()) {
        showToast?.('请输入表单名称', 'warning')
        return false
    }

    // 检查是否配置了授权码
    const baseToken = localStorage.getItem('feishu_base_token')
    if (!baseToken) {
        showToast?.('请先点击“授权码”按钮配置您的授权码', 'warning')
        return false
    }

    if (selectedFields.value.length === 0) {
        showToast?.('请至少选择一个字段', 'warning')
        return false
    }

    try {
        // 查找签名字段（附件类型）
        const signatureField = selectedFields.value.find(f => f.input_type === 'attachment')

        console.log('[useShareForm] 创建表单参数:', {
            record_index: selectedRecordIndex.value,
            show_data: showData.value,
            selectedFieldsCount: selectedFields.value.length
        })

        const result = await createShareForm({
            name: shareFormName.value.trim(),
            description: shareFormDesc.value.trim() || null,
            app_token: currentAppToken.value,
            table_id: tableId,
            signature_field_id: signatureField?.field_id || null,
            fields: selectedFields.value,
            created_by: userKey,
            base_token: baseToken,  // 传递授权码
            record_index: selectedRecordIndex.value,
            show_data: showData.value
        })
        
        console.log('[useShareForm] 表单创建结果:', result)

        if (result.success) {
            const baseUrl = window.location.origin || 'http://localhost:5173'
            generatedShareUrl.value = `${baseUrl}/sign?id=${result.form_id}`
            showToast?.('分享表单创建成功！', 'success')
            return true
        }
        return false
    } catch (e) {
        console.error('创建分享表单失败:', e)
        showToast?.('创建失败: ' + (e.response?.data?.detail || e.message), 'error')
        return false
    }
}

/**
 * 复制分享链接
 * @param {Function} showToast - Toast 通知函数
 */
function copyShareUrl(showToast) {
    if (!generatedShareUrl.value) return
    
    // 方案1: 使用 clipboard API（需要安全上下文）
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(generatedShareUrl.value).then(() => {
            showToast?.('链接已复制到剪贴板', 'success')
        }).catch(() => {
            fallbackCopy(generatedShareUrl.value, showToast)
        })
    } else {
        // 方案2: 降级方案
        fallbackCopy(generatedShareUrl.value, showToast)
    }
}

/**
 * 降级复制方案（兼容飞书 iframe 环境）
 * @param {string} text - 要复制的文本
 * @param {Function} showToast - Toast 通知函数
 */
function fallbackCopy(text, showToast) {
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
            showToast?.('链接已复制到剪贴板', 'success')
        } else {
            showToast?.('复制失败，请手动复制', 'error')
        }
    } catch (err) {
        showToast?.('复制失败，请手动复制', 'error')
    }
}

/**
 * 获取字段类型显示名称
 * @param {string} inputType - 输入类型
 * @returns {string}
 */
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

/**
 * 重置表单状态
 */
function resetShareForm() {
    shareFormName.value = ''
    shareFormDesc.value = ''
    generatedShareUrl.value = ''
    selectedFields.value = []
    showFieldSelector.value = false
    selectedRecordIndex.value = 1 // 重置为记录条1
    showData.value = false // 重置显示数据开关
}

export function useShareForm() {
    return {
        // 状态
        shareFormName,
        shareFormDesc,
        generatedShareUrl,
        availableFields,
        selectedFields,
        loadingFields,
        showFieldSelector,
        currentAppToken,
        selectedRecordIndex,
        showData,
        // 方法
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
    }
}
