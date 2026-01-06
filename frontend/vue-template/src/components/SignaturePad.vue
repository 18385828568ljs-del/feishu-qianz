<template>
  <div class="sig-wrap">
    <canvas ref="canvas"
            @mousedown="onPointerDown"
            @mousemove="onPointerMove"
            @mouseup="onPointerUp"
            @mouseleave="onPointerUp"
            @touchstart.prevent="onTouchStart"
            @touchmove.prevent="onTouchMove"
            @touchend.prevent="onTouchEnd"></canvas>
    <div class="ops">
      <el-button @click="clear">清除</el-button>
      <el-button type="primary" @click="confirm">确认</el-button>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

const emits = defineEmits(['confirm'])
const canvas = ref(null)
let ctx
let drawing = false
let last = null

function initCanvas() {
  const c = canvas.value
  // 根据容器宽度设置像素尺寸，提高清晰度
  const dpr = Math.max(window.devicePixelRatio || 1, 1)
  const cssWidth = c.clientWidth || 600
  const cssHeight = 240
  c.width = cssWidth * dpr
  c.height = cssHeight * dpr
  c.style.width = cssWidth + 'px'
  c.style.height = cssHeight + 'px'
  ctx = c.getContext('2d')
  ctx.scale(dpr, dpr)
  ctx.lineWidth = 2
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.strokeStyle = '#000'
}

onMounted(() => {
  initCanvas()
  window.addEventListener('resize', initCanvas)
})

function getPos(e) {
  const rect = canvas.value.getBoundingClientRect()
  return [e.clientX - rect.left, e.clientY - rect.top]
}

function onPointerDown(e) {
  drawing = true
  last = getPos(e)
}

function onPointerMove(e) {
  if (!drawing) return
  const [x, y] = getPos(e)
  ctx.beginPath()
  ctx.moveTo(last[0], last[1])
  ctx.lineTo(x, y)
  ctx.stroke()
  last = [x, y]
}

function onPointerUp() {
  drawing = false
  last = null
}

function onTouchStart(e) {
  const t = e.touches[0]
  onPointerDown({ clientX: t.clientX, clientY: t.clientY })
}
function onTouchMove(e) {
  const t = e.touches[0]
  onPointerMove({ clientX: t.clientX, clientY: t.clientY })
}
function onTouchEnd() { onPointerUp() }

function clear() {
  const c = canvas.value
  ctx.clearRect(0, 0, c.width, c.height)
}

function confirm() {
  // 导出 PNG Blob
  canvas.value.toBlob(blob => {
    emits('confirm', blob)
    // 确认后自动清除画布
    clear()
  }, 'image/png')
}

// 暴露方法给父组件
defineExpose({ clear })
</script>

<style scoped>
.sig-wrap { border: 1px dashed #c0c4cc; padding: 8px; background: #fff; }
canvas { width: 100%; height: 240px; background: #fff; touch-action: none; }
.ops { margin-top: 8px; display: flex; gap: 8px; }
</style>

