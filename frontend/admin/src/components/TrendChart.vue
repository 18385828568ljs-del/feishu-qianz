<template>
  <div ref="chartRef" class="trend-chart"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  dates: {
    type: Array,
    default: () => []
  },
  users: {
    type: Array,
    default: () => []
  },
  signatures: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const chartRef = ref(null)
let chartInstance = null

// 格式化日期显示(只显示月-日)
function formatDate(dateStr) {
  const parts = dateStr.split('-')
  return `${parts[1]}-${parts[2]}`
}

// 初始化图表
function initChart() {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value)
  updateChart()
  
  // 响应式调整
  window.addEventListener('resize', handleResize)
}

// 更新图表数据
function updateChart() {
  if (!chartInstance) return
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        crossStyle: {
          color: '#999'
        }
      },
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#eee',
      borderWidth: 1,
      textStyle: {
        color: '#333'
      }
    },
    legend: {
      data: ['新增用户', '签名次数'],
      bottom: 0,
      textStyle: {
        color: '#666'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: props.dates.map(formatDate),
      axisPointer: {
        type: 'shadow'
      },
      axisLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      axisLabel: {
        color: '#666'
      }
    },
    yAxis: [
      {
        type: 'value',
        name: '用户数',
        position: 'left',
        axisLine: {
          show: true,
          lineStyle: {
            color: '#409eff'
          }
        },
        axisLabel: {
          color: '#409eff'
        },
        splitLine: {
          lineStyle: {
            color: '#f0f0f0'
          }
        }
      },
      {
        type: 'value',
        name: '签名次数',
        position: 'right',
        axisLine: {
          show: true,
          lineStyle: {
            color: '#67c23a'
          }
        },
        axisLabel: {
          color: '#67c23a'
        },
        splitLine: {
          show: false
        }
      }
    ],
    series: [
      {
        name: '新增用户',
        type: 'line',
        yAxisIndex: 0,
        data: props.users,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        itemStyle: {
          color: '#409eff'
        },
        lineStyle: {
          width: 3,
          color: '#409eff'
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
          ])
        }
      },
      {
        name: '签名次数',
        type: 'line',
        yAxisIndex: 1,
        data: props.signatures,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        itemStyle: {
          color: '#67c23a'
        },
        lineStyle: {
          width: 3,
          color: '#67c23a'
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(103, 194, 58, 0.3)' },
            { offset: 1, color: 'rgba(103, 194, 58, 0.05)' }
          ])
        }
      }
    ]
  }
  
  chartInstance.setOption(option)
}

// 处理窗口大小变化
function handleResize() {
  chartInstance?.resize()
}

// 监听数据变化
watch(() => [props.dates, props.users, props.signatures], () => {
  updateChart()
}, { deep: true })

onMounted(() => {
  initChart()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<style scoped>
.trend-chart {
  width: 100%;
  height: 450px;
}
</style>
