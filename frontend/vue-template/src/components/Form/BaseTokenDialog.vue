<!--
  授权码配置弹窗组件
  用于让用户配置飞书授权码 (PersonalBaseToken)
-->
<script setup>
import { defineProps, defineEmits, ref, computed, watch } from 'vue'
import { useBaseToken } from '@/composables/useBaseToken'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'close', 'saved'])

const { baseToken, setBaseToken, hasBaseToken } = useBaseToken()

// 输入的授权码
const inputToken = ref(baseToken.value)

// 弹窗可见性
const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 同步已保存的授权码到输入框
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    inputToken.value = baseToken.value
  }
})

// 保存授权码
function handleSave() {
  const token = inputToken.value.trim()
  setBaseToken(token)
  emit('saved', token)
  visible.value = false
}

// 清空授权码
function handleClear() {
  inputToken.value = ''
}

// 关闭弹窗
function handleClose() {
  emit('close')
  visible.value = false
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="dialog-overlay" @click.self="handleClose">
      <div class="dialog-container">
        <!-- 头部 -->
        <div class="dialog-header">
          <h3 class="dialog-title">配置授权码</h3>
          <button class="close-btn" @click="handleClose">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- 内容 -->
        <div class="dialog-body">
          <!-- 提示信息 -->
          <div class="info-card">
            <div class="info-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 16v-4M12 8h.01"/>
              </svg>
            </div>
            <div class="info-content">
              <p class="info-title">授权码用于访问您的多维表格数据</p>
              <p class="info-desc">获取方式：多维表格 → 扩展 → API → 授权码</p>
              <a 
                class="info-link" 
                href="https://open.feishu.cn/document/uAjLw4CM/uYjL24iN/base/authorization" 
                target="_blank"
              >
                查看官方文档 →
              </a>
            </div>
          </div>

          <!-- 输入框 -->
          <div class="input-section">
            <label class="input-label">授权码 (PersonalBaseToken)</label>
            <div class="input-wrapper">
              <input
                v-model="inputToken"
                type="password"
                class="token-input"
                placeholder="请输入您的授权码"
              />
              <button v-if="inputToken" class="clear-btn" @click="handleClear">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M15 9l-6 6M9 9l6 6"/>
                </svg>
              </button>
            </div>
          </div>

          <!-- 状态提示 -->
          <div v-if="hasBaseToken" class="status-tip success">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 6L9 17l-5-5"/>
            </svg>
            <span>已配置授权码</span>
          </div>
        </div>

        <!-- 底部按钮 -->
        <div class="dialog-footer">
          <button class="btn btn-default" @click="handleClose">取消</button>
          <button class="btn btn-primary" @click="handleSave">保存</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 20px;
}

.dialog-container {
  background: #fff;
  border-radius: 16px;
  width: 100%;
  max-width: 380px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  overflow: hidden;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
}

.dialog-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1d1d1f;
}

.close-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: #f5f5f5;
  border-radius: 50%;
  cursor: pointer;
  color: #86868b;
  transition: all 0.15s;
}

.close-btn:hover {
  background: #e8e8ed;
  color: #1d1d1f;
}

.close-btn svg {
  width: 14px;
  height: 14px;
}

.dialog-body {
  padding: 20px;
}

.info-card {
  display: flex;
  gap: 12px;
  padding: 14px;
  background: #f5f5f7;
  border-radius: 12px;
  margin-bottom: 20px;
}

.info-icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  color: #007aff;
}

.info-icon svg {
  width: 100%;
  height: 100%;
}

.info-content {
  flex: 1;
}

.info-title {
  margin: 0 0 4px;
  font-size: 13px;
  font-weight: 500;
  color: #1d1d1f;
}

.info-desc {
  margin: 0 0 8px;
  font-size: 12px;
  color: #86868b;
}

.info-link {
  font-size: 12px;
  color: #007aff;
  text-decoration: none;
}

.info-link:hover {
  text-decoration: underline;
}

.input-section {
  margin-bottom: 16px;
}

.input-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #1d1d1f;
  margin-bottom: 8px;
}

.input-wrapper {
  position: relative;
}

.token-input {
  width: 100%;
  padding: 12px 40px 12px 14px;
  font-size: 14px;
  border: 1px solid #e5e5e5;
  border-radius: 10px;
  outline: none;
  transition: all 0.15s;
  box-sizing: border-box;
}

.token-input:focus {
  border-color: #007aff;
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.1);
}

.token-input::placeholder {
  color: #c7c7cc;
}

.clear-btn {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: #e8e8ed;
  border-radius: 50%;
  cursor: pointer;
  color: #86868b;
}

.clear-btn:hover {
  background: #d1d1d6;
  color: #1d1d1f;
}

.clear-btn svg {
  width: 12px;
  height: 12px;
}

.status-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
}

.status-tip.success {
  background: #e8f5e9;
  color: #34c759;
}

.status-tip svg {
  width: 16px;
  height: 16px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 20px;
  border-top: 1px solid #f0f0f0;
}

.btn {
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 500;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-default {
  background: #f5f5f5;
  color: #1d1d1f;
}

.btn-default:hover {
  background: #e8e8ed;
}

.btn-primary {
  background: #007aff;
  color: #fff;
}

.btn-primary:hover {
  background: #0066d6;
}
</style>
