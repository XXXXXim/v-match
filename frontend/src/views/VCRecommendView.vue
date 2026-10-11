<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import { formatMan } from '@/utils/money'
import MatchSuccessModal from '@/components/MatchSuccessModal.vue'

const router = useRouter()
const showMatchModal = ref(false)
const matchedPartner = ref(null)
const goMatches = () => { showMatchModal.value = false; router.push({ name: 'matches' }) }
const goReport = () => { showMatchModal.value = false; if (matchedPartner.value) router.push({ name: 'match-detail', params: { kind: 'vc', id: matchedPartner.value.id } }) }
const loading = ref(true)
const errorMsg = ref('')
const vcs = ref([])
let matchTimer = null

const fetchVCs = async () => {
  loading.value = true; errorMsg.value = ''
  try { vcs.value = (await api.get('/vc-recommendations/')).data }
  catch (err) { errorMsg.value = err.response?.data?.error || '추천을 불러오지 못했습니다.' }
  finally { loading.value = false }
}

const visible = computed(() => vcs.value)
const myGroupLabel = computed(() => vcs.value.find((v) => v.my_group_label)?.my_group_label || '')
const matchedCount = computed(() => vcs.value.filter((v) => v.group_match).length)
const sectorLabel = (vc) => (vc.preferred_industries || []).slice(0, 2).join(' / ') || '전 산업'
const badgeOf = (vc) => ((vc.preferred_industries || [])[0] || 'VC').toUpperCase()
const openDetail = (id) => router.push({ name: 'vc-detail', params: { id } })

const fireMatch = (vc) => { matchedPartner.value = vc; showMatchModal.value = true }

const onToggleBookmark = async (id) => {
  try {
    const res = await api.post(`/bookmarks/vc/${id}/toggle/`)
    const t = vcs.value.find((v) => v.id === id); if (t) t.is_bookmarked = res.data.bookmarked
  } catch { window.alert('북마크 처리에 실패했습니다.') }
}
const onToggleLike = async (vc) => {
  if (vc.is_matched) { matchedPartner.value = vc; goReport(); return }
  try {
    const res = await api.post(`/likes/vc/${vc.id}/toggle/`)
    vc.is_liked = res.data.liked; vc.is_matched = !!res.data.matched
    if (res.data.matched) fireMatch(vc)
  } catch { window.alert('좋아요 처리에 실패했습니다.') }
}

const syncMatches = async () => {
  try {
    const matches = (await api.get('/matches/')).data
    const matchedIds = new Set(matches.map((m) => m.vc.id))
    vcs.value.forEach((vc) => {
      if (matchedIds.has(vc.id) && !vc.is_matched) { vc.is_matched = true; vc.is_liked = true; fireMatch(vc) }
    })
  } catch { /* 백그라운드 동기화 실패는 추천 화면을 막지 않는다. */ }
}

onMounted(async () => { await fetchVCs(); matchTimer = setInterval(syncMatches, 5000) })
onUnmounted(() => { if (matchTimer) clearInterval(matchTimer) })
</script>

<template>
  <div>
    <div class="head">
      <div>
        <h2 class="page-title">VC 추천</h2>
        <p v-if="!loading && !errorMsg" class="count-line">투자 논리에 맞는 {{ visible.length }}개 VC</p>
      </div>
    </div>

    <p v-if="loading" class="info">불러오는 중...</p>
    <div v-else-if="errorMsg" class="error-box">
      {{ errorMsg }}
      <RouterLink :to="{ name: 'startup-profile' }" class="link">스타트업 프로필 등록하러 가기 →</RouterLink>
    </div>

    <template v-else>
      <p v-if="visible.length === 0" class="info">추천할 VC가 없습니다.</p>

      <p v-if="matchedCount" class="match-note">
        🎯 <b>{{ myGroupLabel }}</b> 산업군에 관심 있는 VC <b>{{ matchedCount }}곳</b>을 위쪽에 강조했어요.
      </p>

      <div class="grid">
        <div v-for="vc in visible" :key="vc.id" class="g-card" :class="{ fav: vc.group_match }">
          <div v-if="vc.group_match" class="fav-ribbon">🎯 우리 산업군 관심</div>
          <div class="g-badge">{{ badgeOf(vc) }}</div>
          <h3 class="g-name" @click="openDetail(vc.id)">{{ vc.firm_name }}</h3>
          <div class="g-sector">{{ sectorLabel(vc) }}</div>

          <div class="g-stats">
            <div><span class="s-k">최소 투자금</span><span class="s-v">{{ formatMan(vc.min_investment) }}~</span></div>
            <div><span class="s-k">최대 투자금</span><span class="s-v">{{ formatMan(vc.max_investment) }}</span></div>
          </div>

          <div class="g-region">📍 {{ (vc.preferred_regions || []).join(', ') || '전국' }}</div>

          <div class="g-actions">
            <button class="g-btn detail" @click="openDetail(vc.id)">상세</button>
            <button class="g-btn" :class="{ on: vc.is_bookmarked }" @click="onToggleBookmark(vc.id)">{{ vc.is_bookmarked ? '★' : '☆' }}</button>
            <button class="g-btn like" :class="{ on: vc.is_liked, matched: vc.is_matched }" @click="onToggleLike(vc)">
              {{ vc.is_matched ? '✓ 매칭' : vc.is_liked ? '취소' : '♡' }}
            </button>
          </div>
        </div>
      </div>
    </template>

    <MatchSuccessModal :open="showMatchModal" :partner="matchedPartner" kind="vc"
      @close="showMatchModal = false" @go="goMatches" @report="goReport" />
  </div>
</template>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 20px; }
.page-title { font-size: 24px; font-weight: 800; }
.count-line { margin-top: 4px; font-family: var(--mono); font-size: 12px; color: var(--ink-3); letter-spacing: .04em; }
.info { color: var(--ink-2); }
.error-box { background: var(--danger-bg); border: 1px solid rgba(248,113,113,.3); color: var(--danger); padding: 16px; border-radius: 10px; }
.link { display: inline-block; margin-top: 8px; color: var(--mint); }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(270px, 1fr)); gap: 14px; }
.match-note { margin-bottom: 16px; font-size: 13.5px; color: var(--ink-2); background: var(--mint-bg); border: 1px solid var(--mint-dim); border-radius: 10px; padding: 10px 14px; }
.match-note b { color: var(--mint-br); }
/* 우리 산업군에 관심 있는 VC: 글로우 강조 + 리본 */
.g-card.fav { border-color: var(--mint); box-shadow: 0 0 0 1px var(--mint) inset, 0 6px 22px rgba(47,227,176,.14); }
.fav-ribbon { position: absolute; top: 12px; right: 12px; font-size: 11px; font-weight: 800; color: var(--on-mint); background: var(--mint); border-radius: 999px; padding: 3px 10px; letter-spacing: .01em; }
.g-card.fav .g-name { color: var(--mint-br); }
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
.g-region { margin-top: 14px; font-size: 12.5px; color: var(--ink-2); }
.g-actions { margin-top: 16px; display: flex; gap: 6px; }
.g-btn { padding: 7px 12px; border: 1px solid var(--line); border-radius: 7px; background: var(--surface-2); color: var(--ink-2); cursor: pointer; font-size: 13px; font-weight: 600; }
.g-btn.detail { flex: 1; color: var(--mint); border-color: var(--mint-dim); }
.g-btn.on { background: var(--warn-bg); border-color: var(--warn); color: var(--warn); }
.g-btn.like.on { background: var(--pink-bg); border-color: var(--pink); color: var(--pink); }
.g-btn.like.matched { background: var(--ok-bg); border-color: var(--ok); color: var(--ok); }
</style>
