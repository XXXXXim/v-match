<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'
import LandingPage from '@/components/LandingPage.vue'

const router = useRouter()
const auth = useAuthStore()

const isStartup = computed(() => auth.user?.role === 'startup')
const workspaceLabel = computed(() => (isStartup.value ? 'STARTUP' : 'VENTURE CAPITAL') + ' WORKSPACE')

const registered = ref(false)
const loaded = ref(false)

// 4개 섹션 데이터
const recommend = ref([])
const matches = ref([])
const notis = ref([])
const unread = ref(0)
const chats = ref([])

const goRegisterProfile = () => router.push({ name: isStartup.value ? 'startup-profile' : 'vc-profile' })
const goMainList = () => router.push({ name: isStartup.value ? 'vc-recommend' : 'startup-results' })
const goThread = (id) => router.push({ name: 'coffeechat-thread', params: { id } })

const lede = computed(() => {
  if (!loaded.value) return '워크스페이스를 준비하고 있습니다.'
  return registered.value
    ? '새로운 추천과 진행 중인 매칭, 알림과 대화를 한눈에 확인하세요.'
    : '추천을 받기 전에 프로필을 완성해주세요. 약 3분이면 충분합니다.'
})

// ── 표시용 헬퍼 ──────────────────────────────────────────────
const recTitle = (r) => (isStartup.value ? r.firm_name : r.name) || '이름 미상'
const recSub = (r) => {
  if (isStartup.value) {
    const ind = Array.isArray(r.preferred_industries) ? r.preferred_industries.slice(0, 2).join(', ') : ''
    return ind || 'VC'
  }
  return [r.industry, r.stage].filter(Boolean).join(' · ') || '스타트업'
}

const MATCH_STATUS = {
  matched: { text: '매칭 성립', cls: 'b-mint' },
  requested: { text: '요청 진행 중', cls: 'b-warn' },
  accepted: { text: '성사', cls: 'b-ok' },
  declined: { text: '종료', cls: 'b-mute' },
}
const matchBadge = (m) => MATCH_STATUS[m.status] || { text: m.status, cls: 'b-mute' }
const matchName = (m) => (m.my_role === 'vc' ? m.startup?.name : m.vc?.firm_name) || '상대방'

const chatName = (c) => (c.is_sender ? c.receiver_name : c.sender_name) || '상대방'
const chatBadge = (c) => ({
  ACCEPTED: 'b-ok', PENDING: 'b-warn', REJECTED: 'b-mute',
}[c.status] || 'b-mute')

const notiIcon = (k) => ({ coffeechat: '☕', match: '🤝', like: '❤️' }[k] || '🔔')

const fmtDate = (v) => {
  if (!v) return ''
  try {
    return new Intl.DateTimeFormat('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(v))
  } catch { return '' }
}

// ── 데이터 로딩 ──────────────────────────────────────────────
const loadDashboard = async () => {
  const recUrl = isStartup.value ? '/vc-recommendations/' : '/recommendations/'
  const [rec, mat, noti, cc] = await Promise.allSettled([
    api.get(recUrl),
    api.get('/matches/'),
    api.get('/notifications/'),
    api.get('/coffeechats/my-requests/'),
  ])
  if (rec.status === 'fulfilled') recommend.value = (Array.isArray(rec.value.data) ? rec.value.data : []).slice(0, 4)
  if (mat.status === 'fulfilled') matches.value = (Array.isArray(mat.value.data) ? mat.value.data : []).slice(0, 4)
  if (noti.status === 'fulfilled') {
    notis.value = (noti.value.data?.results || []).slice(0, 4)
    unread.value = noti.value.data?.unread || 0
  }
  if (cc.status === 'fulfilled') chats.value = (Array.isArray(cc.value.data) ? cc.value.data : []).slice(0, 4)
}

onMounted(async () => {
  if (!auth.isLogin) return
  try {
    registered.value = !!(await api.get('/profile-status/')).data?.registered
  } catch {
    registered.value = false
  } finally {
    loaded.value = true
  }
  if (registered.value) {
    try { await loadDashboard() } catch { /* 일부 위젯 실패는 무시 */ }
  }
})
</script>

<template>
  <!-- 비로그인: 랜딩 -->
  <LandingPage v-if="!auth.isLogin" />

  <!-- 로그인: 워크스페이스 -->
  <section v-else class="dash">
    <header class="dash-head">
      <span class="eyebrow">{{ workspaceLabel }}</span>
      <h1>{{ auth.user?.username }}님,<br />다음 기회를 찾아볼까요?</h1>
      <p class="lede">{{ lede }}</p>
    </header>

    <!-- 신규 가입(미등록): 온보딩 -->
    <div v-if="loaded && !registered" class="onboard">
      <div>
        <small>시작 전 마지막 단계</small>
        <h2>프로필 자료를 등록해주세요</h2>
        <p>추천을 받으려면 먼저 프로필을 완성해주세요.</p>
      </div>
      <button class="btn-primary" @click="goRegisterProfile">프로필 완성하기 →</button>
    </div>

    <!-- 로딩 스켈레톤 -->
    <div v-else-if="!loaded" class="grid">
      <article v-for="n in 4" :key="n" class="card sk">
        <div class="sk-bar w40"></div>
        <div class="sk-bar w90"></div>
        <div class="sk-bar w70"></div>
        <div class="sk-bar w80"></div>
      </article>
    </div>

    <!-- 등록 완료: 4개 섹션 대시보드 -->
    <div v-else class="grid">
      <!-- 1) 최근 추천 -->
      <article class="card card--accent">
        <div class="card-head">
          <span class="card-title"><span class="ic">◎</span>최근 추천</span>
          <button class="more" @click="goMainList">전체 보기 →</button>
        </div>
        <ul v-if="recommend.length" class="list">
          <li v-for="(r, i) in recommend" :key="i" class="row clickable" @click="goMainList">
            <span class="avatar">{{ recTitle(r).slice(0, 1) }}</span>
            <span class="row-main">
              <strong>{{ recTitle(r) }}</strong>
              <small>{{ recSub(r) }}</small>
            </span>
            <span v-if="r.is_matched" class="badge b-mint">매칭됨</span>
            <span v-else-if="r.is_liked" class="badge b-violet">관심</span>
          </li>
        </ul>
        <p v-else class="empty">{{ isStartup ? '맞는 VC를 찾고 있어요.' : '조건에 맞는 스타트업을 찾고 있어요.' }}</p>
      </article>

      <!-- 2) 진행 중인 매칭 -->
      <article class="card">
        <div class="card-head">
          <span class="card-title"><span class="ic">🤝</span>진행 중인 매칭</span>
          <RouterLink class="more" :to="{ name: 'matches' }">전체 보기 →</RouterLink>
        </div>
        <ul v-if="matches.length" class="list">
          <li v-for="m in matches" :key="m.id" class="row clickable" @click="router.push({ name: 'matches' })">
            <span class="avatar">{{ matchName(m).slice(0, 1) }}</span>
            <span class="row-main">
              <strong>{{ matchName(m) }}</strong>
              <small v-if="m.waiting">상대 응답 대기 중</small>
              <small v-else-if="m.can_accept">내 응답이 필요해요</small>
              <small v-else>{{ m.my_role === 'vc' ? '스타트업' : 'VC' }}</small>
            </span>
            <span class="badge" :class="matchBadge(m).cls">{{ matchBadge(m).text }}</span>
          </li>
        </ul>
        <p v-else class="empty">아직 진행 중인 매칭이 없어요. 추천에서 관심을 표시해보세요.</p>
      </article>

      <!-- 3) 새 알림 -->
      <article class="card">
        <div class="card-head">
          <span class="card-title">
            <span class="ic">🔔</span>새 알림
            <span v-if="unread" class="count">{{ unread }}</span>
          </span>
          <RouterLink class="more" :to="{ name: 'notifications' }">전체 보기 →</RouterLink>
        </div>
        <ul v-if="notis.length" class="list">
          <li v-for="n in notis" :key="n.id" class="row clickable" :class="{ unread: !n.is_read }" @click="router.push({ name: 'notifications' })">
            <span class="n-ic">{{ notiIcon(n.kind) }}</span>
            <span class="row-main">
              <strong class="n-msg">{{ n.message }}</strong>
              <small>{{ fmtDate(n.created_at) }}</small>
            </span>
            <span v-if="!n.is_read" class="dot" aria-label="안 읽음"></span>
          </li>
        </ul>
        <p v-else class="empty">새 알림이 없어요.</p>
      </article>

      <!-- 4) 채팅 -->
      <article class="card">
        <div class="card-head">
          <span class="card-title"><span class="ic">💬</span>채팅</span>
          <RouterLink class="more" :to="{ name: 'coffeechats' }">전체 보기 →</RouterLink>
        </div>
        <ul v-if="chats.length" class="list">
          <li v-for="c in chats" :key="c.id" class="row clickable" @click="goThread(c.id)">
            <span class="avatar">{{ chatName(c).slice(0, 1) }}</span>
            <span class="row-main">
              <strong>{{ chatName(c) }}</strong>
              <small class="n-msg">{{ c.reply_message || c.message || '대화를 시작해보세요.' }}</small>
            </span>
            <span class="badge" :class="chatBadge(c)">{{ c.status_label }}</span>
          </li>
        </ul>
        <p v-else class="empty">아직 주고받은 커피챗이 없어요.</p>
      </article>
    </div>
  </section>
</template>

<style scoped>
.dash { padding: 56px max(20px, calc((100% - 1080px) / 2)) 90px; }
.eyebrow { display: inline-block; color: var(--mint); font-size: 13px; font-weight: 700; letter-spacing: 2.4px; text-transform: uppercase; }
.dash-head h1 { margin-top: 14px; color: var(--ink); font-size: clamp(30px, 4vw, 44px); font-weight: 400; line-height: 1.12; letter-spacing: -0.8px; }
.lede { margin-top: 14px; color: var(--ink-2); font-size: 16px; }

/* 온보딩 */
.onboard { margin-top: 34px; padding: 26px; display: flex; align-items: center; justify-content: space-between; gap: 20px; background: var(--surface); border: 1px solid var(--hair); border-radius: var(--radius); }
.onboard small { color: var(--mint); font-weight: 700; font-size: 13px; letter-spacing: 0.4px; }
.onboard h2 { margin-top: 8px; color: var(--ink); font-size: 20px; font-weight: 600; }
.onboard p { margin-top: 6px; color: var(--ink-3); font-size: 14px; }
.btn-primary { flex-shrink: 0; padding: 12px 20px; background: var(--mint); color: var(--on-mint); border: none; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; transition: background 0.15s, transform 0.15s; }
.btn-primary:hover { background: var(--mint-br); transform: translateY(-1px); }

/* 그리드 */
.grid { margin-top: 36px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 18px; }
.card { padding: 22px 22px 10px; background: var(--surface); border: 1px solid var(--hair); border-radius: var(--radius); display: flex; flex-direction: column; min-height: 230px; }
.card--accent { border-color: var(--mint-dim); background: linear-gradient(180deg, var(--mint-bg), transparent 42%), var(--surface); }
.card-head { display: flex; align-items: center; justify-content: space-between; padding-bottom: 14px; border-bottom: 1px solid var(--hair-2); }
.card-title { display: inline-flex; align-items: center; gap: 9px; color: var(--ink); font-size: 16px; font-weight: 700; }
.ic { font-size: 15px; }
.count { display: inline-grid; place-items: center; min-width: 20px; height: 20px; padding: 0 6px; background: var(--mint); color: var(--on-mint); border-radius: 999px; font-size: 11px; font-weight: 800; }
.more { background: none; border: none; color: var(--ink-3); font-size: 13px; font-weight: 600; cursor: pointer; text-decoration: none; }
.more:hover { color: var(--mint); }

/* 리스트 */
.list { list-style: none; display: flex; flex-direction: column; }
.row { display: flex; align-items: center; gap: 12px; padding: 12px 4px; border-bottom: 1px solid var(--hair-2); }
.row:last-child { border-bottom: none; }
.clickable { cursor: pointer; border-radius: 8px; transition: background 0.12s; }
.clickable:hover { background: var(--fill); }
.avatar { flex-shrink: 0; width: 34px; height: 34px; display: grid; place-items: center; border-radius: 9px; background: var(--mint-bg); color: var(--mint); font-weight: 800; border: 1px solid var(--mint-dim); }
.n-ic { flex-shrink: 0; width: 34px; height: 34px; display: grid; place-items: center; border-radius: 9px; background: var(--surface-2); border: 1px solid var(--hair); font-size: 15px; }
.row-main { display: grid; flex: 1; min-width: 0; }
.row-main strong { color: var(--ink); font-size: 14px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.row-main small { margin-top: 2px; color: var(--ink-3); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.n-msg { font-weight: 500; }
.row.unread .n-msg { color: var(--ink); }
.dot { flex-shrink: 0; width: 7px; height: 7px; border-radius: 50%; background: var(--mint); box-shadow: 0 0 8px var(--mint); }

/* 배지 */
.badge { flex-shrink: 0; padding: 3px 9px; border-radius: 999px; font-size: 11px; font-weight: 700; }
.b-mint { color: var(--mint); background: var(--mint-bg); border: 1px solid var(--mint-dim); }
.b-violet { color: var(--violet); background: var(--violet-bg); border: 1px solid rgba(157,116,239,0.4); }
.b-ok { color: var(--ok); background: var(--ok-bg); }
.b-warn { color: var(--warn); background: var(--warn-bg); }
.b-mute { color: var(--ink-3); background: var(--fill); border: 1px solid var(--hair); }

/* 빈 상태 */
.empty { flex: 1; display: flex; align-items: center; color: var(--ink-3); font-size: 14px; padding: 8px 4px 18px; }

/* 스켈레톤 */
.sk { gap: 14px; padding-top: 26px; }
.sk-bar { height: 12px; border-radius: 6px; background: linear-gradient(90deg, var(--fill), var(--surface-2), var(--fill)); background-size: 200% 100%; animation: shimmer 1.3s infinite; }
.w40 { width: 40%; } .w70 { width: 70%; } .w80 { width: 80%; } .w90 { width: 90%; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

@media (max-width: 760px) {
  .dash { padding: 40px 16px 90px; }
  .grid { grid-template-columns: 1fr; }
  .onboard { flex-direction: column; align-items: flex-start; }
}
</style>
