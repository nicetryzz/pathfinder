
<template>
  <div class="detail-pane">
    <el-card v-if="node" class="detail-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span style="font-size:2rem;font-weight:bold;line-height:1.2;color:#222;">{{ node.title }}</span>
          <el-tag :type="tagType">{{ node.type }}</el-tag>
        </div>
      </template>
      <div class="detail-content">
        <vue3-markdown-it :source="node.final_text" class="prose" />
        <el-divider />
        <h3>推荐资源</h3>
        <ul>
          <li v-for="source in node.sources" :key="source.url">
            <a :href="source.url" target="_blank">{{ source.title }}</a>
          </li>
        </ul>
      </div>
    </el-card>
    <el-empty v-else description="请从左侧图谱中选择一个节点查看详情" />
  </div>
</template>

<script setup>
import { computed } from 'vue';
import Vue3MarkdownIt from 'vue3-markdown-it';

const props = defineProps({
  node: Object
});

const tagType = computed(() => {
  if (!props.node) return 'info';
  switch (props.node.type) {
    case 'core': return 'primary';
    case 'prerequisite': return 'warning';
    case 'component': return 'success';
    default: return 'info';
  }
});
</script>

<style scoped>
/* 让右侧详情区高度始终为100%，内容区有独立滚动条 */
/* 右侧详情区高度自适应且内容多时只在自身滚动，不影响左侧区域 */
.detail-pane {
  position: relative;
  height: 100%;
  max-height: 100vh;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  padding: 0 12px;
}
.detail-card {
  width: 100%;
  height: 100%;
  max-height: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}
.detail-content {
  flex: 1;
  overflow-y: auto;
  max-height: calc(100vh - 200px); /* 110px 可根据头部高度微调 */
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.prose {
  /* 可引入 Tailwind Typography 或自定义 Markdown 样式 */
}
</style>
