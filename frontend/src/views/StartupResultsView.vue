<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api'
import { formatMan } from '@/utils/money'
import MatchSuccessModal from '@/components/MatchSuccessModal.vue'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const results = ref([])
const activeGroup = ref('all')      // 산업군 필터
const showMatchModal = ref(false)
const matchedPartner = ref(null)
let matchTimer = null

// 산업군별 그룹화 (백엔드가 '내 관심 산업군'을 먼저 정렬해 보냄 → 등장 순서 유지)
const groups = computed(() => {
  const map = new Map()
  for (const s of results.value) {
    const key = s.industry_group_label || '기타'
    if (!map.has(key)) map.set(key, { label: key, interested: !!s.vc_interested, items: [] })
    map.get(key).items.push(s)
  }
  return [...map.values()]
})
const visibleGroups = computed(() =>
  activeGroup.value === 'all' ? groups.value : groups.value.filter((g) => g.label === activeGroup.value),
)
const interestedCount = computed(() => results.value.filter((s) => s.vc_interested).length)

const fetchResults = async () => {
  loading.value = true
  try { results.value = (await api.get('/startup-search/', { params: route.query })).data }
  catch { results.value = [] }
  finally { loading.value = false }
}

const badge = (s) => (s.is_new ? 'NEW · DECK' : (s.stage || '—').toUpperCase())
const signal = (s) => {
  if (s.mom_growth) return { label: `MoM 성장 ${s.mom_growth}%`, pct: Math.min(100, s.mom_growth) }
  if (s.retention_rate) return { label: `유지율 ${s.retention_rate}%`, pct: Math.min(100, s.retention_rate) }
  return null
}

const onDetail = (id) => router.push({ name: 'match-detail', params: { kind: 'startup', id } })
const fireMatch = (s) => { matchedPartner.value = s; showMatchModal.value = true }
const onToggleBookmark = async (s) => {
  try {
    const res = await api.post(`/bookmarks/startup/${s.id}/toggle/`)
    s.is_bookmarked = res.data.bookmarked
  } catch { window.alert('북마크 처리에 실패했습니다.') }
}
const onLike = async (s) => {
  if (s.is_matched) { matchedPartner.value = s; goReport(); return }
  try {
    const res = await api.post(`/likes/startup/${s.id}/toggle/`)
    s.is_liked = res.data.liked; s.is_matched = !!res.data.matched
    if (res.data.matched) fireMatch(s)
  } catch { window.alert('좋아요 처리에 실패했습니다.') }
}
const editPref = () => router.push({ name: 'vc-profile' })
const goMatches = () => { showMatchModal.value = false; router.push({ name: 'matches' }) }
const goReport = () => { showMatchModal.value = false; if (matchedPartner.value) router.push({ name: 'match-detail', params: { kind: 'startup', id: matchedPartner.value.id } }) }

const syncMatches = async () => {
  try {
    const matches = (await api.get('/matches/')).data
    const matchedIds = new Set(matches.map((m) => m.startup.id))
    results.value.forEach((s) => {
      if (matchedIds.has(s.id) && !s.is_matched) { s.is_matched = true; s.is_liked = true; fireMatch(s) }
    })
  } catch { /* 백그라운드 동기화 실패는 현재 탐색을 막지 않는다. */ }
}

onMounted(async () => { await fetchResults(); matchTimer = setInterval(syncMatches, 5000) })
onUnmounted(() => { if (matchTimer) clearInterval(matchTimer) })
</script>

<template>
  <div>
    <div class="head">
      <div>
        <h2 class="page-title">스타트업 찾기</h2>
        <p v-if="!loading" class="count-line">저장된 선호 조건 기준 {{ results.length }}개 매물</p>
      </div>
      <button class="re" @click="editPref">선호 조건 수정 →</button>
    </div>

    <p v-if="loading" class="info">불러오는 중...</p>

    <div v-else-if="results.length === 0" class="empty">
      <p>조건에 맞는 스타트업이 아직 없습니다.<br />선호 조건을 조금 넓혀보세요.</p>
      <button class="submit-btn" @click="editPref">선호 조건 수정하기</button>
    </div>

    <template v-else>
      <!-- 산업군 필터 칩 (★ = 내 관심 산업군) -->
      <div class="chips">
        <button class="chip" :class="{ on: activeGroup === 'all' }" @click="activeGroup = 'all'">
          전체 <b>{{ results.length }}</b>
        </button>
        <button v-for="g in groups" :key="g.label" class="chip"
          :class="{ on: activeGroup === g.label, fav: g.interested }" @click="activeGroup = g.label">
          <span v-if="g.interested" class="star">★</span>{{ g.label }} <b>{{ g.items.length }}</b>
        </button>
      </div>
      <p v-if="interestedCount" class="fav-note">★ 표시는 내 선호 산업군({{ interestedCount }}개 스타트업) — 위쪽에 먼저 보여드려요.</p>

      <!-- 산업군별 섹션 -->
      <section v-for="g in visibleGroups" :key="g.label" class="grp" :class="{ fav: g.interested }">
        <div class="grp-head">
          <h3 class="grp-title">{{ g.label }}</h3>
          <span class="grp-count">{{ g.items.length }}</span>
          <span v-if="g.interested" class="grp-badge">★ 내 관심 산업군</span>
        </div>

        <div class="grid">
          <div v-for="s in g.items" :key="s.id" class="g-card" :class="{ fav: g.interested }">
            <div class="g-badge">{{ badge(s) }}</div>
            <h3 class="g-name" @click="onDetail(s.id)">{{ s.name }}</h3>
            <div class="g-sector">{{ s.industry || '신규(덱 기반)' }}<template v-if="s.region"> / {{ s.region }}</template></div>

            <p class="g-desc">{{ s.summary || s.description || '소개가 등록되지 않았습니다.' }}</p>

            <div class="g-stats">
              <div><span class="s-k">FUNDING</span><span class="s-v">{{ formatMan(s.funding_needed) }}</span></div>
              <div><span class="s-k">ARR</span><span class="s-v">{{ formatMan(s.revenue) }}</span></div>
            </div>

            <template v-if="signal(s)">
              <div class="g-bar"><div class="g-fill" :style="{ width: signal(s).pct + '%' }"></div></div>
              <div class="g-bar-cap">{{ signal(s).label }}</div>
            </template>

            <div class="g-actions">
              <button class="g-btn detail" @click="onDetail(s.id)">📊 상세 분석</button>
              <button class="g-btn" :class="{ on: s.is_bookmarked }" @click="onToggleBookmark(s)">{{ s.is_bookmarked ? '★' : '☆' }}</button>
              <button class="g-btn like" :class="{ on: s.is_liked, matched: s.is_matched }" @click="onLike(s)">
                {{ s.is_matched ? '✓ 매칭' : s.is_liked ? '취소' : '♡' }}
              </button>
            </div>
          </div>
        </div>
      </section>
    </template>

    <MatchSuccessModal :open="showMatchModal" :partner="matchedPartner" kind="startup"
      @close="showMatchModal = false" @go="goMatches" @report="goReport" />
  </div>
</template>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 20px; gap: 12px; }
.page-title { font-size: 24px; font-weight: 800; }
.count-line { margin-top: 4px; font-family: var(--mono); font-size: 12px; color: var(--ink-3); letter-spacing: .04em; }
.re { background: none; border: none; color: var(--mint); cursor: pointer; font-size: 14px; font-weight: 600; white-space: nowrap; }
.info { color: var(--ink-2); }
.empty { text-align: center; padding: 50px 20px; color: var(--ink-2); line-height: 1.7; }
.empty .submit-btn { margin-top: 18px; }
.submit-btn { padding: 11px 22px; background: var(--mint); color: var(--on-mint); border: none; border-radius: 8px; font-weight: 700; cursor: pointer; }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 14px; }

/* 산업군 필터 칩 */
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.chip { display: inline-flex; align-items: center; gap: 5px; padding: 7px 14px; border-radius: 999px; border: 1px solid var(--line); background: var(--surface); color: var(--ink-2); cursor: pointer; font-size: 13px; font-weight: 600; }
.chip:hover { border-color: var(--mint-dim); }
.chip.on { background: var(--mint); color: var(--on-mint); border-color: var(--mint); }
.chip.fav { border-color: var(--mint-dim); color: var(--ink); }
.chip.fav.on { background: var(--mint); color: var(--on-mint); }
.chip b { font-weight: 800; }
.chip .star { color: var(--warn); }
.chip.on .star { color: var(--on-mint); }
.fav-note { color: var(--ink-3); font-size: 12.5px; margin-bottom: 18px; }

/* 산업군 섹션 */
.grp { margin-bottom: 26px; }
.grp-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--line); }
.grp-title { font-size: 16px; font-weight: 800; color: var(--ink); }
.grp-count { font-family: var(--mono); font-size: 12px; color: var(--ink-3); background: var(--surface-2); border-radius: 999px; padding: 2px 9px; }
.grp-badge { margin-left: auto; font-size: 12px; font-weight: 700; color: var(--mint); background: var(--mint-bg); border: 1px solid var(--mint-dim); border-radius: 999px; padding: 3px 11px; }
.grp.fav .grp-head { border-bottom-color: var(--mint-dim); }
.grp.fav .grp-title { color: var(--mint-br); }
/* 관심 산업군 카드: 은은한 강조 */
.g-card.fav { border-color: var(--mint-dim); box-shadow: 0 0 0 1px rgba(47,227,176,.12) inset; }
.g-card { position: relative; background: var(--surface); border: 1px solid var(--hair); border-radius: var(--radius); padding: 18px; transition: border-color .15s, transform .15s; display: flex; flex-direction: column; }
.g-card:hover { border-color: var(--mint-dim); transform: translateY(-2px); }
.g-badge { display: inline-block; align-self: flex-start; font-family: var(--mono); font-size: 10px; letter-spacing: .08em; color: var(--mint); border: 1px solid var(--mint-dim); border-radius: 5px; padding: 3px 7px; margin-bottom: 14px; }
.g-name { font-size: 19px; font-weight: 800; letter-spacing: -.01em; cursor: pointer; }
.g-name:hover { color: var(--mint); }
.g-sector { margin-top: 5px; font-size: 12.5px; letter-spacing: .01em; color: var(--ink-2); }
.g-desc { margin-top: 12px; font-size: 13px; color: var(--ink-2); line-height: 1.55; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.g-stats { margin-top: 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.g-stats > div { display: flex; flex-direction: column; gap: 5px; }
.s-k { font-size: 11px; font-weight: 600; letter-spacing: .01em; color: var(--ink-2); }
.s-v { font-family: var(--mono); font-size: 16px; font-weight: 700; color: var(--ink); }
.g-bar { margin-top: 16px; height: 4px; background: var(--fill); border-radius: 999px; overflow: hidden; }
.g-fill { height: 100%; background: linear-gradient(90deg, var(--mint-deep), var(--mint)); border-radius: 999px; }
.g-bar-cap { margin-top: 6px; font-family: var(--mono); font-size: 10px; color: var(--ink-3); }
.g-actions { margin-top: auto; padding-top: 16px; display: flex; gap: 6px; }
.g-btn { padding: 8px 12px; border: 1px solid var(--line); border-radius: 7px; background: var(--surface-2); color: var(--ink-2); cursor: pointer; font-size: 13px; font-weight: 600; }
.g-btn.detail { flex: 1; color: var(--mint); border-color: var(--mint-dim); }
.g-btn.on { background: var(--warn-bg); border-color: var(--warn); color: var(--warn); }
.g-btn.like.on { background: var(--pink-bg); border-color: var(--pink); color: var(--pink); }
.g-btn.like.matched { background: var(--ok-bg); border-color: var(--ok); color: var(--ok); }
</style>
