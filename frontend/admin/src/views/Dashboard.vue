<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="24" class="stats-row">
      <el-col :span="6" v-for="(item, index) in statItems" :key="index">
        <div class="stat-card" :class="item.class">
          <div class="stat-content">
            <div class="stat-title">{{ item.label }}</div>
            <div class="stat-value">
              <span v-if="loading">...</span>
              <span v-else>{{ item.value }}</span>
            </div>
            <div class="stat-footer">
              <span class="trend" :class="item.trend > 0 ? 'up' : 'neutral'">
                {{ item.sub }}
              </span>
            </div>
          </div>
          <div class="stat-icon-bg">
            <el-icon><component :is="item.icon" /></el-icon>
          </div>
        </div>
      </el-col>
    </el-row>
    
    <!-- 趋势图表区域 -->
    <el-row :gutter="24">
      <el-col :span="24">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>趋势概览</span>
              <el-radio-group v-model="chartPeriod" size="small" @change="loadTrends">
                <el-radio-button label="week">本周</el-radio-button>
                <el-radio-button label="month">本月</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div v-if="trendsLoading" class="chart-loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>加载中...</span>
          </div>
          <TrendChart 
            v-else
            :dates="trends.dates"
            :users="trends.users"
            :signatures="trends.signatures"
          />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { getDashboard, getTrends } from '../services/api'
import { ElMessage } from 'element-plus'
import TrendChart from '../components/TrendChart.vue'
import { User, Document, Ticket, List, Loading, EditPen, Odometer, Money } from '@element-plus/icons-vue'

const loading = ref(true)
const trendsLoading = ref(true)
const chartPeriod = ref('week')

const stats = ref({
  total_users: 0,
  new_users_today: 0,
  total_signatures: 0,
  signatures_today: 0,
  active_forms: 0,
  total_form_submissions: 0,
  total_invites: 0,
  active_invites: 0,
  total_income: 0,
  income_today: 0
})
const trends = ref({
  dates: [],
  users: [],
  signatures: []
})

const statItems = computed(() => [
  {
    label: '总收入',
    value: `¥${(stats.value.total_income / 100).toFixed(2)}`,
    sub: `今日 +¥${(stats.value.income_today / 100).toFixed(2)}`,
    trend: 1,
    icon: 'Money',
    class: 'income-card'
  },
  {
    label: '总用户数',
    value: stats.value.total_users,
    sub: `今日 +${stats.value.new_users_today}`,
    trend: stats.value.new_users_today > 0 ? 1 : 0,
    icon: 'User',
    class: 'users-card'
  },
  {
    label: '总签名次数',
    value: stats.value.total_signatures,
    sub: `今日 +${stats.value.signatures_today}`,
    trend: stats.value.signatures_today > 0 ? 1 : 0,
    icon: 'EditPen',
    class: 'signatures-card'
  },
  {
    label: '活跃表单',
    value: stats.value.active_forms,
    sub: `总提交 ${stats.value.total_form_submissions}`,
    trend: 0,
    icon: 'Document',
    class: 'forms-card'
  }
])

async function loadStats() {
  loading.value = true
  try {
    const data = await getDashboard()
    stats.value = data
  } catch (error) {
    ElMessage.error('加载统计数据失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

async function loadTrends() {
  trendsLoading.value = true
  try {
    const data = await getTrends(chartPeriod.value)
    trends.value = data
  } catch (error) {
    console.error('加载趋势数据失败:', error)
  } finally {
    trendsLoading.value = false
  }
}

onMounted(() => {
  loadStats()
  loadTrends()
})
</script>

<style scoped>
.dashboard {
  max-width: 1600px;
  margin: 0 auto;
}

.stats-row {
  margin-bottom: 24px;
}

.stat-card {
  position: relative;
  height: 140px;
  border-radius: 12px;
  background: #fff;
  overflow: hidden;
  box-shadow: var(--box-shadow);
  transition: transform 0.3s, box-shadow 0.3s;
  cursor: default;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--box-shadow-hover);
}

.stat-content {
  position: relative;
  z-index: 2;
  padding: 24px;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.stat-title {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.stat-footer {
  font-size: 13px;
  color: var(--text-secondary);
}

.stat-icon-bg {
  position: absolute;
  right: -10px;
  bottom: -10px;
  opacity: 0.1;
  transform: rotate(-15deg) scale(1.5);
  font-size: 100px;
  z-index: 1;
  transition: all 0.3s;
}

.stat-card:hover .stat-icon-bg {
  opacity: 0.2;
  transform: rotate(0) scale(1.6);
}

/* 各卡片颜色 */
.income-card { border-left: 4px solid var(--el-color-warning); }
.income-card .stat-icon-bg { color: var(--el-color-warning); }

.users-card { border-left: 4px solid var(--el-color-primary); }
.users-card .stat-icon-bg { color: var(--el-color-primary); }

.signatures-card { border-left: 4px solid var(--el-color-success); }
.signatures-card .stat-icon-bg { color: var(--el-color-success); }

.forms-card { border-left: 4px solid #909399; }
.forms-card .stat-icon-bg { color: #909399; }

/* 图表和操作卡片 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-loading {
  height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #f9f9f9;
  border-radius: 8px;
  color: #999;
  gap: 12px;
}

.chart-loading .is-loading {
  font-size: 24px;
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
