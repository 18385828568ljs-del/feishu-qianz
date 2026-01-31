<template>
  <div class="login-wrapper">
    <div class="login-container">
      <div class="login-left">
        <div class="login-welcome">
          <h2>飞书签名插件</h2>
          <p>Feishu Signature Plugin</p>
          <div class="welcome-img">
            <el-icon :size="120" color="rgba(255,255,255,0.8)"><EditPen /></el-icon>
          </div>
          <p class="desc">高效、安全、便捷的电子签名解决方案</p>
        </div>
      </div>
      
      <div class="login-right">
        <div class="login-form-box">
          <div class="form-header">
            <h3>管理员登录</h3>
            <p>请输入账号和密码进入管理后台</p>
          </div>
          
          <el-form @submit.prevent="handleLogin" class="login-form" size="large">
            <el-form-item>
              <el-input
                v-model="username"
                placeholder="请输入账号"
                :prefix-icon="User"
              />
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="password"
                type="password"
                placeholder="请输入密码"
                show-password
                :prefix-icon="Lock"
              />
            </el-form-item>
            
            <el-form-item>
              <el-button 
                type="primary" 
                class="login-btn" 
                :loading="loading"
                native-type="submit"
                auto-insert-space
              >
                登 录
              </el-button>
            </el-form-item>
          </el-form>
          

        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, EditPen } from '@element-plus/icons-vue'
import { setAdminCredentials, getDashboard } from '../services/api'

const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)

async function handleLogin() {
  if (!username.value || !password.value) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  
  loading.value = true
  
  try {
    setAdminCredentials(username.value, password.value)
    await getDashboard()
    ElMessage.success('登录成功')
    router.push('/')
  } catch (error) {
    ElMessage.error('账号或密码错误')
    setAdminCredentials('', '')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrapper {
  height: 100vh;
  width: 100vw;
  background: #f0f2f5;
  display: flex;
  align-items: center;
  justify-content: center;
  background-image: url('https://gw.alipayobjects.com/zos/rmsportal/TVYTbAXWheQpRcWDaDMu.svg');
  background-repeat: no-repeat;
  background-position: center 110px;
  background-size: 100%;
}

.login-container {
  width: 900px;
  height: 500px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
  display: flex;
  overflow: hidden;
}

.login-left {
  flex: 1;
  background: linear-gradient(135deg, #1e80ff 0%, #0052cc 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  position: relative;
}

.login-welcome {
  text-align: center;
  z-index: 2;
}

.login-welcome h2 {
  font-size: 28px;
  margin-bottom: 8px;
}

.login-welcome p {
  font-size: 16px;
  opacity: 0.8;
}

.welcome-img {
  margin: 40px 0;
}

.login-welcome .desc {
  font-size: 14px;
  opacity: 0.6;
}

.login-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.login-form-box {
  width: 100%;
  max-width: 320px;
}

.form-header {
  margin-bottom: 32px;
}

.form-header h3 {
  font-size: 24px;
  color: #1d2129;
  margin-bottom: 8px;
}

.form-header p {
  color: #86909c;
  font-size: 14px;
}

.login-btn {
  width: 100%;
  height: 40px;
  font-size: 16px;
  border-radius: 8px;
}

.form-footer {
  margin-top: 24px;
  text-align: center;
  font-size: 13px;
  color: #86909c;
}
</style>
