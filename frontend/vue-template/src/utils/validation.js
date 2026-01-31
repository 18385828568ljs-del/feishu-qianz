/**
 * 参数验证工具函数
 */

/**
 * 验证用户信息是否完整
 * @param {Object} userInfo - 用户信息对象
 * @param {string} userInfo.openId - 用户ID
 * @param {string} userInfo.tenantKey - 租户Key
 * @returns {Object} { valid: boolean, missing: string[] }
 */
export function validateUserInfo(userInfo) {
  const missing = []
  
  if (!userInfo) {
    return { valid: false, missing: ['userInfo'] }
  }
  
  if (!userInfo.openId || userInfo.openId === 'anonymous') {
    missing.push('openId')
  }
  
  if (!userInfo.tenantKey || userInfo.tenantKey === 'anonymous') {
    missing.push('tenantKey')
  }
  
  return {
    valid: missing.length === 0,
    missing
  }
}

/**
 * 验证签名上传参数
 * @param {Object} params - 上传参数
 * @returns {Object} { valid: boolean, missing: string[] }
 */
export function validateUploadParams(params) {
  const missing = []
  const required = ['blob', 'fileName', 'folderToken', 'openId', 'tenantKey']
  
  required.forEach(field => {
    if (!params[field]) {
      missing.push(field)
    }
  })
  
  return {
    valid: missing.length === 0,
    missing
  }
}

/**
 * 验证配额查询参数
 * @param {string} openId - 用户ID
 * @param {string} tenantKey - 租户Key
 * @returns {Object} { valid: boolean, missing: string[] }
 */
export function validateQuotaParams(openId, tenantKey) {
  const missing = []
  
  if (!openId) missing.push('openId')
  if (!tenantKey) missing.push('tenantKey')
  
  return {
    valid: missing.length === 0,
    missing
  }
}

/**
 * 生成友好的错误提示
 * @param {string[]} missing - 缺失的字段列表
 * @returns {string} 错误提示文本
 */
export function getMissingFieldsMessage(missing) {
  const fieldNames = {
    openId: '用户ID',
    tenantKey: '租户Key',
    blob: '签名图片',
    fileName: '文件名',
    folderToken: '文件夹Token'
  }
  
  const missingNames = missing.map(field => fieldNames[field] || field)
  return `缺少必填参数：${missingNames.join('、')}`
}
