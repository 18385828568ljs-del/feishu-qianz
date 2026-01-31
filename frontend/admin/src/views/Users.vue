<template>
  <div class="page-container">
    <!-- 搜索栏 -->
    <el-card class="filter-card">
      <div class="filter-header">
        <span class="title">用户列表</span>
        <div class="filter-actions">
          <el-input
            v-model="searchText"
            placeholder="搜索 Open ID"
            clearable
            style="width: 240px"
            @keyup.enter="loadData"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button type="success" @click="handleExport">
            <el-icon class="mr-1"><Download /></el-icon>导出 Excel
          </el-button>
        </div>
      </div>
    </el-card>
    
    <!-- 数据表格 -->
    <el-card class="table-card">
      <el-table :data="tableData" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="open_id" label="Open ID" min-width="200" show-overflow-tooltip />
        <el-table-column prop="remaining_quota" label="免费次数" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.remaining_quota > 0 ? 'success' : 'danger'" effect="dark">
              {{ row.remaining_quota }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_used" label="使用次数" width="100" align="center" />
        <el-table-column prop="invite_code_used" label="邀请码" width="120" align="center">
          <template #default="{ row }">
            <span v-if="row.invite_code_used">{{ row.invite_code_used }}</span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="invite_expire_at" label="体验到期" min-width="150" align="center">
          <template #default="{ row }">
            <span v-if="row.invite_expire_at" :class="isExpired(row.invite_expire_at) ? 'expired-text' : 'vip-text'">
              {{ formatDateShort(row.invite_expire_at) }}
            </span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_paid" label="累计付费" width="120" align="center">
          <template #default="{ row }">
            <span class="price">¥{{ (row.total_paid / 100).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" min-width="180" align="center">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="openQuotaDialog(row)" circle>
              <el-icon><Edit /></el-icon>
            </el-button>
            <el-button type="warning" size="small" @click="handleReset(row)" circle title="初始化数据">
              <el-icon><Refresh /></el-icon>
            </el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)" circle>
              <el-icon><Delete /></el-icon>
            </el-button>
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
    
    <!-- 调整配额对话框 -->
    <el-dialog v-model="quotaDialogVisible" title="调整用户配额" width="400px" align-center>
      <el-form label-position="top">
        <el-form-item label="用户">
          <el-input :value="selectedUser?.open_id" disabled />
        </el-form-item>
        <el-form-item label="当前配额">
          <div class="current-quota">{{ selectedUser?.remaining_quota }} 次</div>
        </el-form-item>
        <el-form-item label="新配额">
          <el-input-number v-model="newQuota" :min="0" :max="100000" style="width: 100%" />
          <div class="form-tip">设置用户的剩余签名次数</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="quotaDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitQuotaChange" :loading="quotaUpdating">确定修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getUsers, deleteUser, getUserExportUrl, updateUserQuota, resetUser } from '../services/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Download, Delete, Edit, Refresh } from '@element-plus/icons-vue'

const loading = ref(false)
const searchText = ref('')
const tableData = ref([])
const pagination = ref({ page: 1, pageSize: 20, total: 0 })

const quotaDialogVisible = ref(false)
const quotaUpdating = ref(false)
const selectedUser = ref(null)
const newQuota = ref(0)

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

function formatDateShort(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

function isExpired(dateStr) {
  if (!dateStr) return false
  return new Date(dateStr) < new Date()
}

async function loadData() {
  loading.value = true
  try {
    const data = await getUsers(pagination.value.page, pagination.value.pageSize, searchText.value)
    tableData.value = data.items
    pagination.value.total = data.total
  } catch (error) {
    ElMessage.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除用户 ${row.open_id} 吗？删除后其所有记录将无法找回。`, '警告', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    
    await deleteUser(row.id)
    ElMessage.success('用户已删除')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
        ElMessage.error('删除失败')
    }
  }
}

function handleExport() {
  const url = getUserExportUrl()
  window.open(url, '_blank')
}

function openQuotaDialog(user) {
  selectedUser.value = user
  newQuota.value = user.remaining_quota
  quotaDialogVisible.value = true
}

async function submitQuotaChange() {
  if (!selectedUser.value) return
  
  quotaUpdating.value = true
  try {
    await updateUserQuota(selectedUser.value.id, newQuota.value)
    ElMessage.success('配额已更新')
    quotaDialogVisible.value = false
    loadData()
  } catch (error) {
    ElMessage.error('更新配额失败')
  } finally {
    quotaUpdating.value = false
  }
}

async function handleReset(row) {
  try {
    await ElMessageBox.confirm(
      `确定要初始化用户 ${row.open_id} 的数据吗？\n操作将重置：剩余次数(20)、已用次数(0)、清空邀请码、清空付费记录。`,
      '危险操作',
      {
        confirmButtonText: '确定初始化',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    await resetUser(row.id)
    ElMessage.success('用户数据已初始化')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
        ElMessage.error('初始化失败')
    }
  }
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
  gap: 12px;
}

.search-input {
  width: 300px;
}

.table-card {
  min-height: 500px;
}

.text-gray {
  color: var(--text-secondary);
}

.vip-text {
  color: var(--el-color-warning);
  font-weight: 500;
}

.expired-text {
  color: var(--text-secondary);
  text-decoration: line-through;
}

.pagination-container {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
  border-top: 1px solid #f2f3f5;
}

.current-quota {
  font-size: 20px;
  font-weight: 600;
  color: var(--el-color-primary);
  font-family: 'DIN Alternate', 'Roboto', sans-serif;
}

.price {
  font-family: 'DIN Alternate', 'Roboto', sans-serif;
  font-weight: 600;
  color: var(--text-primary);
  font-size: 14px;
}

.form-tip {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.mr-1 {
  margin-right: 4px;
}
</style>
