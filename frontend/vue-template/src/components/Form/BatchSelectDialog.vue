<script setup>
import { ref, watch, onMounted } from 'vue'
import { ElDialog, ElButton, ElTable, ElTableColumn, ElInput, ElCheckbox } from 'element-plus'

const props = defineProps({
  modelValue: Boolean,
  records: {
    type: Array, // [{ id: 'recxxx', name: 'Record Name' }]
    default: () => []
  },
  loading: Boolean
})

const emit = defineEmits(['update:modelValue', 'confirm'])

const searchQuery = ref('')
const selectedRows = ref([])

// Filtered records based on search
const filteredRecords = ref([])

watch([() => props.records, searchQuery], ([newRecords, query]) => {
  if (!query) {
    filteredRecords.value = newRecords
  } else {
    const lower = query.toLowerCase()
    filteredRecords.value = newRecords.filter(r => 
      (r.name || '').toLowerCase().includes(lower)
    )
  }
})

// Update selection when dialog opens or records change
watch(() => props.modelValue, (val) => {
  if (val) {
    selectedRows.value = [] // Reset state
    // Wait for table to render
    setTimeout(() => {
      if (tableRef.value) {
        tableRef.value.clearSelection() // Clear first
        tableRef.value.toggleAllSelection() // Then select all
      }
    }, 100)
  }
})

const tableRef = ref(null)

function handleSelectionChange(val) {
  // val contains the actual row objects provided in :data
  selectedRows.value = val 
}

function handleConfirm() {
  // Sort selected rows by their original index to maintain order
  const selectedIds = selectedRows.value.map(r => r.id)
  
  // Ensure we return IDs in the same order as the original records
  const orderedIds = props.records
    .filter(r => selectedIds.includes(r.id))
    .map(r => r.id)
    
  emit('confirm', orderedIds)
  emit('update:modelValue', false)
}

function handleClose() {
  emit('update:modelValue', false)
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title="选择目标记录"
    width="500px"
    class="batch-select-dialog"
    destroy-on-close
  >
    <div class="dialog-body">
      <div class="search-bar">
        <el-input 
          v-model="searchQuery" 
          placeholder="搜索记录名称..." 
          prefix-icon="Search"
          clearable
        />
      </div>
      
      <el-table
        :data="filteredRecords"
        height="300"
        style="width: 100%"
        row-key="id"
        @selection-change="handleSelectionChange"
        v-loading="loading"
        ref="tableRef"
      >
        <el-table-column type="selection" width="55" :reserve-selection="true" />
        <el-table-column prop="name" label="记录名称" />
      </el-table>
      
      <div class="selection-info">
        已选择 {{ selectedRows.length }} / {{ records.length }} 条
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleConfirm" :disabled="selectedRows.length === 0">
          确认填充
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.search-bar {
  margin-bottom: 12px;
}
.selection-info {
  margin-top: 8px;
  color: #666;
  font-size: 13px;
  text-align: right;
}
</style>
