<script setup>
import { useRoute } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()
// 只在主页显示备案号，分享表单页面不显示
const showFooter = computed(() => route.path === '/')
</script>

<template>
  <div class="app-wrapper">
    <main>
      <router-view />
    </main>
    <footer v-if="showFooter" class="icp-footer">
      <a href="https://beian.miit.gov.cn/" target="_blank">浙ICP备2025220033号-1</a>
    </footer>
  </div>
</template>

<style scoped>
.app-wrapper {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

main {
  padding: 0;
  flex: 1; /* 让内容区域占据剩余空间 */
}

.icp-footer {
  text-align: center;
  padding: 12px;
  background-color: transparent; /* 透明背景，融入页面 */
  font-size: 12px;
  color: #9ca3af; /* 浅灰色 */
  margin-top: auto; /* 确保在内容不足时位于底部 */
}

.icp-footer a {
  text-decoration: none;
  color: inherit;
  transition: color 0.2s;
}

.icp-footer a:hover {
  color: #6b7280;
  text-decoration: underline;
}
</style>

