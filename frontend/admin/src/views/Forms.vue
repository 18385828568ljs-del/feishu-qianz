<template>
  <div class="page-container">
    <!-- 搜索栏 -->
    <el-card class="filter-card">
      <div class="filter-header">
        <span class="title">表单管理</span>
        <div class="filter-actions">
          <el-input
            v-model="searchText"
            placeholder="搜索表单名称"
            clearable
            style="width: 240px"
            @keyup.enter="loadData"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button type="primary" @click="loadData">查询</el-button>
        </div>
      </div>
    </el-card>

    <!-- 数据表格 -->
    <el-card class="table-card">
      <el-table :data="tableData" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="form_id" label="表单ID" width="120" show-overflow-tooltip>
          <template #default="{ row }">
             <span class="code-font">{{ row.form_id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="表单名称" min-width="200" show-overflow-tooltip>
           <template #default="{ row }">
             <span style="font-weight: 500;">{{ row.name }}</span>
           </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="submit_count" label="提交数" width="100" align="center">
          <template #default="{ row }">
            <el-tag type="info" effect="plain">{{ row.submit_count }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              inline-prompt
              active-text="启用"
              inactive-text="停用"
              :loading="row.statusLoading"
              @change="(val) => handleStatusChange(row, val)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" align="center">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="copyShareLink(row)">
              <el-icon style="margin-right: 4px"><Link /></el-icon> 复制链接
            </el-button>
            <el-button link type="danger" @click="handleDelete(row)">
              <el-icon style="margin-right: 4px"><Delete /></el-icon> 删除
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
import { getForms, updateFormStatus, deleteForm } from '../services/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Link, Delete } from '@element-plus/icons-vue'

const loading = ref(false)
const searchText = ref('')
const tableData = ref([])
const pagination = ref({ page: 1, pageSize: 20, total: 0 })

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

async function loadData() {
  loading.value = true
  try {
    const data = await getForms(pagination.value.page, pagination.value.pageSize, searchText.value)
    tableData.value = data.items.map(item => ({ ...item, statusLoading: false })) // Add statusLoading state
    pagination.value.total = data.total
  } catch (error) {
    ElMessage.error('加载表单列表失败')
  } finally {
    loading.value = false
  }
}

async function handleStatusChange(row, newVal) {
  row.statusLoading = true
  try {
    await updateFormStatus(row.form_id, newVal)
    ElMessage.success('状态更新成功')
  } catch (error) {
    ElMessage.error('更新失败')
    row.is_active = !newVal // Revert on failure
  } finally {
    row.statusLoading = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      '确定要删除该表单吗？删除后，已发布的外部链接将失效。',
      '永久删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    await deleteForm(row.form_id)
    ElMessage.success('表单已删除')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除表单失败')
    }
  }
}

function copyShareLink(row) {
  // Use a configurable base URL or window.location.origin, assuming main app is on port 5173 or current origin
  // If admin is on 5174 and main app on 5173, we might need a way to know main app URL.
  // For now, let's assume they might be on same domain in prod or let the user configure.
  // Let's use localhost:5173 for dev environment guess if on 5174
  
  let baseUrl = window.location.origin
  if (baseUrl.includes(':5174')) {
    baseUrl = baseUrl.replace(':5174', ':5173')
  }
  
  const url = `${baseUrl}/sign/${row.form_id}`
  navigator.clipboard.writeText(url)
  ElMessage.success('链接已复制')
}

onMounted(loadData)
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-card {
  border: none;
}

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.filter-actions {
  display: flex;
  gap: 12px;
}

.table-card {
  border: none;
  min-height: 500px;
}

.code-font {
  font-family: 'Consolas', monospace;
  color: var(--el-color-primary);
  background: rgba(30, 128, 255, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
}

.pagination-container {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
}
</style>
