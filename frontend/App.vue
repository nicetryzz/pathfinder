
<template>
  <div class="app-container">
    <div class="header">
      <h1>Pathfinder - Your AI Learning Navigator</h1>
    </div>
    <div class="main-content">
      <div class="left-pane">
        <div class="search-bar">
          <el-input v-model="topic" placeholder="输入主题" clearable style="flex:1; margin-right:12px;" />
          <el-button type="primary" @click="fetchMap">加载知识图谱</el-button>
        </div>
        <div class="graph-area">
          <GraphCanvas :graph-data="knowledgeGraph.graph" @node-click="handleNodeClick" />
        </div>
      </div>
      <div class="right-pane">
        <NodeDetail :node="selectedNode" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import GraphCanvas from './components/GraphCanvas.vue';
import NodeDetail from './components/NodeDetail.vue';

const topic = ref('LLM AI agent');
const knowledgeGraph = ref({ graph: { nodes: [], edges: [] } });
const selectedNode = ref(null);

const handleNodeClick = (nodeId) => {
  selectedNode.value = knowledgeGraph.value.graph.nodes.find(n => n.id === nodeId);
};

const fetchMap = async () => {
  try {
    const response = await fetch(`/api/v1/maps/${topic.value}`);
    const data = await response.json();
    knowledgeGraph.value = data;
    selectedNode.value = null;
  } catch (error) {
    console.error("Failed to fetch knowledge graph:", error);
  }
};

onMounted(fetchMap);
</script>

<style>
html, body, #app {
  height: 100%;
  margin: 0;
  padding: 0;
}
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.header {
  background-color: #409EFF;
  color: white;
  display: flex;
  align-items: center;
  font-size: 1.2rem;
  font-weight: bold;
  height: 56px;
  flex-shrink: 0;
  padding-left: 16px;
}
.main-content {
  flex: 1;
  min-height: 0;
  display: flex;
  background: #fff;
}
.left-pane {
  width: 55%;
  display: flex;
  flex-direction: column;
  background: #fff;
  box-shadow: 2px 0 8px #eee;
  padding: 24px 0;
  align-items: center;
}
.search-bar {
  width: 80%;
  margin-bottom: 24px;
  display: flex;
  gap: 12px;
  align-items: center;
}
.graph-area {
  width: 100%;
  flex: 1;
  min-height: 0;
}
.right-pane {
  width: 45%;
  background: #f5f7fa;
  padding: 20px;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
</style>
