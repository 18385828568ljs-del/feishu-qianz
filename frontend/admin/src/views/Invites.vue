<template>
  <div class="page-container">
    <!-- 顶部操作栏 -->
    <el-card class="filter-card">
      <div class="filter-header">
        <span class="title">邀请码管理</span>
        <div class="header-actions">
          <el-button type="success" @click="handleExport" class="mr-1">
            <el-icon class="mr-1"><Download /></el-icon>导出 Excel
          </el-button>
          <el-button type="primary" @click="openCreateDialog">
            <el-icon class="mr-1"><Plus /></el-icon>创建邀请码
          </el-button>
        </div>
      </div>
    </el-card>
    
    <!-- 数据表格 -->
    <el-card class="table-card">
      <el-table :data="tableData" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="code" label="邀请码" min-width="200">
          <template #default="{ row }">
            <el-tooltip content="点击复制" placement="top">
              <span class="code-tag" @click="copyCode(row.code)">
                {{ row.code }}
                <el-icon class="copy-icon"><CopyDocument /></el-icon>
              </span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="benefit_days" label="权益时长" width="150" align="center">
           <template #default="{ row }">
             <span class="benefit-days">{{ row.benefit_days }} 天</span>
           </template>
        </el-table-column>
        <el-table-column prop="expires_at" label="领取截止日期" min-width="180" align="center">
          <template #default="{ row }">
            <span :class="isExpired(row.expires_at) ? 'expired-text' : ''">
               {{ row.expires_at ? formatDate(row.expires_at) : '永久有效' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="150" align="center">
          <template #default="{ row }">
             <el-switch
              v-model="row.is_active"
              inline-prompt
              active-text="有效"
              inactive-text="禁用"
              :loading="row.statusLoading"
              @change="(val) => handleStatusChange(row, val)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="200" align="center">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center" fixed="right">
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
    
    <!-- 创建邀请码对话框 -->
    <el-dialog v-model="createDialogVisible" title="创建新邀请码" width="400px" align-center>
      <el-form label-position="top">
        <el-form-item label="体验时长(天)">
          <el-input-number v-model="createForm.benefitDays" :min="1" :max="3650" style="width: 100%" />
          <div class="form-tip">用户兑换后可以免费体验的天数</div>
        </el-form-item>
        <el-form-item label="邀请码有效期(天)">
          <el-input-number v-model="createForm.expiresInDays" :min="1" :max="365" style="width: 100%" />
          <div class="form-tip">邀请码本身的有效期，过期后无法兑换</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createInviteCode" :loading="creating">立即创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getInvites, createInvite, updateInviteStatus, deleteInvite, getInviteExportUrl } from '../services/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, CopyDocument, Download, Delete } from '@element-plus/icons-vue'

const loading = ref(false)
const creating = ref(false)
const tableData = ref([])
const pagination = ref({ page: 1, pageSize: 20, total: 0 })

const createDialogVisible = ref(false)
const createForm = ref({
  benefitDays: 365,
  expiresInDays: 30
})

function formatDate(dateStr) {
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
    const data = await getInvites(pagination.value.page, pagination.value.pageSize)
    tableData.value = data.items.map(item => ({ ...item, statusLoading: false }))
    pagination.value.total = data.total
  } catch (error) {
    ElMessage.error('加载邀请码列表失败')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  createForm.value = { benefitDays: 365, expiresInDays: 30 }
  createDialogVisible.value = true
}

async function createInviteCode() {
  creating.value = true
  try {
    const result = await createInvite(
      99999, // 硬编码一个极大次数，表示无限使用
      createForm.value.benefitDays,
      createForm.value.expiresInDays
    )
    ElMessage.success('邀请码创建成功')
    createDialogVisible.value = false
    loadData()
  } catch (error) {
    ElMessage.error('创建失败')
  } finally {
    creating.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除邀请码 ${row.code} 吗？`, '警告', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    
    await deleteInvite(row.id)
    ElMessage.success('邀请码已删除')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
        ElMessage.error('删除失败')
    }
  }
}

function handleExport() {
  const url = getInviteExportUrl()
  window.open(url, '_blank')
}

async function handleStatusChange(row, newVal) {
  // 如果是禁用操作，弹出确认框询问是否撤销权益
  if (!newVal) {
    try {
      const action = await ElMessageBox.confirm(
        '禁用邀请码后，新用户将无法使用此邀请码。\n\n是否同时撤销已兑换用户的 VIP 权益？',
        '禁用邀请码',
        {
          distinguishCancelButton: true,
          confirmButtonText: '禁用并撤销权益',
          cancelButtonText: '仅禁用',
          type: 'warning',
        }
      ).catch(action => action)
      
      if (action === 'cancel') {
        // 用户点击"仅禁用"
        row.statusLoading = true
        try {
          const result = await updateInviteStatus(row.id, false, false)
          ElMessage.success('邀请码已禁用')
        } catch (error) {
          ElMessage.error('更新失败')
          row.is_active = true
        } finally {
          row.statusLoading = false
        }
      } else if (action === 'confirm') {
        // 用户点击"禁用并撤销权益"
        row.statusLoading = true
        try {
          const result = await updateInviteStatus(row.id, false, true)
          if (result.revoked_count > 0) {
            ElMessage.success(`邀请码已禁用，已撤销 ${result.revoked_count} 位用户的 VIP 权益`)
          } else {
            ElMessage.success('邀请码已禁用')
          }
        } catch (error) {
          ElMessage.error('更新失败')
          row.is_active = true
        } finally {
          row.statusLoading = false
        }
      } else {
        // 用户点击关闭按钮
        row.is_active = true
      }
    } catch (e) {
      row.is_active = true
    }
  } else {
    // 启用操作，直接执行
    row.statusLoading = true
    try {
      await updateInviteStatus(row.id, true, false)
      ElMessage.success('邀请码已启用')
    } catch (error) {
      ElMessage.error('更新失败')
      row.is_active = false
    } finally {
      row.statusLoading = false
    }
  }
}

function copyCode(code) {
  navigator.clipboard.writeText(code)
  ElMessage.success('邀请码已复制')
}

onMounted(loadData)
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-card { border: none; }
.table-card { border: none; min-height: 500px; }

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

.code-tag {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  background: #f2f3f5;
  border-radius: 4px;
  font-family: 'Consolas', monospace;
  font-weight: 600;
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.2s;
}

.code-tag:hover {
  background: #e5e6eb;
  color: var(--el-color-primary);
}

.copy-icon {
  margin-left: 6px;
  font-size: 12px;
  opacity: 0.5;
}

.expired-text {
  color: var(--el-color-danger);
  text-decoration: line-through;
}

.form-tip {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.benefit-days {
  font-weight: 600;
  color: var(--el-color-success);
}

.mr-1 { margin-right: 4px; }

.pagination-container {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
}
</style>
