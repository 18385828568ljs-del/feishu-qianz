<!--
  购买引导组件 - 飞书官方付费版本
  引导用户前往飞书插件详情页购买
-->
<script setup>
import { ref, defineProps, defineEmits } from 'vue'
import { ElDialog, ElButton } from 'element-plus'
import { bitable } from '@lark-base-open/js-sdk'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'close'])

const isOpening = ref(false)

// 关闭弹窗
function handleClose() {
  emit('update:modelValue', false)
  emit('close')
}

// 跳转到插件详情页购买
async function goToPurchase() {
  isOpening.value = true
  
  try {
    // 方式1：尝试使用飞书JSAPI打开插件详情页
    const { appId } = await bitable.bridge.getEnv()
    
    if (appId) {
      // 使用飞书协议打开插件详情页
      const detailUrl = `https://applink.feishu.cn/client/web_app/open?appId=${appId}`
      window.open(detailUrl, '_blank')
    } else {
      // 降级方案：提示用户手动打开
      alert('请在飞书应用商店搜索"签名助手"并购买')
    }
    
    // 关闭弹窗
    handleClose()
  } catch (error) {
    console.error('打开插件详情页失败:', error)
    // 降级方案
    alert('请在飞书应用商店中找到本插件并购买')
  } finally {
    isOpening.value = false
  }
}
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
        <div class="header-left">
           <!-- 占位，保持标题居中 -->
        </div>
        <div class="dialog-title-text">购买签名配额</div>
        <button class="close-btn" @click="handleClose">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6 6 18M6 6l12 12"/>
          </svg>
        </button>
      </div>
    </template>
    
    <div class="dialog-content">
      <div class="purchase-guide">
        <!-- 飞书图标 -->
        <div class="feishu-icon">
          <svg viewBox="0 0 48 48" fill="none">
            <rect width="48" height="48" rx="12" fill="#00D6B9"/>
            <path d="M24 12L16 20h6v8h4v-8h6l-8-8z" fill="white"/>
            <path d="M14 32h20v2H14z" fill="white"/>
          </svg>
        </div>
        
        <!-- 提示文案 -->
        <h3 class="guide-title">获取更多签名配额</h3>
        <p class="guide-desc">
          当前配额已用完或不足。<br/>
          请前往<strong>飞书插件详情页</strong>选购套餐。
        </p>
        
        <!-- 购买步骤 -->
        <div class="steps">
          <div class="step-item">
            <div class="step-num">1</div>
            <div class="step-text">点击下方"前往购买"按钮</div>
          </div>
          <div class="step-item">
            <div class="step-num">2</div>
            <div class="step-text">在插件详情页选择合适套餐</div>
          </div>
          <div class="step-item">
            <div class="step-num">3</div>
            <div class="step-text">支付成功后配额即时生效</div>
          </div>
        </div>
        
        <!-- 优势说明 -->
        <div class="benefits">
          <div class="benefit-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z"/>
              <path d="M9 12L11 14L15 10"/>
            </svg>
            <span>官方安全</span>
          </div>
          <div class="benefit-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
            </svg>
            <span>即时到账</span>
          </div>
          <div class="benefit-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 6v6l4 2"/>
            </svg>
            <span>自动同步</span>
          </div>
        </div>
        
        <!-- 按钮 -->
        <div class="actions">
          <el-button 
            type="primary" 
            size="large" 
            @click="goToPurchase"
            :loading="isOpening"
            class="purchase-btn"
          >
            {{ isOpening ? '正在打开...' : '前往购买' }}
          </el-button>
        </div>
        
        <!-- 底部提示 -->
        <p class="bottom-note">
          <svg class="info-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
          购买后返回插件即可继续使用
        </p>
      </div>
    </div>
  </el-dialog>
</template>

<style scoped>
/* 弹窗头部 */
.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between; /* 两端对齐 */
  padding-bottom: 0;
  position: relative;
  height: 24px;
}

.header-left {
    width: 28px; /* 占位，与右侧按钮平衡 */
}

/* 自定义关闭按钮样式 */
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
  width: 20px; /* 稍微大一点，更易点击 */
  height: 20px;
}

.close-btn:hover {
  background: rgba(31, 35, 41, 0.1); /* 飞书风格 hover */
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
}

.purchase-guide {
  text-align: center;
  padding: 0 4px;
}

.feishu-icon {
  width: 64px; /* 稍微缩小图标，更精致 */
  height: 64px;
  margin: 0 auto 16px;
}

.feishu-icon svg {
  width: 100%;
  height: 100%;
  filter: drop-shadow(0 4px 12px rgba(0, 214, 185, 0.2));
}

.guide-title {
  font-size: 20px;
  font-weight: 600;
  color: #1f2329;
  margin-bottom: 8px;
}

.guide-desc {
  font-size: 14px;
  color: #646a73;
  line-height: 1.5;
  margin-bottom: 24px;
}

.guide-desc strong {
  color: #00D6B9;
  font-weight: 600;
}

/* 购买步骤 - 优化布局 */
.steps {
  text-align: left;
  margin: 0 auto 24px;
  background: #f5f6f7;
  padding: 16px;
  border-radius: 8px;
}

.step-item {
  display: flex;
  align-items: start;
  gap: 10px;
  margin-bottom: 12px;
}

.step-item:last-child {
  margin-bottom: 0;
}

.step-num {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3370ff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
  margin-top: 1px; /* 对齐文字 */
}

.step-text {
  font-size: 14px;
  color: #434343; /* 深色一点，增加易读性 */
  line-height: 1.5;
}

/* 优势说明 - 紧凑布局 */
.benefits {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.benefit-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #8f959e;
}

.benefit-item svg {
  width: 16px;
  height: 16px;
  color: #34c759;
}

/* 按钮 */
.actions {
  margin-bottom: 12px;
}

.purchase-btn {
  width: 100%;
  height: 44px;
  border-radius: 8px; /* 稍微圆角小一点，更商务 */
  font-size: 16px;
  font-weight: 500;
  background: #3370ff; /* 飞书蓝 */
  border: none;
  box-shadow: 0 2px 6px rgba(51, 112, 255, 0.2);
  transition: all 0.2s;
}

.purchase-btn:hover {
  background: #295ed9;
  transform: translateY(-1px);
}

.purchase-btn:active {
  transform: translateY(0);
}

/* 底部提示 */
.bottom-note {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 12px;
  color: #8f959e;
}

.info-icon {
  width: 14px;
  height: 14px;
}
</style>
