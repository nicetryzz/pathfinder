<template>
  <div class="chart-container">
    <v-chart class="chart" :option="chartOption" @click="onChartClick" autoresize />
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { GraphChart } from 'echarts/charts';
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components';
import VChart from 'vue-echarts';

use([CanvasRenderer, GraphChart, TitleComponent, TooltipComponent, LegendComponent]);

const props = defineProps({
  graphData: Object
});
const emit = defineEmits(['node-click']);

const chartOption = computed(() => {
  const graph = props.graphData || {};
  const nodes = Array.isArray(graph.nodes) ? graph.nodes.map(node => ({
    id: node.id,
    name: node.title,
    symbolSize: node.type === 'core' ? 60 : 40,
    itemStyle: {
      color: getNodeColor(node.type)
    },
    label: {
      show: true,
      formatter: '{b}'
    },
    rawData: node
  })) : [];
  // 恢复连接线，但不显示 label（关系描述）
  const edges = Array.isArray(graph.edges) ? graph.edges.map(edge => ({
    source: edge.source,
    target: edge.target
    // 不加 label
  })) : [];
  return {
    tooltip: {},
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        data: nodes,
        links: edges,
        center: ['50%', '50%'],
        force: {
          repulsion: 300,
          edgeLength: 200
        }
      }
    ]
  };
});

function getNodeColor(type) {
  switch (type) {
    case 'core': return '#409EFF';
    case 'prerequisite': return '#E6A23C';
    case 'component': return '#67C23A';
    default: return '#909399';
  }
}

function onChartClick(params) {
  if (params.dataType === 'node') {
    emit('node-click', params.data.id);
  }
}
</script>

<style scoped>
.chart-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  width: 100%;
}
.chart {
  height: 100%;
  width: 100%;
  min-height: 400px;
  min-width: 400px;
}
</style>
