<!--
  充值/购买套餐弹窗组件
  展示套餐列表，支持支付宝扫码支付
-->
<script setup>
import { ref, onMounted, watch, defineProps, defineEmits, onUnmounted } from 'vue'
import { ElDialog, ElButton, ElMessage } from 'element-plus'
import { getPricingPlans, createAlipayOrder, queryAlipayOrder } from '@/services/api'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  quotaInfo: {
    type: Object,
    default: () => ({ planExpiresAt: null })
  }
})

const emit = defineEmits(['update:modelValue', 'close', 'success', 'toast'])

// 状态
const loading = ref(false)
const plans = ref([])
const selectedPlan = ref(null)
const creatingOrder = ref(false)

// 支付状态
const showPayment = ref(false)  // 是否显示支付界面
const qrCodeUrl = ref('')        // 二维码URL
const currentOrderId = ref('')   // 当前订单ID
const paymentPolling = ref(null) // 轮询定时器
const paymentStatus = ref('pending')  // pending, checking, success, failed

// 按套餐类型分组
const groupedPlans = ref({})

// 加载套餐列表
async function loadPlans() {
  loading.value = true
  try {
    const data = await getPricingPlans()
    plans.value = Array.isArray(data) ? data : []
    
    // 按套餐类型分组
    const grouped = {}
    plans.value.forEach(plan => {
      let groupKey = ''
      if (plan.id.startsWith('basic')) {
        groupKey = 'basic'
      } else if (plan.id.startsWith('pro')) {
        groupKey = 'pro'
      } else if (plan.id.startsWith('enterprise')) {
        groupKey = 'enterprise'
      }
      
      if (groupKey) {
        if (!grouped[groupKey]) {
          grouped[groupKey] = {
            name: plan.name,
            monthly: null,
            yearly: null
          }
        }
        if (plan.billing_type === 'monthly') {
          grouped[groupKey].monthly = plan
        } else if (plan.billing_type === 'yearly') {
          grouped[groupKey].yearly = plan
        }
      }
    })
    groupedPlans.value = grouped
  } catch (error) {
    console.error('加载套餐列表失败:', error)
    emit('toast', { message: '加载套餐列表失败，请稍后重试', type: 'error' })
    plans.value = []
    groupedPlans.value = {}
  } finally {
    loading.value = false
  }
}

// 关闭弹窗
function handleClose() {
  stopPolling()
  showPayment.value = false
  qrCodeUrl.value = ''
  currentOrderId.value = ''
  paymentStatus.value = 'pending'
  emit('update:modelValue', false)
  emit('close')
  selectedPlan.value = null
}

// 选择套餐
function selectPlan(plan) {
  selectedPlan.value = plan
}

// 格式化到期时间
function formatExpireDate(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp * 1000)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}年${month}月${day}日`
}

// 格式化价格（分转元）
function formatPrice(priceInCents) {
  if (!priceInCents) return '0.00'
  return (priceInCents / 100).toFixed(2)
}

// 获取套餐的显示价格（优先使用 monthly_price/yearly_price，否则使用 price）
function getPlanPrice(plan) {
  if (!plan) return 0
  // 如果是月付套餐，优先使用 monthly_price
  if (plan.billing_type === 'monthly' && plan.monthly_price !== null && plan.monthly_price !== undefined) {
    return plan.monthly_price
  }
  // 如果是年付套餐，优先使用 yearly_price
  if (plan.billing_type === 'yearly' && plan.yearly_price !== null && plan.yearly_price !== undefined) {
    return plan.yearly_price
  }
  // 否则使用 price
  return plan.price || 0
}

// 获取套餐显示名称
function getPlanDisplayName(groupKey) {
  const names = {
    'basic': '入门版',
    'pro': '专业版',
    'enterprise': '企业版'
  }
  return names[groupKey] || ''
}

// 获取套餐配额显示
function getQuotaDisplay(plan) {
  if (plan.unlimited) {
    return '不限次数'
  }
  if (plan.count) {
    return `${plan.count}次/月`
  }
  return '0次'
}

// 开始支付宝支付
async function startAlipayPayment() {
  if (!selectedPlan.value) {
    emit('toast', { message: '请先选择套餐', type: 'warning' })
    return
  }

  creatingOrder.value = true
  paymentStatus.value = 'pending'

  try {
    // 创建支付宝订单（用户信息从 JWT 中提取）
    const result = await createAlipayOrder(
      selectedPlan.value.id,
      'native'  // 扫码支付
    )

    if (!result.success) {
      throw new Error(result.error || '创建订单失败')
    }

    // 显示二维码
    // 如果后端返回的是 base64 (以 data: 开头)，直接显示
    // 否则直接使用 result.qr_code（对应 type=2 的直接图片链接）
    qrCodeUrl.value = result.qr_code
    
    currentOrderId.value = result.order_id
    showPayment.value = true

    // 开始轮询支付状态
    startPolling()

  } catch (error) {
    console.error('创建支付订单失败:', error)
    emit('toast', { 
      message: error.message || '创建订单失败，请稍后重试', 
      type: 'error' 
    })
  } finally {
    creatingOrder.value = false
  }
}

// 开始轮询支付状态
function startPolling() {
  stopPolling()  // 先停止之前的轮询
  
  paymentPolling.value = setInterval(async () => {
    if (!currentOrderId.value) {
      stopPolling()
      return
    }

    try {
      paymentStatus.value = 'checking'
      const result = await queryAlipayOrder(currentOrderId.value)
      
      if (result.success && result.status === 'paid') {
        // 支付成功
        paymentStatus.value = 'success'
        stopPolling()
        
        const quotaText = selectedPlan.value.unlimited 
          ? '不限次数' 
          : `${selectedPlan.value.count} 次签名配额`
        emit('toast', { 
          message: `购买成功！已获得 ${quotaText}`, 
          type: 'success' 
        })
        emit('success')
        
        // 延迟关闭弹窗
        setTimeout(() => {
          handleClose()
        }, 1500)
      } else {
        paymentStatus.value = 'pending'
      }
    } catch (error) {
      console.warn('查询支付状态失败:', error)
      paymentStatus.value = 'pending'
    }
  }, 2000)  // 每2秒查询一次
}

// 停止轮询
function stopPolling() {
  if (paymentPolling.value) {
    clearInterval(paymentPolling.value)
    paymentPolling.value = null
  }
}

// 返回套餐选择
function backToPlans() {
  stopPolling()
  showPayment.value = false
  qrCodeUrl.value = ''
  currentOrderId.value = ''
  paymentStatus.value = 'pending'
}

// 弹窗打开时加载套餐列表
onMounted(() => {
  if (props.modelValue) {
    loadPlans()
  }
})

// 监听弹窗打开
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    loadPlans()
    showPayment.value = false
  } else {
    stopPolling()
  }
})

// 组件卸载时停止轮询
onUnmounted(() => {
  stopPolling()
})
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
    class="recharge-dialog"
    @close="handleClose"
  >
    <template #header>
      <div class="dialog-header">
        <button v-if="showPayment" class="back-btn" @click="backToPlans">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M15 18l-6-6 6-6"/>
          </svg>
        </button>
        <div v-else class="header-left"></div>
        <div class="dialog-title-text">
          {{ showPayment ? '支付宝支付' : '购买签名配额' }}
        </div>
        <button class="close-btn" @click="handleClose">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6 6 18M6 6l12 12"/>
          </svg>
        </button>
      </div>
      <!-- 到期时间提示 -->
      <div v-if="!showPayment && quotaInfo?.planExpiresAt" class="expire-hint">
        当前套餐到期时间：{{ formatExpireDate(quotaInfo.planExpiresAt) }}
      </div>
    </template>
    
    <div class="dialog-content">
      <!-- 支付界面 -->
      <div v-if="showPayment" class="payment-container">
        <div class="payment-info">
          <div class="plan-summary">
            <span class="plan-label">{{ selectedPlan?.name }}</span>
            <span class="plan-price">¥{{ formatPrice(getPlanPrice(selectedPlan)) }}</span>
          </div>
          
          <!-- 二维码 -->
          <div class="qrcode-wrapper">
            <img v-if="qrCodeUrl" :src="qrCodeUrl" alt="支付宝扫码支付" class="qrcode-image" />
            <div v-else class="qrcode-loading">
              <div class="loading-spinner"></div>
            </div>
          </div>
          
          <div class="payment-tips">
            <div class="alipay-logo">
              <svg viewBox="0 0 24 24" fill="#1677FF" width="20" height="20">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/>
              </svg>
              <span>请使用支付宝扫码支付</span>
            </div>
            <p class="status-text">
              <span v-if="paymentStatus === 'checking'" class="checking">
                <span class="dot-loading"></span>正在检测支付状态...
              </span>
              <span v-else-if="paymentStatus === 'success'" class="success">
                ✓ 支付成功！
              </span>
              <span v-else class="pending">
                支付完成后将自动跳转
              </span>
            </p>
          </div>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-else-if="loading" class="loading-container">
        <div class="loading-spinner"></div>
        <p>加载套餐中...</p>
      </div>

      <!-- 套餐列表 -->
      <div v-else-if="Object.keys(groupedPlans).length > 0" class="plans-container">
        <div 
          v-for="(group, groupKey) in groupedPlans" 
          :key="groupKey"
          class="plan-group"
        >
          <h3 class="group-title">{{ getPlanDisplayName(groupKey) }}</h3>
          <div class="plans-row">
            <!-- 月付套餐 -->
            <div 
              v-if="group.monthly"
              class="plan-card"
              :class="{ 'selected': selectedPlan?.id === group.monthly.id }"
              @click="selectPlan(group.monthly)"
            >
              <div class="plan-header">
                <h3 class="plan-name">{{ group.monthly.name }}</h3>
                <span class="billing-badge monthly">月付</span>
                <div v-if="selectedPlan?.id === group.monthly.id" class="selected-badge">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M20 6L9 17l-5-5"/>
                  </svg>
                </div>
              </div>
              <div class="plan-body">
                <div class="plan-quota">
                  <span class="quota-number">{{ getQuotaDisplay(group.monthly) }}</span>
                </div>
                <div class="plan-price">
                  <span class="price-symbol">¥</span>
                  <span class="price-amount">{{ formatPrice(getPlanPrice(group.monthly)) }}</span>
                  <span class="price-unit">/月</span>
                </div>
              </div>
            </div>
            
            <!-- 年付套餐 -->
            <div 
              v-if="group.yearly"
              class="plan-card yearly-card"
              :class="{ 'selected': selectedPlan?.id === group.yearly.id }"
              @click="selectPlan(group.yearly)"
            >
              <div class="plan-header">
                <h3 class="plan-name">{{ group.yearly.name }}</h3>
                <span class="billing-badge yearly">年付</span>
                <div v-if="selectedPlan?.id === group.yearly.id" class="selected-badge">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M20 6L9 17l-5-5"/>
                  </svg>
                </div>
              </div>
              <div class="plan-body">
                <div class="plan-quota">
                  <span class="quota-number">{{ getQuotaDisplay(group.yearly) }}</span>
                </div>
                <div class="plan-price">
                  <span class="price-symbol">¥</span>
                  <span class="price-amount">{{ formatPrice(getPlanPrice(group.yearly)) }}</span>
                  <span class="price-unit">/年</span>
                </div>
                <div v-if="group.yearly.save_percent" class="save-badge">
                  节省{{ group.yearly.save_percent }}%
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 购买按钮 -->
        <div class="purchase-actions">
          <el-button 
            type="primary" 
            size="large"
            :disabled="!selectedPlan || creatingOrder"
            :loading="creatingOrder"
            @click="startAlipayPayment"
            class="purchase-btn alipay-btn"
          >
            <svg v-if="!creatingOrder" class="alipay-icon" viewBox="0 0 1024 1024" fill="currentColor">
              <path d="M789.12 595.584c-64.256-27.776-132.224-55.68-185.728-77.952 21.632-52.992 37.568-112.64 41.216-157.056H471.68v-56.32h197.504V272.64H471.68V192h-82.304v80.64H192.128v31.616h197.248v56.32H206.848v31.616h341.888c-5.12 35.584-16.512 80.64-33.92 121.344-72.064-26.24-159.616-55.04-252.288-76.16l-15.616 32.256c169.984 38.912 335.104 94.592 478.208 158.848C648.96 756.48 517.888 832 358.784 832c-148.608 0-271.872-65.408-271.872-186.88 0-73.088 52.864-137.472 134.528-179.84l-22.656-28.8C92.16 486.656 0 571.264 0 680.32 0 841.6 159.744 960 375.04 960c206.592 0 371.456-99.072 463.36-267.136 60.032 30.976 109.696 60.16 144.512 85.376L1024 746.88c-52.352-35.968-133.504-87.936-234.88-151.296z"/>
            </svg>
            <span v-if="creatingOrder">创建订单中...</span>
            <span v-else-if="selectedPlan">支付宝支付 ¥{{ formatPrice(getPlanPrice(selectedPlan)) }}</span>
            <span v-else>请选择套餐</span>
          </el-button>
        </div>
      </div>

      <!-- 无套餐提示 -->
      <div v-else-if="!loading" class="empty-container">
        <p>暂无可用套餐</p>
      </div>
    </div>
  </el-dialog>
</template>

<style scoped>
/* 弹窗头部 */
.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 0;
  position: relative;
  height: 24px;
}

.header-left, .back-btn {
  width: 28px;
  height: 28px;
}

.back-btn {
  border: none;
  background: transparent;
  border-radius: 50%;
  color: #8f959e;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  padding: 0;
}

.back-btn svg {
  width: 20px;
  height: 20px;
}

.back-btn:hover {
  background: rgba(31, 35, 41, 0.1);
  color: #1f2329;
}

.close-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  border-radius: 50%;
  color: #8f959e;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  padding: 0;
}

.close-btn svg {
  width: 20px;
  height: 20px;
}

.close-btn:hover {
  background: rgba(31, 35, 41, 0.1);
  color: #1f2329;
}

.dialog-title-text {
  font-size: 17px;
  font-weight: 600;
  color: #1f2329;
  flex: 1;
  text-align: center;
}

/* 弹窗内容 */
.dialog-content {
  padding-top: 12px;
  min-height: 200px;
}

/* 支付界面 */
.payment-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 0;
}

.payment-info {
  text-align: center;
  width: 100%;
}

.plan-summary {
  display: flex;
  justify-content: center;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 24px;
}

.plan-label {
  font-size: 16px;
  color: #646a73;
}

.plan-summary .plan-price {
  font-size: 28px;
  font-weight: 700;
  color: #1677FF;
}

.qrcode-wrapper {
  width: 200px;
  height: 200px;
  margin: 0 auto 20px;
  border: 1px solid #f0f0f0;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
}

.qrcode-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.qrcode-loading {
  display: flex;
  align-items: center;
  justify-content: center;
}

.payment-tips {
  text-align: center;
}

.alipay-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #1677FF;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 8px;
}

.status-text {
  font-size: 13px;
  color: #8f959e;
  margin: 0;
}

.status-text .checking {
  color: #ff9500;
}

.status-text .success {
  color: #34c759;
  font-weight: 500;
}

.dot-loading {
  display: inline-block;
  width: 6px;
  height: 6px;
  background: #ff9500;
  border-radius: 50%;
  margin-right: 6px;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* 加载状态 */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #646a73;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #f0f0f0;
  border-top-color: #3370ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 12px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 到期时间提示 */
.expire-hint {
  text-align: center;
  font-size: 13px;
  color: #8f959e;
  padding: 8px 16px 12px;
  margin: 0;
  border-bottom: 1px solid #f0f0f0;
}

/* 套餐列表 */
.plans-container {
  padding: 0 4px;
}

.plan-group {
  margin-bottom: 24px;
}

.plan-group:last-child {
  margin-bottom: 0;
}

.group-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2329;
  margin: 0 0 12px 0;
  padding: 0 4px;
}

.plans-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
}

.plan-card {
  background: #fff;
  border: 2px solid #f0f0f0;
  border-radius: 12px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.plan-card:hover {
  border-color: #3370ff;
}

.plan-card.selected {
  border-color: #3370ff;
  background: #f7f9ff;
}

.plan-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  gap: 6px;
  flex-wrap: wrap;
}

.billing-badge {
  font-size: 10px;
  padding: 2px 5px;
  border-radius: 4px;
  font-weight: 500;
}

.billing-badge.monthly {
  background: #e8f4ff;
  color: #3370ff;
}

.billing-badge.yearly {
  background: #fff4e6;
  color: #ff9500;
}

.plan-card.yearly-card {
  border-color: #ff9500;
}

.plan-card.yearly-card::before {
  content: '推荐';
  position: absolute;
  top: -8px;
  right: 12px;
  background: #ff9500;
  color: #fff;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.plan-name {
  font-size: 14px;
  font-weight: 600;
  color: #1f2329;
  margin: 0;
}

.selected-badge {
  width: 18px;
  height: 18px;
  background: #3370ff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.selected-badge svg {
  width: 10px;
  height: 10px;
}

.plan-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.plan-quota {
  min-height: 28px;
}

.quota-number {
  font-size: 18px;
  font-weight: 700;
  color: #1f2329;
}

.plan-price {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.price-symbol {
  font-size: 12px;
  color: #646a73;
}

.price-amount {
  font-size: 18px;
  font-weight: 700;
  color: #3370ff;
}

.price-unit {
  font-size: 11px;
  color: #8f959e;
}

.save-badge {
  display: inline-block;
  background: #fff4e6;
  color: #ff9500;
  font-size: 10px;
  padding: 2px 5px;
  border-radius: 4px;
  font-weight: 500;
}

/* 购买按钮 */
.purchase-actions {
  margin-top: 20px;
  padding: 0 4px;
}

.purchase-btn {
  width: 100%;
  height: 44px;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  border: none;
  transition: all 0.2s;
}

.alipay-btn {
  background: #1677FF;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.alipay-btn:hover:not(:disabled) {
  background: #0958d9;
}

.alipay-icon {
  width: 18px;
  height: 18px;
}

.purchase-btn:disabled {
  background: #e5e5e5;
  color: #999;
  cursor: not-allowed;
}

/* 空状态 */
.empty-container {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #646a73;
  font-size: 14px;
}
</style>
