<template>
  <div class="page-container">
    <!-- 顶部筛选栏 -->
    <el-card class="filter-card">
      <div class="filter-header">
        <span class="title">订单管理</span>
        <div class="filter-actions">
          <el-select v-model="statusFilter" placeholder="订单状态" clearable style="width: 150px" @change="loadData">
            <el-option label="全部" value="" />
            <el-option label="待支付" value="pending" />
            <el-option label="已支付" value="paid" />
            <el-option label="已取消" value="cancelled" />
            <el-option label="已过期" value="expired" />
          </el-select>
          <el-button type="success" @click="handleExport">
            <el-icon class="mr-1"><Download /></el-icon>导出 Excel
          </el-button>
        </div>
      </div>
    </el-card>
    
    <!-- 数据表格 -->
    <el-card class="table-card">
      <el-table :data="tableData" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="order_id" label="订单号" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="order-id">{{ row.order_id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="user_key" label="用户" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <el-tooltip :content="row.user_key" placement="top">
              <span class="user-key">{{ row.user_key.split('::')[0].substring(0, 12) }}...</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="plan_id" label="套餐" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.plan_id }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="quota_count" label="次数" width="100" align="center">
          <template #default="{ row }">
            <span class="quota-count">{{ row.quota_count }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" width="120" align="center">
          <template #default="{ row }">
            <span class="amount">¥{{ (row.amount / 100).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" effect="dark">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="payment_method" label="支付方式" width="120" align="center">
          <template #default="{ row }">
            <span>{{ getPaymentMethod(row.payment_method) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="180" align="center">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="paid_at" label="支付时间" min-width="180" align="center">
          <template #default="{ row }">
            <span v-if="row.paid_at">{{ formatDate(row.paid_at) }}</span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadData"
          @current-change="loadData"
          background
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getOrders } from '../services/api'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'

const loading = ref(false)
const statusFilter = ref('')
const tableData = ref([])
const pagination = ref({ page: 1, pageSize: 20, total: 0 })

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

function getStatusType(status) {
  const statusMap = {
    pending: 'warning',
    paid: 'success',
    cancelled: 'info',
    expired: 'danger'
  }
  return statusMap[status] || 'info'
}

function getStatusText(status) {
  const statusMap = {
    pending: '待支付',
    paid: '已支付',
    cancelled: '已取消',
    expired: '已过期'
  }
  return statusMap[status] || status
}

function getPaymentMethod(method) {
  const methodMap = {
    mock: '模拟支付',
    wechat: '微信支付',
    alipay: '支付宝',
    yungouos: 'YunGouOS'
  }
  return methodMap[method] || method
}

async function loadData() {
  loading.value = true
  try {
    const data = await getOrders(pagination.value.page, pagination.value.pageSize, statusFilter.value)
    tableData.value = data.items
    pagination.value.total = data.total
  } catch (error) {
    ElMessage.error('加载订单列表失败')
  } finally {
    loading.value = false
  }
}

function handleExport() {
  ElMessage.info('订单导出功能开发中...')
  // TODO: 实现订单导出功能
}

onMounted(loadData)
</script>

<style scoped>
.page-container {
  max-width: 1600px;
  margin: 0 auto;
}

.filter-card {
  margin-bottom: 24px;
}

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 装饰性标题前缀 */
.title::before {
  content: '';
  width: 4px;
  height: 18px;
  background: var(--el-color-primary);
  border-radius: 2px;
  display: block;
}

.filter-actions {
  display: flex;
  gap: 16px;
  align-items: center;
}

.table-card {
  min-height: 500px;
}

.order-id {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
  background: #f2f3f5;
  padding: 2px 6px;
  border-radius: 4px;
}

.user-key {
  font-size: 13px;
  color: var(--text-secondary);
}

.quota-count {
  font-weight: 600;
  color: var(--el-color-primary);
  font-family: 'DIN Alternate', 'Roboto', sans-serif;
}

.amount {
  font-family: 'DIN Alternate', 'Roboto', sans-serif;
  font-weight: 600;
  color: var(--el-color-success);
  font-size: 15px;
}

.text-gray {
  color: var(--text-secondary);
}

.mr-1 {
  margin-right: 4px;
}

.pagination-container {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
  border-top: 1px solid #f2f3f5;
}
</style>
