<!--
  充值/购买套餐弹窗组件
  展示套餐列表，支持选择套餐并完成支付
-->
<script setup>
import { ref, onMounted, watch, defineProps, defineEmits } from 'vue'
import { ElDialog, ElButton, ElMessage } from 'element-plus'
import { getPricingPlans, createOrder, mockPay } from '@/services/api'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  userInfo: {
    type: Object,
    default: () => ({ openId: '', tenantKey: '' })
  }
})

const emit = defineEmits(['update:modelValue', 'close', 'success', 'toast'])

// 状态
const loading = ref(false)
const plans = ref([])
const selectedPlan = ref(null)
const creatingOrder = ref(false)
const paying = ref(false)

// 加载套餐列表
async function loadPlans() {
  loading.value = true
  try {
    const data = await getPricingPlans()
    console.log('获取到的套餐数据:', data)
    plans.value = Array.isArray(data) ? data : []
    console.log('设置后的套餐列表:', plans.value)
    if (plans.value.length === 0) {
      console.warn('套餐列表为空')
    }
  } catch (error) {
    console.error('加载套餐列表失败:', error)
    console.error('错误详情:', error.response?.data || error.message)
    emit('toast', { message: '加载套餐列表失败，请稍后重试', type: 'error' })
    plans.value = []
  } finally {
    loading.value = false
  }
}

// 关闭弹窗
function handleClose() {
  emit('update:modelValue', false)
  emit('close')
  selectedPlan.value = null
}

// 选择套餐
function selectPlan(plan) {
  selectedPlan.value = plan
}

// 格式化价格（分转元）
function formatPrice(priceInCents) {
  return (priceInCents / 100).toFixed(2)
}

// 购买套餐
async function purchasePlan() {
  if (!selectedPlan.value) {
    emit('toast', { message: '请先选择套餐', type: 'warning' })
    return
  }

  if (!props.userInfo.openId || !props.userInfo.tenantKey) {
    emit('toast', { message: '用户信息不完整', type: 'error' })
    return
  }

  creatingOrder.value = true
  let orderId = null

  try {
    // 创建订单
    const orderResult = await createOrder(
      selectedPlan.value.id,
      props.userInfo.openId,
      props.userInfo.tenantKey
    )

    if (!orderResult.success) {
      throw new Error(orderResult.error || '创建订单失败')
    }

    orderId = orderResult.order_id

    // 模拟支付
    paying.value = true
    const payResult = await mockPay(orderId)

    if (!payResult.success) {
      throw new Error(payResult.error || '支付失败')
    }

    // 支付成功
    emit('toast', { 
      message: `购买成功！已获得 ${selectedPlan.value.count} 次签名配额`, 
      type: 'success' 
    })
    emit('success')
    handleClose()
  } catch (error) {
    console.error('购买失败:', error)
    emit('toast', { 
      message: error.message || '购买失败，请稍后重试', 
      type: 'error' 
    })
  } finally {
    creatingOrder.value = false
    paying.value = false
  }
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
    class="recharge-dialog"
    @close="handleClose"
  >
    <template #header>
      <div class="dialog-header">
        <div class="header-left"></div>
        <div class="dialog-title-text">购买签名配额</div>
        <button class="close-btn" @click="handleClose">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6 6 18M6 6l12 12"/>
          </svg>
        </button>
      </div>
    </template>
    
    <div class="dialog-content">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-container">
        <div class="loading-spinner"></div>
        <p>加载套餐中...</p>
      </div>

      <!-- 套餐列表 -->
      <div v-else-if="plans.length > 0" class="plans-container">
        <div class="plans-grid">
          <div 
            v-for="plan in plans" 
            :key="plan.id"
            class="plan-card"
            :class="{ 'selected': selectedPlan?.id === plan.id }"
            @click="selectPlan(plan)"
          >
            <div class="plan-header">
              <h3 class="plan-name">{{ plan.name }}</h3>
              <div v-if="selectedPlan?.id === plan.id" class="selected-badge">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 6L9 17l-5-5"/>
                </svg>
              </div>
            </div>
            <div class="plan-body">
              <div class="plan-quota">
                <span class="quota-number">{{ plan.count }}</span>
                <span class="quota-unit">次签名</span>
              </div>
              <div class="plan-price">
                <span class="price-symbol">¥</span>
                <span class="price-amount">{{ formatPrice(plan.price) }}</span>
              </div>
              <div v-if="plan.description" class="plan-desc">
                {{ plan.description }}
              </div>
            </div>
          </div>
        </div>

        <!-- 购买按钮 -->
        <div class="purchase-actions">
          <el-button 
            type="primary" 
            size="large"
            :disabled="!selectedPlan || creatingOrder || paying"
            :loading="creatingOrder || paying"
            @click="purchasePlan"
            class="purchase-btn"
          >
            <span v-if="creatingOrder">创建订单中...</span>
            <span v-else-if="paying">支付中...</span>
            <span v-else-if="selectedPlan">立即购买 ¥{{ formatPrice(selectedPlan.price) }}</span>
            <span v-else>请选择套餐</span>
          </el-button>
        </div>
      </div>

      <!-- 无套餐提示 -->
      <div v-else class="empty-container">
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

.header-left {
  width: 28px;
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

/* 套餐列表 */
.plans-container {
  padding: 0 4px;
}

.plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}

.plan-card {
  background: #fff;
  border: 2px solid #f0f0f0;
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.plan-card:hover {
  border-color: #3370ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(51, 112, 255, 0.15);
}

.plan-card.selected {
  border-color: #3370ff;
  background: #f7f9ff;
  box-shadow: 0 4px 12px rgba(51, 112, 255, 0.2);
}

.plan-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.plan-name {
  font-size: 15px;
  font-weight: 600;
  color: #1f2329;
  margin: 0;
}

.selected-badge {
  width: 20px;
  height: 20px;
  background: #3370ff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.selected-badge svg {
  width: 12px;
  height: 12px;
}

.plan-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.plan-quota {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.quota-number {
  font-size: 24px;
  font-weight: 700;
  color: #1f2329;
}

.quota-unit {
  font-size: 14px;
  color: #646a73;
}

.plan-price {
  display: flex;
  align-items: baseline;
  gap: 2px;
  margin-top: 4px;
}

.price-symbol {
  font-size: 14px;
  color: #646a73;
  font-weight: 500;
}

.price-amount {
  font-size: 20px;
  font-weight: 700;
  color: #3370ff;
}

.plan-desc {
  font-size: 12px;
  color: #8f959e;
  line-height: 1.4;
  margin-top: 4px;
}

/* 购买按钮 */
.purchase-actions {
  padding: 0 4px;
}

.purchase-btn {
  width: 100%;
  height: 44px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  background: #3370ff;
  border: none;
  box-shadow: 0 2px 6px rgba(51, 112, 255, 0.2);
  transition: all 0.2s;
}

.purchase-btn:hover:not(:disabled) {
  background: #295ed9;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(51, 112, 255, 0.3);
}

.purchase-btn:active:not(:disabled) {
  transform: translateY(0);
}

.purchase-btn:disabled {
  background: #e5e5e5;
  color: #999;
  cursor: not-allowed;
  box-shadow: none;
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
