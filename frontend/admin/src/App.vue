<template>
  <div class="admin-app">
    <!-- 登录页面不显示侧边栏 -->
    <template v-if="route.path === '/login'">
      <router-view />
    </template>
    
    <!-- 主布局 -->
    <template v-else>
      <el-container class="layout-container">
        <!-- 侧边栏 -->
        <el-aside width="240px" class="sidebar">
          <div class="logo">
            <div class="logo-icon">
              <el-icon :size="20"><ElementPlus /></el-icon>
            </div>
            <span class="logo-text">后台管理系统</span>
          </div>
          
          <el-menu
            :default-active="route.path"
            router
            class="sidebar-menu"
            :unique-opened="true"
          >
            <el-menu-item 
              v-for="item in menuItems" 
              :key="item.path"
              :index="item.path"
            >
              <el-icon><component :is="item.icon" /></el-icon>
              <span>{{ item.title }}</span>
            </el-menu-item>
          </el-menu>
          
          <div class="sidebar-footer">
            <div class="user-info-mini">
              <el-avatar :size="32" icon="UserFilled" class="user-avatar" />
              <span class="username">管理员</span>
            </div>
            <el-button link type="danger" @click="handleLogout">
              <el-icon><SwitchButton /></el-icon>
            </el-button>
          </div>
        </el-aside>
        
        <!-- 主内容区 -->
        <el-container class="main-container">
          <el-header class="header">
            <div class="header-left">
              <!-- 面包屑导航 -->
              <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
                <el-breadcrumb-item v-if="route.path !== '/'">{{ currentPageTitle }}</el-breadcrumb-item>
              </el-breadcrumb>
            </div>
            
            <div class="header-right">
              <el-tooltip content="文档" placement="bottom">
                <el-button circle text>
                  <el-icon><QuestionFilled /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="通知" placement="bottom">
                <el-button circle text>
                  <el-icon><Bell /></el-icon>
                </el-button>
              </el-tooltip>
              
              <el-dropdown trigger="click" @command="handleCommand">
                <div class="user-profile">
                  <el-avatar :size="32" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" />
                  <span class="username">Admin</span>
                  <el-icon><CaretBottom /></el-icon>
                </div>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="password">
                      <el-icon><Key /></el-icon> 修改密码
                    </el-dropdown-item>
                    <el-dropdown-item divided command="logout" style="color: #f53f3f;">
                      <el-icon><SwitchButton /></el-icon> 退出登录
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </el-header>
          
          <el-main class="main-content">
            <transition name="fade-transform" mode="out-in">
              <router-view />
            </transition>
          </el-main>
        </el-container>
      </el-container>
    </template>
    
    <!-- 修改密码对话框 -->
    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="400px" align-center>
      <el-form label-position="top">
        <el-form-item label="旧密码" required>
          <el-input v-model="passwordForm.oldPassword" type="password" show-password placeholder="请输入当前密码" />
        </el-form-item>
        <el-form-item label="新密码" required>
          <el-input v-model="passwordForm.newPassword" type="password" show-password placeholder="请输入新密码（至少6位）" />
        </el-form-item>
        <el-form-item label="确认新密码" required>
          <el-input v-model="passwordForm.confirmPassword" type="password" show-password placeholder="请再次输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitPasswordChange" :loading="passwordLoading">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { routes } from './router'
import { logout, changePassword, setAdminToken } from './services/api'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()

// 菜单项（排除登录页）
const menuItems = computed(() => 
  routes
    .filter(r => r.meta?.title)
    .map(r => ({
      path: r.path,
      title: r.meta.title,
      icon: r.meta.icon
    }))
)

// 当前页面标题
const currentPageTitle = computed(() => {
  const current = routes.find(r => r.path === route.path)
  return current?.meta?.title || '页面'
})

// 修改密码相关
const passwordDialogVisible = ref(false)
const passwordLoading = ref(false)
const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

// 处理下拉菜单命令
function handleCommand(command) {
  if (command === 'logout') {
    handleLogout()
  } else if (command === 'password') {
    passwordForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
    passwordDialogVisible.value = true
  }
}

// 提交修改密码
async function submitPasswordChange() {
  const { oldPassword, newPassword, confirmPassword } = passwordForm.value
  
  if (!oldPassword || !newPassword || !confirmPassword) {
    ElMessage.warning('请填写所有字段')
    return
  }
  
  if (newPassword.length < 6) {
    ElMessage.warning('新密码至少6位')
    return
  }
  
  if (newPassword !== confirmPassword) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  
  passwordLoading.value = true
  try {
    await changePassword(oldPassword, newPassword)
    ElMessage.success('密码修改成功，请使用新密码重新登录')
    passwordDialogVisible.value = false
    
    // 强制退出登录
    handleLogout()
  } catch (error) {
    const msg = error.response?.data?.detail || '密码修改失败'
    ElMessage.error(msg)
  } finally {
    passwordLoading.value = false
  }
}

// 退出登录
function handleLogout() {
  logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.admin-app {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.layout-container {
  height: 100%;
}

/* 侧边栏样式 */
.sidebar {
  background-color: var(--sidebar-bg);
  color: #fff;
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  z-index: 100;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  background-color: rgba(255, 255, 255, 0.05);
  margin-bottom: 8px;
}

.logo-icon {
  width: 32px;
  height: 32px;
  background: var(--el-color-primary);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  color: white;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.5px;
  color: #fff;
  white-space: nowrap;
}

.sidebar-menu {
  flex: 1;
  border-right: none !important;
  background: transparent !important;
  padding: 8px;
}

/* 深度选择器覆盖 Element Plus 菜单样式 */
:deep(.el-menu) {
  background-color: transparent;
  border-right: none;
}

:deep(.el-menu-item) {
  height: 50px;
  line-height: 50px;
  margin-bottom: 4px;
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.7) !important;
}

:deep(.el-menu-item:hover) {
  background-color: rgba(255, 255, 255, 0.1) !important;
  color: #fff !important;
}

:deep(.el-menu-item.is-active) {
  background-color: var(--el-color-primary) !important;
  color: #fff !important;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(30, 128, 255, 0.3);
}

:deep(.el-menu-item .el-icon) {
  font-size: 18px;
  margin-right: 12px;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(0, 0, 0, 0.1);
}

.user-info-mini {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-info-mini .username {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.9);
}

/* 主容器样式 */
.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-color);
  overflow: hidden;
}

.header {
  height: 64px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  z-index: 99;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}

.user-profile:hover {
  background-color: #f7f8fa;
}

.user-profile .username {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
}

.main-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  position: relative;
}

/* 页面切换动画 */
.fade-transform-enter-active,
.fade-transform-leave-active {
  transition: all 0.3s;
}

.fade-transform-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}

.fade-transform-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>
