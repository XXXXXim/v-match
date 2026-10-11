<script setup>
import { computed } from 'vue'
import { formatMan } from '@/utils/money'

const props = defineProps({
  startup: { type: Object, required: true },
})
const emit = defineEmits(['toggle-bookmark', 'toggle-like', 'open-detail'])

// 매칭 전이므로 FIT 점수는 비공개. 좌상단 배지는 단계(또는 신규)로 표기.
const badge = computed(() => (props.startup.is_new ? 'NEW · DECK' : (props.startup.stage || '—').toUpperCase()))
// 프로그레스 바: 매칭 전 공개 가능한 트랙션 신호(성장률·유지율)만 시각화.
const signal = computed(() => {
  const g = props.startup.mom_growth
  const r = props.startup.retention_rate
  if (g) return { label: `MoM 성장 ${g}%`, pct: Math.min(100, g) }
  if (r) return { label: `유지율 ${r}%`, pct: Math.min(100, r) }
  return null
})
</script>

<template>
  <div class="g-card">
    <div class="g-badge">{{ badge }}</div>
    <h3 class="g-name" @click="emit('open-detail', startup.id)">{{ startup.name }}</h3>
    <div class="g-sector">{{ startup.industry || '신규(덱 기반)' }}<template v-if="startup.region"> / {{ startup.region }}</template></div>

    <div class="g-stats">
      <div><span class="s-k">FUNDING</span><span class="s-v">{{ formatMan(startup.funding_needed) }}</span></div>
      <div><span class="s-k">ARR</span><span class="s-v">{{ formatMan(startup.revenue) }}</span></div>
    </div>

    <div class="g-bar" v-if="signal" :title="signal.label">
      <div class="g-fill" :style="{ width: signal.pct + '%' }"></div>
    </div>
    <div class="g-bar empty" v-else></div>
    <div class="g-bar-cap" v-if="signal">{{ signal.label }}</div>

    <div class="g-actions">
      <button class="g-btn detail" @click="emit('open-detail', startup.id)">상세</button>
      <button class="g-btn" :class="{ on: startup.is_bookmarked }" @click="emit('toggle-bookmark', startup.id)">{{ startup.is_bookmarked ? '★' : '☆' }}</button>
      <button class="g-btn like" :class="{ on: startup.is_liked }" @click="emit('toggle-like', startup.id)">{{ startup.is_liked ? '♥' : '♡' }}</button>
    </div>
  </div>
</template>

<style scoped>
.g-card { position: relative; background: var(--surface); border: 1px solid var(--hair); border-radius: var(--radius); padding: 18px; transition: border-color .15s, transform .15s; }
.g-card:hover { border-color: var(--mint-dim); transform: translateY(-2px); }
.g-badge { display: inline-block; font-family: var(--mono); font-size: 10px; letter-spacing: .08em; color: var(--mint); border: 1px solid var(--mint-dim); border-radius: 5px; padding: 3px 7px; margin-bottom: 14px; }
.g-name { font-size: 19px; font-weight: 800; letter-spacing: -.01em; cursor: pointer; }
.g-name:hover { color: var(--mint); }
.g-sector { margin-top: 5px; font-size: 12.5px; letter-spacing: .01em; color: var(--ink-2); }
.g-stats { margin-top: 18px; display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.g-stats > div { display: flex; flex-direction: column; gap: 5px; }
.s-k { font-size: 11px; font-weight: 600; letter-spacing: .01em; color: var(--ink-2); }
.s-v { font-family: var(--mono); font-size: 16px; font-weight: 700; color: var(--ink); }
.g-bar { margin-top: 16px; height: 4px; background: var(--fill); border-radius: 999px; overflow: hidden; }
.g-bar.empty { opacity: .4; }
.g-fill { height: 100%; background: linear-gradient(90deg, var(--mint-deep), var(--mint)); border-radius: 999px; }
.g-bar-cap { margin-top: 6px; font-family: var(--mono); font-size: 10px; color: var(--ink-3); }
.g-actions { margin-top: 16px; display: flex; gap: 6px; }
.g-btn { padding: 7px 12px; border: 1px solid var(--line); border-radius: 7px; background: var(--surface-2); color: var(--ink-2); cursor: pointer; font-size: 13px; font-weight: 600; }
.g-btn.detail { flex: 1; color: var(--mint); border-color: var(--mint-dim); }
.g-btn.on { background: var(--warn-bg); border-color: var(--warn); color: var(--warn); }
.g-btn.like.on { background: var(--pink-bg); border-color: var(--pink); color: var(--pink); }
</style>
