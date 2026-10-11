<script setup>
defineProps({
  open: Boolean,
  url: { type: String, default: null },
  title: { type: String, default: 'PDF 미리보기' },
  emptyText: { type: String, default: '등록된 파일이 없습니다.' },
})
const emit = defineEmits(['close'])
</script>

<template>
  <div v-if="open" class="overlay" @click.self="emit('close')">
    <div class="vm-modal">
      <div class="bar">
        <span class="title">{{ title }}</span>
        <span class="right">
          <a v-if="url" :href="url" target="_blank" rel="noopener noreferrer" class="newtab">새 탭에서 열기 ↗</a>
          <button class="x" @click="emit('close')">✕</button>
        </span>
      </div>
      <iframe v-if="url" :src="url" class="frame" title="PDF"></iframe>
      <div v-else class="empty">{{ emptyText }}</div>
    </div>
  </div>
</template>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.55); display: flex; align-items: center; justify-content: center; z-index: 60; padding: 20px; }
.vm-modal { background: #0e1311; border-radius: 12px; width: 100%; max-width: 900px; height: 90vh; display: flex; flex-direction: column; overflow: hidden; }
.bar { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid #1c2320; }
.title { font-weight: 700; }
.right { display: flex; align-items: center; gap: 14px; }
.newtab { font-size: 13px; color: #2fe3b0; font-weight: 600; }
.x { background: none; border: none; font-size: 18px; cursor: pointer; color: #8a938e; }
.frame { flex: 1; width: 100%; border: 0; }
.empty { flex: 1; display: flex; align-items: center; justify-content: center; color: #8a938e; }
</style>
