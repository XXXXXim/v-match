<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import StartupCard from '@/components/StartupCard.vue'
import MatchSuccessModal from '@/components/MatchSuccessModal.vue'

const router = useRouter()
const showMatchModal = ref(false)
const matchedPartner = ref(null)
const goMatches = () => { showMatchModal.value = false; router.push({ name: 'matches' }) }
const goReport = () => { showMatchModal.value = false; if (matchedPartner.value) router.push({ name: 'match-detail', params: { kind: 'startup', id: matchedPartner.value.id } }) }
const loading = ref(true)
const errorMsg = ref('')
const startups = ref([])
const minScore = ref(0)

const fetchRecommendations = async () => {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await api.get('/recommendations/')
    startups.value = res.data.map((s) => ({ ...s, ai_explanation: '', ai_source: '', ai_loading: false }))
  } catch (err) {
    errorMsg.value = err.response?.data?.error || '추천을 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

const visibleStartups = computed(() => startups.value)

const onToggleBookmark = async (id) => {
  try {
    const res = await api.post(`/bookmarks/startup/${id}/toggle/`)
    const t = startups.value.find((s) => s.id === id)
    if (t) t.is_bookmarked = res.data.bookmarked
  } catch { window.alert('북마크 처리에 실패했습니다.') }
}

const onToggleLike = async (id) => {
  try {
    const res = await api.post(`/likes/startup/${id}/toggle/`)
    const t = startups.value.find((s) => s.id === id)
    if (t) t.is_liked = res.data.liked
    if (res.data.matched) { matchedPartner.value = t; showMatchModal.value = true }
  } catch { window.alert('좋아요 처리에 실패했습니다.') }
}

const onExplain = async (id) => {
  const t = startups.value.find((s) => s.id === id)
  if (!t || t.ai_loading) return
  t.ai_loading = true
  try {
    const res = await api.post(`/recommendations/${id}/explain/`)
    t.ai_explanation = res.data.ai_explanation
    t.ai_source = res.data.source
  } catch { window.alert('AI 분석 생성에 실패했습니다.') }
  finally { t.ai_loading = false }
}

const onOpenDetail = (id) => router.push({ name: 'match-detail', params: { kind: 'startup', id } })

onMounted(fetchRecommendations)
</script>

<template>
  <div>
    <h2 class="page-title">추천 스타트업</h2>
    <p v-if="loading" class="info">불러오는 중...</p>
    <div v-else-if="errorMsg" class="error-box">
      {{ errorMsg }}
      <RouterLink :to="{ name: 'vc-profile' }" class="link">VC 프로필 등록하러 가기 →</RouterLink>
    </div>
    <template v-else>
      <p class="count-line">{{ visibleStartups.length }}개의 추천 스타트업</p>
      <p v-if="visibleStartups.length === 0" class="info">추천할 스타트업이 없습니다.</p>
      <div v-else class="grid">
        <StartupCard
          v-for="startup in visibleStartups"
          :key="startup.id"
          :startup="startup"
          @toggle-bookmark="onToggleBookmark"
          @toggle-like="onToggleLike"
          @explain="onExplain"
          @open-detail="onOpenDetail"
        />
      </div>
    </template>
    <MatchSuccessModal :open="showMatchModal" :partner="matchedPartner" kind="startup"
      @close="showMatchModal = false" @go="goMatches" @report="goReport" />
</div>
</template>

<style scoped>
.page-title { margin-bottom: 6px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.count-line { font-family: var(--mono); font-size: 12px; color: var(--ink-3); letter-spacing: .04em; margin-bottom: 16px; }
.info { color: #8a938e; }
.error-box { background: #2a1416; border: 1px solid #3a1a1c; color: #f87171; padding: 16px; border-radius: 8px; }
.link { display: inline-block; margin-top: 8px; color: #2fe3b0; }
.filter-bar { display: flex; align-items: center; gap: 12px; background: #0e1311; border: 1px solid #1c2320; border-radius: 10px; padding: 12px 16px; margin-bottom: 16px; font-size: 14px; }
.filter-bar input[type='range'] { flex: 1; max-width: 280px; }
.count { color: #8a938e; font-size: 13px; }
</style>
