<template>
  <div class="page-container">
    <!-- 顶部操作栏 -->
    <el-card class="filter-card">
      <div class="filter-header">
        <span class="title">定价方案管理</span>
        <div class="header-actions">
          <el-switch
            v-model="showInactive"
            inline-prompt
            active-text="显示已下架"
            inactive-text="仅显示上架"
            @change="loadData"
            style="margin-right: 12px"
          />
          <el-button type="primary" @click="openCreateDialog">
            <el-icon class="mr-1"><Plus /></el-icon>创建套餐
          </el-button>
        </div>
      </div>
    </el-card>
    
    <!-- 数据表格 -->
    <el-card class="table-card">
      <el-table :data="tableData" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="plan_id" label="套餐ID" width="150" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="primary">{{ row.plan_id }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="套餐名称" min-width="180">
          <template #default="{ row }">
            <span class="plan-name">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="quota_count" label="签名次数" width="120" align="center">
          <template #default="{ row }">
            <span class="quota-badge">{{ row.quota_count }} 次</span>
          </template>
        </el-table-column>
        <el-table-column prop="price" label="价格" width="140" align="center">
          <template #default="{ row }">
            <span class="price">¥{{ (row.price / 100).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="100" align="center">
          <template #default="{ row }">
            <span class="sort-order">{{ row.sort_order }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.description">{{ row.description }}</span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              inline-prompt
              active-text="上架"
              inactive-text="下架"
              :loading="row.statusLoading"
              @change="(val) => handleStatusChange(row, val)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="openEditDialog(row)">
              <el-icon><Edit /></el-icon>
            </el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 创建/编辑套餐对话框 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="isEditing ? '编辑套餐' : '创建新套餐'" 
      width="500px" 
      align-center
    >
      <el-form :model="form" label-position="top" :rules="formRules" ref="formRef">
        <el-form-item label="套餐ID" prop="plan_id" v-if="!isEditing">
          <el-input v-model="form.plan_id" placeholder="例如: pack_10" />
          <div class="form-tip">套餐的唯一标识符，创建后不可修改</div>
        </el-form-item>
        <el-form-item label="套餐名称" prop="name">
          <el-input v-model="form.name" placeholder="例如: 10次签名包" />
        </el-form-item>
        <el-form-item label="签名次数" prop="quota_count">
          <el-input-number v-model="form.quota_count" :min="1" :max="10000" style="width: 100%" />
        </el-form-item>
        <el-form-item label="价格（元）" prop="price">
          <el-input-number 
            v-model="priceYuan" 
            :min="0.01" 
            :max="10000" 
            :precision="2" 
            :step="0.1"
            style="width: 100%" 
          />
          <div class="form-tip">实际存储价格：{{ form.price }} 分</div>
        </el-form-item>
        <el-form-item label="排序" prop="sort_order">
          <el-input-number v-model="form.sort_order" :min="0" :max="999" style="width: 100%" />
          <div class="form-tip">数字越小越靠前</div>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="选填，套餐说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          {{ isEditing ? '保存修改' : '立即创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getPricing, createPricing, updatePricing, deletePricing } from '../services/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'

const loading = ref(false)
const submitting = ref(false)
const showInactive = ref(false)
const tableData = ref([])
const dialogVisible = ref(false)
const isEditing = ref(false)
const formRef = ref(null)

const form = ref({
  plan_id: '',
  name: '',
  quota_count: 10,
  price: 990, // 以分为单位
  sort_order: 0,
  description: ''
})

// 价格转换（分 <-> 元）
const priceYuan = computed({
  get: () => form.value.price / 100,
  set: (val) => { form.value.price = Math.round(val * 100) }
})

const formRules = {
  plan_id: [{ required: true, message: '请输入套餐ID', trigger: 'blur' }],
  name: [{ required: true, message: '请输入套餐名称', trigger: 'blur' }],
  quota_count: [{ required: true, message: '请输入签名次数', trigger: 'blur' }],
  price: [{ required: true, message: '请输入价格', trigger: 'blur' }]
}

async function loadData() {
  loading.value = true
  try {
    const data = await getPricing(showInactive.value)
    tableData.value = data.items.map(item => ({ ...item, statusLoading: false }))
  } catch (error) {
    ElMessage.error('加载定价方案失败')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  isEditing.value = false
  form.value = {
    plan_id: '',
    name: '',
    quota_count: 10,
    price: 990,
    sort_order: 0,
    description: ''
  }
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEditing.value = true
  form.value = {
    plan_id: row.plan_id,
    name: row.name,
    quota_count: row.quota_count,
    price: row.price,
    sort_order: row.sort_order,
    description: row.description || ''
  }
  dialogVisible.value = true
}

async function submitForm() {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    submitting.value = true
    try {
      if (isEditing.value) {
        await updatePricing(form.value.plan_id, {
          name: form.value.name,
          quota_count: form.value.quota_count,
          price: form.value.price,
          sort_order: form.value.sort_order,
          description: form.value.description
        })
        ElMessage.success('套餐更新成功')
      } else {
        await createPricing(form.value)
        ElMessage.success('套餐创建成功')
      }
      dialogVisible.value = false
      loadData()
    } catch (error) {
      ElMessage.error(isEditing.value ? '更新失败' : '创建失败')
    } finally {
      submitting.value = false
    }
  })
}

async function handleStatusChange(row, newVal) {
  row.statusLoading = true
  try {
    await updatePricing(row.plan_id, { is_active: newVal })
    ElMessage.success(newVal ? '套餐已上架' : '套餐已下架')
  } catch (error) {
    ElMessage.error('更新状态失败')
    row.is_active = !newVal
  } finally {
    row.statusLoading = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除套餐 "${row.name}" 吗？此操作不可恢复。`,
      '警告',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    await deletePricing(row.plan_id)
    ElMessage.success('套餐已删除')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
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

.header-actions {
  display: flex;
  align-items: center;
}

.table-card {
  min-height: 500px;
}

.plan-name {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 14px;
}

.quota-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  background: #e8f3ff;
  color: var(--el-color-primary);
  border-radius: 4px;
  font-weight: 600;
  font-size: 13px;
  font-family: 'DIN Alternate', 'Roboto', sans-serif;
}

.price {
  font-family: 'DIN Alternate', 'Roboto', sans-serif;
  font-weight: 700;
  color: var(--el-color-success);
  font-size: 16px;
}

.sort-order {
  font-family: 'Consolas', monospace;
  font-weight: 500;
  color: var(--text-secondary);
  background: #f2f3f5;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
}

.text-gray {
  color: var(--text-secondary);
}

.form-tip {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
  line-height: 1.4;
}

.mr-1 {
  margin-right: 4px;
}
</style>
