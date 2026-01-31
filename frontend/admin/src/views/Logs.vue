<template>
  <div class="page-container">
    <!-- 筛选栏 -->
    <el-card class="filter-card">
      <div class="filter-header">
        <span class="title">签名日志</span>
        <div class="filter-actions">
           <el-input
            v-model="filters.userKey"
            placeholder="用户Key / OpenID"
            clearable
            style="width: 200px"
          >
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
          
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始"
            end-placeholder="结束"
            value-format="YYYY-MM-DD"
            style="width: 240px"
          />
          
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
          <el-button type="success" @click="handleExport">
            <el-icon class="mr-1"><Download /></el-icon>导出 Excel
          </el-button>
          <el-button type="danger" plain @click="handleClear">
            <el-icon class="mr-1"><Delete /></el-icon>清空日志
          </el-button>
        </div>
      </div>
    </el-card>
    
    <!-- 数据表格 -->
    <el-card class="table-card">
      <el-table :data="tableData" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="user_key" label="用户 Key" min-width="200" show-overflow-tooltip>
           <template #default="{ row }">
             <span class="mono-text">{{ row.user_key }}</span>
           </template>
        </el-table-column>
        <el-table-column prop="file_name" label="文件名" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <el-icon><Document /></el-icon> {{ row.file_name }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120" align="center">
          <template #default>
            <el-tag type="success" effect="light">签字成功</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="签名时间" width="180" align="center">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center" fixed="right">
          <template #default="{ row }">
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getLogs, deleteLog, clearLogs, getLogExportUrl } from '../services/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, Document, Download, Delete } from '@element-plus/icons-vue'

const loading = ref(false)
const tableData = ref([])
const pagination = ref({ page: 1, pageSize: 20, total: 0 })

const filters = ref({
  userKey: '',
  dateRange: null
})

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

async function loadData() {
  loading.value = true
  try {
    const startDate = filters.value.dateRange?.[0] || ''
    const endDate = filters.value.dateRange?.[1] || ''
    
    const data = await getLogs(
      pagination.value.page,
      pagination.value.pageSize,
      filters.value.userKey,
      startDate,
      endDate
    )
    tableData.value = data.items
    pagination.value.total = data.total
  } catch (error) {
    ElMessage.error('加载签名日志失败')
  } finally {
    loading.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定要删除这条签名记录吗？', '提示', {
      type: 'warning'
    })
    await deleteLog(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

async function handleClear() {
  try {
    await ElMessageBox.confirm('确定要清空所有签名记录吗？此操作不可恢复！', '极高风险', {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'danger'
    })
    await clearLogs()
    ElMessage.success('日志已清空')
    loadData()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('清空失败')
  }
}

function handleExport() {
  const startDate = filters.value.dateRange?.[0] || ''
  const endDate = filters.value.dateRange?.[1] || ''
  const url = getLogExportUrl(filters.value.userKey, startDate, endDate)
  window.open(url, '_blank')
}

function resetFilters() {
  filters.value = { userKey: '', dateRange: null }
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-card, .table-card { border: none; }

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.mono-text {
  font-family: 'Consolas', monospace;
  font-size: 12px;
  color: var(--text-regular);
}

.mr-1 { margin-right: 4px; }

.pagination-container {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
}
</style>
