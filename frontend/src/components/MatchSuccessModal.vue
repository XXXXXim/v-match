<script setup>
defineProps({ open: Boolean })
const emit = defineEmits(['close', 'go'])
</script>

<template>
  <div v-if="open" class="overlay" @click.self="emit('close')">
    <div class="match-modal" role="dialog" aria-modal="true" aria-labelledby="matchSuccessTitle">
      <div class="emoji">🎉</div>
      <h3 id="matchSuccessTitle">매칭이 성사되었습니다!</h3>
      <p>
        서로의 관심이 확인되었습니다.<br />
        매칭 페이지에서 AI 심층 분석을 보고 커피챗을 요청할 수 있습니다.
      </p>
      <div class="actions">
        <button class="btn ghost" @click="emit('close')">닫기</button>
        <button class="btn primary" @click="emit('go')">매칭 페이지로 이동 →</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); display: flex; align-items: center; justify-content: center; z-index: 60; }
.match-modal { background: #0e1311; border-radius: 16px; padding: 30px 28px; width: 92%; max-width: 420px; text-align: center; box-shadow: 0 20px 50px rgba(0,0,0,0.25); }
.emoji { font-size: 44px; }
.match-modal h3 { font-size: 22px; font-weight: 800; margin: 10px 0 12px; color: #f472b6; }
.match-modal p { color: #aab3ae; font-size: 15px; line-height: 1.7; }
.actions { margin-top: 22px; display: flex; gap: 10px; justify-content: center; }
.btn { padding: 11px 20px; border-radius: 8px; font-weight: 600; font-size: 14px; cursor: pointer; border: none; }
.btn.primary { background: #2fe3b0; color: #0e1311; }
.btn.ghost { background: #161d19; color: #cdd4d0; }
</style>
