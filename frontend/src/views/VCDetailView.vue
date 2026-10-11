<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api'
import { formatMan } from '@/utils/money'
import MatchSuccessModal from '@/components/MatchSuccessModal.vue'

const route = useRoute()
const router = useRouter()
const vc = ref(null)
const loading = ref(true)
const errorMsg = ref('')
const showMatchModal = ref(false)
let matchTimer = null

const load = async () => {
  loading.value = true
  try {
    vc.value = (await api.get(`/vc/${route.params.id}/`)).data
  } catch (err) {
    errorMsg.value = err.response?.data?.error || 'VC 정보를 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

const onToggleLike = async () => {
  if (vc.value?.is_matched) {
    goMatches()
    return
  }
  try {
    const res = await api.post(`/likes/vc/${vc.value.id}/toggle/`)
    vc.value.is_liked = res.data.liked
    vc.value.is_matched = !!res.data.matched
    if (res.data.matched) showMatchModal.value = true
  } catch { window.alert('좋아요 처리에 실패했습니다.') }
}
const onToggleBookmark = async () => {
  try {
    const res = await api.post(`/bookmarks/vc/${vc.value.id}/toggle/`)
    vc.value.is_bookmarked = res.data.bookmarked
  } catch { window.alert('북마크 처리에 실패했습니다.') }
}
const goMatches = () => { showMatchModal.value = false; router.push({ name: 'matches' }) }

const syncMatch = async () => {
  if (!vc.value || vc.value.is_matched) return
  try {
    const matches = (await api.get('/matches/')).data
    if (matches.some((m) => m.vc.id === vc.value.id)) {
      vc.value.is_matched = true
      vc.value.is_liked = true
      showMatchModal.value = true
    }
  } catch { /* 백그라운드 상태 확인 실패는 상세 열람을 막지 않는다. */ }
}

onMounted(async () => {
  await load()
  matchTimer = setInterval(syncMatch, 5000)
})
onUnmounted(() => { if (matchTimer) clearInterval(matchTimer) })
</script>

<template>
  <div>
    <button class="back" @click="router.back()">← 목록으로</button>
    <p v-if="loading" class="info">불러오는 중...</p>
    <p v-else-if="errorMsg" class="error">{{ errorMsg }}</p>

    <div v-else class="detail">
      <div class="head">
        <h2>{{ vc.firm_name }}</h2>
        <p class="tags">
          <span class="tag" v-for="ind in vc.preferred_industries" :key="ind">{{ ind }}</span>
        </p>
        <p v-if="vc.website" class="vc-link">
          🔗 <a :href="vc.website" target="_blank" rel="noopener noreferrer">{{ vc.website }} ↗</a>
        </p>
      </div>

      <div class="card">
        <div class="row"><span class="k">선호 산업</span><span class="v">{{ vc.preferred_industries.join(', ') || '-' }}</span></div>
        <div class="row"><span class="k">선호 단계</span><span class="v">{{ vc.preferred_stages.join(', ') || '-' }}</span></div>
        <div class="row"><span class="k">선호 지역</span><span class="v">{{ vc.preferred_regions.join(', ') || '-' }}</span></div>
        <div class="row"><span class="k">희망 투자금</span><span class="v">{{ formatMan(vc.min_investment) }} ~ {{ formatMan(vc.max_investment) }}</span></div>
      </div>

      <div v-if="vc.bio" class="card">
        <h3>소개</h3>
        <p class="text">{{ vc.bio }}</p>
      </div>
      <div v-if="vc.vc_summary" class="card">
        <h3>📋 VC 요약</h3>
        <p class="text">{{ vc.vc_summary }}</p>
      </div>

      <div class="actions">
        <button class="action-btn like" :class="{ active: vc.is_liked, matched: vc.is_matched }" @click="onToggleLike">
          {{ vc.is_matched ? '✓ 매칭됨 · 확인하기' : vc.is_liked ? '♥ 상대 응답 대기' : '♡ 좋아요' }}
        </button>
        <button class="action-btn" :class="{ active: vc.is_bookmarked }" @click="onToggleBookmark">
          {{ vc.is_bookmarked ? '★ 북마크됨' : '☆ 북마크' }}
        </button>
      </div>
    </div>

    <MatchSuccessModal :open="showMatchModal" @close="showMatchModal = false" @go="goMatches" />
  </div>
</template>

<style scoped>
.back { background: none; border: none; color: #2fe3b0; cursor: pointer; font-size: 14px; margin-bottom: 16px; padding: 0; }
.info, .error { color: #8a938e; } .error { color: #f87171; }
.head { margin-bottom: 16px; }
.head h2 { font-size: 26px; font-weight: 800; }
.tags { margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap; }
.tag { background: #10201b; color: #2fe3b0; font-size: 12px; padding: 3px 10px; border-radius: 999px; }
.vc-link { margin-top: 10px; font-size: 14px; }
.vc-link a { color: #2fe3b0; font-weight: 600; word-break: break-all; }
.card { background: #0e1311; border: 1px solid #1c2320; border-radius: 12px; padding: 20px; margin-bottom: 14px; }
.card h3 { font-size: 15px; font-weight: 700; margin-bottom: 8px; }
.row { display: flex; gap: 12px; padding: 7px 0; border-bottom: 1px dashed #161d19; font-size: 14px; }
.row:last-child { border-bottom: none; }
.row .k { width: 100px; color: #8a938e; flex-shrink: 0; }
.row .v { color: #cdd4d0; }
.text { color: #aab3ae; font-size: 14px; line-height: 1.7; }
.actions { margin-top: 18px; display: flex; gap: 10px; }
.action-btn { padding: 10px 20px; border: 1px solid #283029; border-radius: 8px; background: #0e1311; cursor: pointer; font-weight: 500; font-size: 15px; }
.action-btn.active { background: #241d0c; border-color: #fbbf24; color: #fbbf24; }
.action-btn.like.active { background: #2a1320; border-color: #f472b6; color: #f472b6; }
.action-btn.like.matched { background: #10241a; border-color: #4ade80; color: #4ade80; }
</style>
