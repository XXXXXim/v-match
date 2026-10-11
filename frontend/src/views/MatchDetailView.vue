<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api'
import PdfModal from '@/components/PdfModal.vue'
import InvestmentReport from '@/components/InvestmentReport.vue'
import { formatMan } from '@/utils/money'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const errorMsg = ref('')
const data = ref(null)

const kind = route.params.kind
const id = route.params.id

const matched = computed(() => data.value?.matched)
const report = computed(() => data.value?.ai_report || null)
const dd = computed(() => report.value?.report || null)
const fullReport = computed(() => dd.value?.full_report || null)
const rec = computed(() => dd.value?.recommendation || '')
const fitScore = computed(() => report.value?.fit_score ?? null)

// 분석 대상(상대). VC가 보면 스타트업, 스타트업이 보면 VC.
const subjectIsStartup = computed(() => kind === 'startup')
const su = computed(() => data.value?.startup || {})
const vc = computed(() => data.value?.vc || {})

const verdict = computed(() => {
  const s = fitScore.value || 0
  if (s >= 85) return { label: 'STRONG MATCH', cls: 'v-strong' }
  if (s >= 75) return { label: 'CONDITIONAL MATCH', cls: 'v-cond' }
  if (s >= 65) return { label: 'WATCHLIST', cls: 'v-watch' }
  return { label: 'LOW FIT', cls: 'v-low' }
})

const reportId = computed(() => {
  const mid = String(data.value?.match_id ?? id).padStart(3, '0')
  const tag = (subjectIsStartup.value ? su.value.name : vc.value.firm_name) || 'VMATCH'
  return `VX-${mid}-${tag.replace(/[^A-Za-z0-9가-힣]/g, '').slice(0, 6).toUpperCase()}`
})

const scoreColor = (s) => (s >= 4 ? 'var(--mint)' : s >= 3 ? '#38bdf8' : s >= 2 ? 'var(--warn)' : 'var(--ink-3)')

// 섹션 드릴다운: 열린 섹션 관리
const openSections = ref(new Set())
const toggleSection = (name) => {
  const next = new Set(openSections.value)
  next.has(name) ? next.delete(name) : next.add(name)
  openSections.value = next
}
const statusColor = (st) => ({ good: 'var(--mint)', ok: 'var(--warn)', risk: '#f87171', na: 'var(--ink-3)' }[st] || 'var(--ink-3)')
const statusLabel = (st) => ({ good: '양호', ok: '보통', risk: '주의', na: '–' }[st] || '–')
const gateLabel = (st) => ({ pass: '문제없음', check: '확인필요', risk: '위험' }[st] || '확인필요')

// ---- 레이더(7섹션 0~5) ----
const RAD = 92
const radarAxes = computed(() => (dd.value?.sections || []).map((s) => ({ name: s.name, score: s.score })))
const radarPoint = (i, ratio, n) => {
  const a = (-90 + (360 / n) * i) * (Math.PI / 180)
  return [120 + Math.cos(a) * RAD * ratio, 120 + Math.sin(a) * RAD * ratio]
}
const radarGrid = computed(() => {
  const n = radarAxes.value.length || 1
  return [0.25, 0.5, 0.75, 1].map((r) =>
    radarAxes.value.map((_, i) => radarPoint(i, r, n).join(',')).join(' '))
})
const radarData = computed(() => {
  const n = radarAxes.value.length || 1
  return radarAxes.value.map((ax, i) => radarPoint(i, Math.max(0.04, ax.score / 5), n))
})
const radarPoly = computed(() => radarData.value.map((p) => p.join(',')).join(' '))
const radarLabel = (i) => radarPoint(i, 1.26, radarAxes.value.length || 1)

// ---- 메트릭 카드 ----
const metrics = computed(() => {
  if (subjectIsStartup.value) {
    return [
      { k: 'CURRENT ARR', v: formatMan(su.value.revenue), tag: su.value.mom_growth ? `↑ ${su.value.mom_growth}% MoM` : '', tagOk: true },
      { k: 'NET RETENTION', v: su.value.retention_rate ? `${su.value.retention_rate}%` : '—', tag: su.value.retention_rate >= 100 ? 'EXPANSION' : '', tagOk: true },
      { k: 'MAU', v: su.value.mau ? Number(su.value.mau).toLocaleString() : '—', tag: '', tagOk: false },
      { k: 'TAM', v: su.value.market_size ? `${Number(su.value.market_size).toLocaleString()}억` : '—', tag: su.value.market_growth ? `${su.value.market_growth}% 성장` : '', tagOk: true },
    ]
  }
  return [
    { k: 'CHECK SIZE', v: `${formatMan(vc.value.min_investment)}~`, tag: '', tagOk: false },
    { k: 'MAX TICKET', v: formatMan(vc.value.max_investment), tag: '', tagOk: false },
    { k: 'SECTORS', v: `${(vc.value.preferred_industries || []).length}개`, tag: '', tagOk: false },
    { k: 'REGIONS', v: `${(vc.value.preferred_regions || []).length}개`, tag: '', tagOk: false },
  ]
})

const teamFacts = computed(() => {
  if (!subjectIsStartup.value) return []
  const f = []
  if (su.value.founder_experience_years != null) f.push(`창업자 경력 ${su.value.founder_experience_years}년`)
  if (su.value.prior_exits) f.push(`이전 Exit ${su.value.prior_exits}회`)
  if (su.value.founder_education) f.push(`${su.value.founder_education}`)
  if (su.value.team_size) f.push(`팀 ${su.value.team_size}명`)
  return f
})

const pitchOpen = ref(false)
const refreshing = ref(false)

// 관심 보내기(좋아요) / 저장(북마크) — 기본 정보 박스 아래에 배치
const togglingLike = ref(false)
const togglingBookmark = ref(false)

const onToggleLike = async () => {
  if (!data.value) return
  // 이미 매칭된 상태면 매칭 페이지로 이동
  if (data.value.is_matched) { router.push({ name: 'matches' }); return }
  togglingLike.value = true
  try {
    const res = await api.post(`/likes/${kind}/${id}/toggle/`)
    data.value.is_liked = res.data.liked
    data.value.is_matched = !!res.data.matched
    if (res.data.matched) window.alert('🎉 매칭 성사! 매칭 페이지에서 커피챗을 시작할 수 있어요.')
  } catch (e) {
    window.alert(e.response?.data?.error || '매칭 제안에 실패했습니다.')
  } finally { togglingLike.value = false }
}

const onToggleBookmark = async () => {
  if (!data.value) return
  togglingBookmark.value = true
  try {
    const res = await api.post(`/bookmarks/${kind}/${id}/toggle/`)
    data.value.is_bookmarked = res.data.bookmarked
  } catch (e) {
    window.alert(e.response?.data?.error || '저장에 실패했습니다.')
  } finally { togglingBookmark.value = false }
}

const refreshReport = async () => {
  if (!data.value?.match_id) return
  refreshing.value = true
  try {
    const res = await api.get(`/matches/${data.value.match_id}/ai-report/?refresh=1`)
    data.value.ai_report = {
      fit_score: res.data.fit_score, summary: res.data.summary,
      source: res.data.source, created_at: res.data.created_at, report: res.data.report,
    }
  } catch {
    window.alert('리포트 재생성에 실패했습니다. API 키와 서버 상태를 확인해주세요.')
  } finally { refreshing.value = false }
}

onMounted(async () => {
  try {
    data.value = (await api.get(`/match-detail/${kind}/${id}/`)).data
  } catch (err) {
    errorMsg.value = err.response?.data?.error || '상세 정보를 불러오지 못했습니다.'
  } finally { loading.value = false }
})
</script>

<template>
  <div class="report-page">
    <p v-if="loading" class="info">불러오는 중...</p>
    <p v-else-if="errorMsg" class="error">{{ errorMsg }}</p>

    <template v-else>
      <!-- 터미널 헤더 -->
      <div class="term-head">
        <div class="th-left">
          <button class="back" @click="router.back()">← TERMINAL</button>
          <span class="th-id">ANALYSIS_REPORT // ID: {{ reportId }}</span>
        </div>
        <div v-if="matched && fitScore != null" class="th-conf" :class="verdict.cls">
          <span class="cf-label">FIT SCORE</span>
          <span class="cf-score">{{ fitScore }}<span class="cf-pct">%</span></span>
          <span class="cf-tag">{{ fitScore >= 75 ? 'HIGH PRECISION' : 'STANDARD' }}</span>
        </div>
      </div>

      <!-- 매칭 전: 잠금 -->
      <div v-if="!matched" class="lock-banner">
        🔒 <strong>FIT 적합도 점수와 AI 분석 리포트</strong>는 <strong>매칭 성사(서로 좋아요)</strong> 후 제공됩니다.
        지금은 관심 여부를 판단할 수 있는 기본 정보만 보여드려요.
      </div>

      <!-- 매칭 후: HUD 3컬럼 -->
      <div v-if="matched" class="hud">
        <!-- 좌: 프로필 카드 -->
        <section class="panel profile">
          <h1 class="subj-name">{{ subjectIsStartup ? su.name : vc.firm_name }}</h1>
          <p class="subj-desc">{{ subjectIsStartup ? (su.summary || su.description || '소개가 등록되지 않았습니다.') : (vc.vc_summary || vc.bio || '투자 성향 소개가 없습니다.') }}</p>

          <dl class="spec">
            <template v-if="subjectIsStartup">
              <div><dt>STAGE</dt><dd>{{ su.stage || '—' }}</dd></div>
              <div><dt>SECTOR</dt><dd>{{ su.industry || '신규(덱 기반)' }}</dd></div>
              <div><dt>LOCATION</dt><dd>{{ su.region || '—' }}</dd></div>
              <div><dt>RAISING</dt><dd>{{ formatMan(su.funding_needed) }}</dd></div>
            </template>
            <template v-else>
              <div><dt>SECTORS</dt><dd>{{ (vc.preferred_industries || []).join(', ') || '—' }}</dd></div>
              <div><dt>REGIONS</dt><dd>{{ (vc.preferred_regions || []).join(', ') || '—' }}</dd></div>
              <div><dt>TICKET</dt><dd>{{ formatMan(vc.min_investment) }} ~ {{ formatMan(vc.max_investment) }}</dd></div>
              <div v-if="vc.website"><dt>LINK</dt><dd><a :href="vc.website" target="_blank" rel="noopener noreferrer">{{ vc.website }} ↗</a></dd></div>
            </template>
          </dl>

          <div v-if="teamFacts.length" class="team">
            <div class="block-label">TEAM STRENGTH</div>
            <ul><li v-for="(t, i) in teamFacts" :key="i"><span class="dot"></span>{{ t }}</li></ul>
          </div>
        </section>

        <!-- 중: 레이더 + 메트릭 -->
        <section class="center">
          <div class="panel radar-panel">
            <svg viewBox="0 0 240 240" class="radar">
              <polygon v-for="(p, i) in radarGrid" :key="'g'+i" :points="p" fill="none" stroke="var(--line)" stroke-width="1" />
              <line v-for="(ax, i) in radarAxes" :key="'l'+i" x1="120" y1="120" :x2="radarPoint(i,1,radarAxes.length)[0]" :y2="radarPoint(i,1,radarAxes.length)[1]" stroke="var(--line)" stroke-width="1" />
              <polygon :points="radarPoly" fill="rgba(47,227,176,0.16)" stroke="var(--mint)" stroke-width="2" />
              <circle v-for="(p, i) in radarData" :key="'c'+i" :cx="p[0]" :cy="p[1]" r="3" fill="var(--mint)" />
              <text v-for="(ax, i) in radarAxes" :key="'t'+i" :x="radarLabel(i)[0]" :y="radarLabel(i)[1]" text-anchor="middle" dominant-baseline="middle" class="rlabel">{{ ax.name }}</text>
            </svg>
            <div class="radar-cap">RADAR_MODEL // 7-AXIS DUE-DILIGENCE</div>
          </div>

          <div class="metrics">
            <div v-for="m in metrics" :key="m.k" class="metric">
              <div class="m-top"><span class="m-key">{{ m.k }}</span><span v-if="m.tag" class="m-tag" :class="{ ok: m.tagOk }">{{ m.tag }}</span></div>
              <div class="m-val">{{ m.v }}</div>
            </div>
          </div>
        </section>

        <!-- 우: AI VERDICT + KEY INSIGHTS -->
        <section class="panel verdict-panel">
          <div class="block-label">AI VERDICT</div>
          <div class="verdict" :class="verdict.cls">
            <h3>{{ verdict.label }}</h3>
            <p>{{ (report && report.summary) ? report.summary.split('\n')[0] : '데이터 기반 적합도 분석 결과입니다.' }}</p>
            <span v-if="rec" class="band">권고: {{ rec }}</span>
          </div>

          <div class="block-label mt">KEY INSIGHTS</div>
          <ol class="insights">
            <li v-for="(x, i) in (dd && dd.strengths ? dd.strengths : [])" :key="i">
              <span class="num">{{ String(i + 1).padStart(2, '0') }}</span><span class="ins-text">{{ x }}</span>
            </li>
            <li v-if="!dd || !dd.strengths || !dd.strengths.length" class="muted-li">강점 데이터가 아직 산출되지 않았습니다.</li>
          </ol>

          <div class="vp-foot">
            <button class="src-btn" :disabled="refreshing" @click="refreshReport">
              {{ refreshing ? '생성 중…' : '↻ 리포트 다시 생성' }}
            </button>
          </div>
        </section>
      </div>

      <!-- 15섹션 투자 분석 리포트 -->
      <div v-if="fullReport" class="card">
        <InvestmentReport :data="fullReport" />
      </div>

      <!-- 하단 상세 분석 -->
      <div v-if="dd && dd.sections" class="card">
        <h3>📊 섹션별 실사 평가 <span class="anchor-note">(클릭하면 지표 펼침)</span></h3>
        <div v-for="s in dd.sections" :key="s.name" class="sec-row">
          <div class="sec-head" :class="{ clickable: s.metrics && s.metrics.length }"
               @click="s.metrics && s.metrics.length && toggleSection(s.name)">
            <span class="sec-name">
              <span v-if="s.metrics && s.metrics.length" class="caret" :class="{ open: openSections.has(s.name) }">▶</span>
              {{ s.name }}
            </span>
            <span class="sec-score" :style="{ color: scoreColor(s.score) }">{{ s.score }}/5</span>
          </div>
          <div class="sec-bar"><div class="sec-fill" :style="{ width: (s.score / 5 * 100) + '%', background: scoreColor(s.score) }"></div></div>
          <p class="sec-comment">{{ s.comment }}</p>
          <div v-if="openSections.has(s.name) && s.metrics && s.metrics.length" class="metric-table">
            <div v-for="m in s.metrics" :key="m.label" class="metric-row">
              <div class="mr-top">
                <span class="mr-label">{{ m.label }}</span>
                <span class="mr-value" :style="{ color: statusColor(m.status) }">
                  {{ m.display }}<span v-if="m.benchmark" class="mr-bench"> / 기준 {{ m.benchmark }}</span>
                </span>
              </div>
              <div v-if="m.benchmark" class="mr-bar">
                <div class="mr-fill" :style="{ width: Math.min(100, m.value / m.benchmark * 100) + '%', background: statusColor(m.status) }"></div>
              </div>
              <div class="mr-bottom">
                <span class="mr-status" :style="{ color: statusColor(m.status) }">● {{ statusLabel(m.status) }}</span>
                <span class="mr-hint">{{ m.hint }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="dd && (dd.strengths?.length || dd.concerns?.length)" class="two-col">
        <div class="card half" v-if="dd.strengths?.length"><h3>✅ 강점</h3><ul><li v-for="(x, i) in dd.strengths" :key="i">{{ x }}</li></ul></div>
        <div class="card half" v-if="dd.concerns?.length"><h3>⚠️ 우려·리스크</h3><ul><li v-for="(x, i) in dd.concerns" :key="i">{{ x }}</li></ul></div>
      </div>

      <div v-if="dd && dd.hard_gates?.length" class="card">
        <h3>🚦 하드게이트 (딜킬러) 점검</h3>
        <div class="gates">
          <div v-for="g in dd.hard_gates" :key="g.item" class="gate" :class="g.status">
            <span class="gate-dot"></span><span class="gate-item">{{ g.item }}</span><span class="gate-status">{{ gateLabel(g.status) }}</span>
          </div>
        </div>
      </div>

      <div v-if="matched && report && report.summary" class="card">
        <h3>🧾 종합 요약</h3>
        <pre class="summary-pre">{{ report.summary }}</pre>
        <div class="src-row">
          <span v-if="report.source === 'fallback'" class="src">템플릿(키 미설정)</span>
          <span v-else-if="report.source === 'error'" class="src err">생성 실패</span>
          <span v-else-if="report.source" class="src ai">AI 생성 ({{ report.source === 'openai' ? 'OpenAI' : 'GMS' }})</span>
        </div>
      </div>

      <div class="card">
        <h3>기본 정보</h3>
        <div class="basic">
          <div><span class="k">투자 성향(VC)</span><span class="v">{{ vc.vc_summary || vc.bio || '—' }}</span></div>
          <div><span class="k">선호 산업</span><span class="v">{{ (vc.preferred_industries || []).join(', ') || '—' }}</span></div>
          <div v-if="vc.website"><span class="k">VC 링크</span><span class="v"><a :href="vc.website" target="_blank" rel="noopener noreferrer">{{ vc.website }} ↗</a></span></div>
          <div><span class="k">스타트업</span><span class="v">{{ su.industry || '신규(덱 기반)' }} <template v-if="su.stage">· {{ su.stage }}</template> <template v-if="su.region">· {{ su.region }}</template></span></div>
          <div><span class="k">기본 트랙션</span><span class="v">매출 {{ formatMan(su.revenue) }} · MAU {{ su.mau }} · 유지율 {{ su.retention_rate }}%</span></div>
        </div>
      </div>

      <!-- 관심 보내기 / 저장: 기본 정보 박스 '아래'에 배치 -->
      <div class="detail-actions">
        <button class="act like" :class="{ active: data.is_liked, matched: data.is_matched }"
          :disabled="togglingLike" @click="onToggleLike">
          {{ data.is_matched ? '✓ 매칭됨 · 매칭 보기'
             : data.is_liked ? '제안 취소'
             : '♡ 매칭 제안' }}
        </button>
        <button class="act" :class="{ active: data.is_bookmarked }"
          :disabled="togglingBookmark" @click="onToggleBookmark">
          {{ data.is_bookmarked ? '★ 저장됨' : '☆ 저장' }}
        </button>
      </div>
    </template>

    <PdfModal :open="pitchOpen" :url="data && data.startup ? data.startup.pitch_deck_url : null" title="피치덱 미리보기" empty-text="등록된 피치덱이 없습니다." @close="pitchOpen = false" />
  </div>
</template>

<style scoped>
.report-page { max-width: 1180px; margin: 0 auto; }
.info { color: var(--ink-2); } .error { color: var(--danger); }

/* 터미널 헤더 */
.term-head { display: flex; justify-content: space-between; align-items: center; padding-bottom: 14px; margin-bottom: 18px; border-bottom: 1px solid var(--hair); flex-wrap: wrap; gap: 8px; }
.th-left { display: flex; align-items: center; gap: 16px; }
.back { background: none; border: none; color: var(--mint); cursor: pointer; font-family: var(--mono); font-size: 12px; letter-spacing: .08em; padding: 0; }
.th-id { font-family: var(--mono); font-size: 12px; color: var(--ink-3); letter-spacing: .08em; }
.th-conf { display: flex; align-items: center; gap: 12px; padding: 8px 18px; border-radius: 12px; background: var(--mint-bg); border: 1px solid var(--mint-dim); }
.th-conf.v-cond { background: var(--warn-bg); border-color: rgba(251,191,36,.4); }
.th-conf.v-watch { background: rgba(251,146,60,.12); border-color: rgba(251,146,60,.4); }
.th-conf.v-low { background: var(--danger-bg); border-color: rgba(248,113,113,.4); }
.cf-label { font-family: var(--mono); font-size: 11px; letter-spacing: .14em; color: var(--ink-2); }
.cf-score { font-family: var(--mono); font-size: 40px; font-weight: 800; line-height: 1; color: var(--mint); letter-spacing: -.02em; }
.th-conf.v-cond .cf-score { color: var(--warn); }
.th-conf.v-watch .cf-score { color: #fb923c; }
.th-conf.v-low .cf-score { color: var(--danger); }
.cf-pct { font-size: 20px; font-weight: 700; margin-left: 1px; }
.cf-tag { font-family: var(--mono); font-size: 10px; font-weight: 700; letter-spacing: .1em; color: var(--ink-3); }

.lock-banner { background: var(--warn-bg); border: 1px solid rgba(251,191,36,.3); color: var(--warn); border-radius: 10px; padding: 14px 16px; font-size: 14px; line-height: 1.6; margin-bottom: 16px; }

/* HUD 그리드 */
.hud { display: grid; grid-template-columns: 320px 1fr 340px; gap: 16px; margin-bottom: 22px; }
.panel { position: relative; background: var(--surface); border: 1px solid var(--hair); border-radius: var(--radius); padding: 22px; }
/* 코너 브래킷 */
.panel::before, .panel::after { content: ''; position: absolute; width: 12px; height: 12px; pointer-events: none; }
.panel::before { top: 8px; left: 8px; border-top: 1px solid var(--mint-dim); border-left: 1px solid var(--mint-dim); }
.panel::after { bottom: 8px; right: 8px; border-bottom: 1px solid var(--mint-dim); border-right: 1px solid var(--mint-dim); }

.subj-name { font-size: 26px; font-weight: 800; letter-spacing: -.02em; }
.subj-desc { margin-top: 8px; color: var(--ink-2); font-size: 14px; line-height: 1.55; }
.spec { margin-top: 20px; }
.spec > div { display: flex; justify-content: space-between; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--hair-2); }
.spec dt { font-family: var(--mono); font-size: 11px; letter-spacing: .1em; color: var(--ink-3); }
.spec dd { font-size: 13px; font-weight: 700; color: var(--ink); text-align: right; word-break: break-all; }
.spec dd a { color: var(--mint); }
.team { margin-top: 20px; }
.block-label { font-family: var(--mono); font-size: 11px; letter-spacing: .12em; color: var(--mint); padding-bottom: 8px; border-bottom: 1px solid var(--hair); margin-bottom: 12px; }
.block-label.mt { margin-top: 22px; }
.team ul { list-style: none; }
.team li { display: flex; align-items: center; gap: 10px; padding: 6px 0; font-size: 13px; color: var(--ink-2); }
.team .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--mint); flex-shrink: 0; }

/* 중앙 */
.center { display: flex; flex-direction: column; gap: 16px; }
.radar-panel { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 18px; flex: 1; }
.radar { width: 100%; max-width: 320px; height: auto; }
.rlabel { font-family: var(--mono); font-size: 9px; fill: var(--ink-2); letter-spacing: .02em; }
.radar-cap { font-family: var(--mono); font-size: 10px; color: var(--ink-4); letter-spacing: .1em; margin-top: 6px; }
.metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.metric { background: var(--surface); border: 1px solid var(--hair); border-radius: 10px; padding: 16px; }
.m-top { display: flex; justify-content: space-between; align-items: center; }
.m-key { font-family: var(--mono); font-size: 10px; letter-spacing: .1em; color: var(--ink-3); }
.m-tag { font-family: var(--mono); font-size: 10px; color: var(--ink-3); }
.m-tag.ok { color: var(--mint); }
.m-val { margin-top: 12px; font-family: var(--mono); font-size: 26px; font-weight: 700; color: var(--ink); letter-spacing: -.01em; }

/* 우 */
.verdict-panel { display: flex; flex-direction: column; }
.verdict { border-left: 3px solid var(--mint); padding: 14px 16px; background: var(--mint-bg); border-radius: 0 8px 8px 0; }
.verdict.v-cond { border-left-color: var(--warn); background: var(--warn-bg); }
.verdict.v-watch { border-left-color: #fb923c; background: rgba(251,146,60,.1); }
.verdict.v-low { border-left-color: var(--danger); background: var(--danger-bg); }
.verdict h3 { font-size: 18px; font-weight: 800; letter-spacing: .02em; }
.verdict p { margin-top: 8px; font-size: 13px; color: var(--ink-2); line-height: 1.55; }
.verdict .band { display: inline-block; margin-top: 10px; font-size: 12px; font-weight: 700; color: var(--ink); opacity: .9; }
.insights { list-style: none; counter-reset: ins; }
.insights li { display: flex; gap: 12px; padding: 11px 0; border-bottom: 1px solid var(--hair-2); }
.insights .num { font-family: var(--mono); font-size: 12px; color: var(--mint); flex-shrink: 0; padding-top: 1px; }
.insights .ins-text { font-size: 13px; color: var(--ink-2); line-height: 1.55; }
.insights .muted-li { color: var(--ink-3); font-size: 13px; }
.vp-foot { margin-top: auto; padding-top: 18px; display: flex; flex-direction: column; gap: 10px; }
.src-btn { background: var(--surface-2); border: 1px solid var(--hair); color: var(--ink-2); font-size: 12px; font-weight: 600; padding: 9px; border-radius: 8px; cursor: pointer; }
.src-btn:disabled { opacity: .6; cursor: wait; }

/* 하단 카드 */
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 20px; margin-bottom: 16px; }
.card h3 { font-size: 15px; font-weight: 700; margin-bottom: 12px; color: var(--ink); }
.anchor-note { font-size: 12px; font-weight: 400; color: var(--ink-3); }
.sec-row { padding: 10px 0; border-bottom: 1px dashed var(--line); }
.sec-row:last-child { border-bottom: none; }
.sec-head { display: flex; justify-content: space-between; align-items: baseline; }
.sec-name { font-weight: 700; font-size: 14px; color: var(--ink); }
.sec-score { font-weight: 800; font-size: 14px; }
.sec-bar { margin: 6px 0; height: 6px; background: var(--fill); border-radius: 999px; overflow: hidden; }
.sec-fill { height: 100%; border-radius: 999px; transition: width .4s; }
.sec-comment { font-size: 13px; color: var(--ink-2); line-height: 1.6; }
.sec-head.clickable { cursor: pointer; user-select: none; }
.sec-head.clickable:hover .sec-name { color: var(--mint); }
.caret { display: inline-block; font-size: 9px; margin-right: 6px; color: var(--ink-3); transition: transform .15s; }
.caret.open { transform: rotate(90deg); }
.metric-table { margin-top: 12px; padding: 14px 16px; background: var(--bg-2); border: 1px solid var(--line); border-radius: 8px; display: flex; flex-direction: column; gap: 16px; }
.metric-row { display: flex; flex-direction: column; gap: 5px; }
.mr-top { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
.mr-label { font-size: 13px; font-weight: 600; color: var(--ink-2); }
.mr-value { font-family: var(--mono); font-size: 15px; font-weight: 800; white-space: nowrap; }
.mr-bench { font-family: var(--mono); font-size: 11px; font-weight: 400; color: var(--ink-3); }
.mr-bar { height: 6px; background: var(--line); border-radius: 3px; overflow: hidden; }
.mr-fill { height: 100%; border-radius: 3px; transition: width .3s ease; }
.mr-bottom { display: flex; align-items: center; gap: 10px; margin-top: 2px; }
.mr-status { font-size: 11px; font-weight: 700; white-space: nowrap; }
.mr-hint { font-size: 11px; color: var(--ink-3); }
.two-col { display: flex; gap: 14px; }
.card.half { flex: 1; }
.card.half ul { margin: 0; padding-left: 18px; }
.card.half li { font-size: 14px; color: var(--ink-2); line-height: 1.8; }
.gates { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.gate { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 8px; font-size: 13px; background: var(--surface-2); }
.gate-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.gate-item { flex: 1; color: var(--ink-2); }
.gate-status { font-weight: 700; font-size: 12px; }
.gate.pass { background: var(--ok-bg); } .gate.pass .gate-dot { background: var(--ok); } .gate.pass .gate-status { color: var(--ok); }
.gate.check { background: var(--warn-bg); } .gate.check .gate-dot { background: var(--warn); } .gate.check .gate-status { color: var(--warn); }
.gate.risk { background: var(--danger-bg); } .gate.risk .gate-dot { background: var(--danger); } .gate.risk .gate-status { color: var(--danger); }
.summary-pre { white-space: pre-wrap; font-family: inherit; font-size: 14px; line-height: 1.7; color: var(--ink); background: var(--bg-2); border-radius: 8px; padding: 16px; border: 1px solid var(--line); }
.src-row { margin-top: 10px; }
.src { font-size: 11px; background: var(--warn-bg); color: var(--warn); padding: 3px 10px; border-radius: 999px; font-weight: 600; }
.src.ai { background: var(--mint-bg); color: var(--mint); }
.src.err { background: var(--danger-bg); color: var(--danger); }
.basic > div { display: flex; gap: 12px; padding: 7px 0; border-bottom: 1px dashed var(--line); font-size: 14px; }
.basic .k { width: 110px; color: var(--ink-3); flex-shrink: 0; } .basic .v { color: var(--ink-2); }
.basic .v a { color: var(--mint); font-weight: 600; word-break: break-all; }

.detail-actions { display: flex; gap: 10px; margin: 4px 0 24px; }
.act { padding: 11px 22px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--ink); cursor: pointer; font-weight: 600; font-size: 15px; }
.act:disabled { opacity: .55; cursor: wait; }
.act.active { background: var(--warn-bg); border-color: var(--warn); color: var(--warn); }
.act.like.active { background: var(--pink-bg); border-color: var(--pink); color: var(--pink); }
.act.like.matched { background: var(--ok-bg); border-color: var(--ok); color: var(--ok); }

@media (max-width: 980px) {
  .hud { grid-template-columns: 1fr; }
  .two-col { flex-direction: column; }
}
</style>
