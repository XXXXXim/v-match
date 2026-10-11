<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import { VC_INDUSTRY_OPTIONS, ALL_INDUSTRY, VC_REGION_OPTIONS } from '@/constants/options'
import { formatMan } from '@/utils/money'

const EDUCATIONS = ['고졸', '전문대졸', '대졸', '석사', '박사', '무관']
const MAX_WON = 10000000000   // 슬라이더 상한 100억
const STEP = 10000000         // 1천만원 단위

const router = useRouter()
const loading = ref(true)

const pref = ref({ preferred_industries: [], preferred_regions: [], preferred_education: [], min_won: 0, max_won: 0 })
const prefSaving = ref(false)

const docs = ref([])
const file = ref(null)
const title = ref('')
const uploading = ref(false)

const msg = ref(''); const msgType = ref('success')
const flash = (text, type = 'success') => {
  msg.value = text; msgType.value = type
  setTimeout(() => { if (msg.value === text) msg.value = '' }, 4000)
}
const registered = computed(() => docs.value.length > 0)

// 슬라이더 표시값(만원 단위 변환)
const minMan = computed(() => Math.round(pref.value.min_won / 10000))
const maxMan = computed(() => Math.round(pref.value.max_won / 10000))
const minPct = computed(() => Math.min(100, (pref.value.min_won / MAX_WON) * 100))
const maxPct = computed(() => Math.min(100, (pref.value.max_won / MAX_WON) * 100))
const onMinSlide = (e) => {
  const v = Number(e.target.value)
  pref.value.min_won = Math.min(v, pref.value.max_won)
}
const onMaxSlide = (e) => {
  const v = Number(e.target.value)
  pref.value.max_won = Math.max(v, pref.value.min_won)
}

const toggleIndustry = (ind) => {
  const list = pref.value.preferred_industries
  if (ind === ALL_INDUSTRY) { pref.value.preferred_industries = list.includes(ALL_INDUSTRY) ? [] : [ALL_INDUSTRY]; return }
  const next = list.filter((x) => x !== ALL_INDUSTRY)
  pref.value.preferred_industries = next.includes(ind) ? next.filter((x) => x !== ind) : [...next, ind]
}
const toggleMulti = (key, val) => {
  const list = pref.value[key]
  pref.value[key] = list.includes(val) ? list.filter((x) => x !== val) : [...list, val]
}
const isOn = (key, val) => pref.value[key].includes(val)

const loadAll = async () => {
  loading.value = true
  try {
    const d = (await api.get('/vc-profile/')).data
    pref.value = {
      preferred_industries: d.preferred_industries || [],
      preferred_regions: d.preferred_regions || [],
      preferred_education: d.preferred_education || [],
      min_won: (d.min_investment || 0) * 10000,
      max_won: (d.max_investment || 0) * 10000,
    }
  } catch { /* 미등록 */ }
  try { const r = await api.get('/vc-profile/portfolio/'); docs.value = Array.isArray(r.data) ? r.data : [] }
  catch { docs.value = [] }
  loading.value = false
}

const savePref = async () => {
  prefSaving.value = true
  try {
    await api.put('/vc-profile/', {
      preferred_industries: pref.value.preferred_industries,
      preferred_regions: pref.value.preferred_regions,
      preferred_education: pref.value.preferred_education,
      min_investment: Math.round(Number(pref.value.min_won) / 10000),
      max_investment: Math.round(Number(pref.value.max_won) / 10000),
    })
    flash('저장되었습니다.')
  } catch (e) {
    flash(e.response?.data?.detail || e.response?.data?.error || '선호도 저장에 실패했습니다.', 'error')
  } finally { prefSaving.value = false }
}

const pick = (e) => { file.value = e.target.files[0] || null }
const upload = async () => {
  if (!file.value) return flash('프로필 자료 PDF를 선택해주세요.', 'error')
  if (!file.value.name.toLowerCase().endsWith('.pdf')) return flash('PDF 파일만 업로드 가능합니다.', 'error')
  uploading.value = true
  try {
    const fd = new FormData(); fd.append('file', file.value); if (title.value) fd.append('title', title.value)
    await api.post('/vc-profile/portfolio/', fd)
    file.value = null; title.value = ''; flash('프로필 자료가 등록되었습니다.')
    const r = await api.get('/vc-profile/portfolio/'); docs.value = Array.isArray(r.data) ? r.data : []
  } catch (e) { flash(e.response?.data?.error || '등록에 실패했습니다.', 'error') }
  finally { uploading.value = false }
}

const goRecommend = () => router.push({ name: 'startup-results' })
onMounted(loadAll)
</script>

<template>
  <div class="calib">
    <header class="calib-top">
      <div class="brand"><span class="dot"></span> V-MATCH</div>
      <div class="steps">
        <span class="step active"><b>01</b> INVESTMENT THESIS</span>
        <span class="step"><b>02</b> PORTFOLIO</span>
      </div>
    </header>

    <p v-if="loading" class="info">불러오는 중...</p>

    <template v-else>
      <div class="panel-wrap">
        <div class="vlabel">CALIBRATION_SEQUENCE_01</div>

        <div class="panel">
          <h1 class="p-title">투자 논리 설정</h1>
          <p class="p-sub">귀사의 펀드 운용 전략에 최적화된 딜을 필터링하기 위한 기초 설정을 진행합니다.</p>

          <div v-if="registered" class="done-banner">
            ✅ 프로필 등록이 완료되었습니다!
            <button class="go-btn" @click="goRecommend">스타트업 찾기 →</button>
          </div>
          <div v-if="msg" class="flash" :class="msgType">{{ msg }}</div>

          <!-- AVERAGE CHECK SIZE -->
          <div class="block">
            <div class="block-label">AVERAGE CHECK SIZE</div>
            <div class="dual">
              <div class="track"><div class="track-fill" :style="{ left: minPct + '%', width: (maxPct - minPct) + '%' }"></div></div>
              <input type="range" :min="0" :max="MAX_WON" :step="STEP" :value="pref.min_won" @input="onMinSlide" class="rng rng-min" />
              <input type="range" :min="0" :max="MAX_WON" :step="STEP" :value="pref.max_won" @input="onMaxSlide" class="rng rng-max" />
            </div>
            <div class="dual-cap">
              <span>0원</span>
              <span class="selected">SELECTED: {{ formatMan(minMan) }} ~ {{ formatMan(maxMan) }}</span>
              <span>100억+</span>
            </div>
          </div>

          <!-- FOCUS SECTORS -->
          <div class="block">
            <div class="block-label">FOCUS SECTORS <span class="hint">('All' 선택 시 전 산업)</span></div>
            <div class="chips">
              <button v-for="ind in VC_INDUSTRY_OPTIONS" :key="ind" type="button" class="chip"
                :class="{ on: isOn('preferred_industries', ind), all: ind === 'All' }"
                @click="toggleIndustry(ind)">{{ ind === 'All' ? '🌐 All' : ind }}</button>
            </div>
          </div>

          <!-- TARGET REGIONS -->
          <div class="block">
            <div class="block-label">TARGET REGIONS</div>
            <div class="chips">
              <button v-for="rg in VC_REGION_OPTIONS" :key="rg" type="button" class="chip"
                :class="{ on: isOn('preferred_regions', rg) }" @click="toggleMulti('preferred_regions', rg)">{{ rg }}</button>
            </div>
          </div>

          <!-- FOUNDER EDUCATION -->
          <div class="block">
            <div class="block-label">FOUNDER EDUCATION <span class="hint">(복수 선택)</span></div>
            <div class="chips">
              <button v-for="e in EDUCATIONS" :key="e" type="button" class="chip"
                :class="{ on: isOn('preferred_education', e) }" @click="toggleMulti('preferred_education', e)">{{ e }}</button>
            </div>
          </div>

          <div class="p-foot">
            <button class="cancel" @click="router.back()">CANCEL</button>
            <button class="save" :disabled="prefSaving" @click="savePref">{{ prefSaving ? '저장 중...' : '저장하기' }}</button>
          </div>
        </div>
      </div>

      <!-- 포트폴리오 업로드 -->
      <div class="doc-card" :class="{ complete: registered }">
        <div class="dc-head">
          <div class="block-label" style="border:0;padding:0;margin:0;">PORTFOLIO // 프로필 자료 등록</div>
          <span v-if="registered" class="badge ok">{{ docs.length }}건</span>
          <span v-else class="badge">미등록</span>
        </div>
        <p class="hint2">투자 분야·이력을 담은 프로필 자료 (PDF)</p>
        <div class="row"><input type="text" v-model="title" placeholder="자료 제목 (선택)" class="title-input" /></div>
        <div class="row">
          <input type="file" accept="application/pdf" @change="pick" />
          <button class="upload-btn" :disabled="uploading" @click="upload">{{ uploading ? '업로드 중...' : '등록' }}</button>
        </div>
        <ul v-if="docs.length" class="doc-list">
          <li v-for="d in docs" :key="d.id"><a :href="d.file_url" target="_blank" rel="noopener noreferrer">📄 {{ d.title || '포트폴리오' }} ↗</a></li>
        </ul>
      </div>
    </template>
  </div>
</template>

<style scoped>
.calib { max-width: 860px; margin: 0 auto; }
.calib-top { display: flex; justify-content: space-between; align-items: center; padding-bottom: 18px; margin-bottom: 22px; }
.brand { display: flex; align-items: center; gap: 8px; font-family: var(--mono); font-weight: 700; letter-spacing: .1em; font-size: 14px; }
.brand .dot { width: 14px; height: 14px; border-radius: 50%; border: 2px solid var(--mint); box-shadow: 0 0 10px var(--mint-dim); }
.steps { display: flex; gap: 20px; }
.step { font-family: var(--mono); font-size: 11px; letter-spacing: .08em; color: var(--ink-4); }
.step b { color: var(--ink-4); margin-right: 4px; }
.step.active { color: var(--ink-2); } .step.active b { color: var(--mint); }
.info { color: var(--ink-2); }

.panel-wrap { position: relative; padding-left: 34px; }
.vlabel { position: absolute; left: 0; top: 40px; writing-mode: vertical-rl; transform: rotate(180deg); font-family: var(--mono); font-size: 10px; letter-spacing: .25em; color: var(--ink-4); }
.panel { position: relative; background: linear-gradient(160deg, rgba(18,24,21,.9), rgba(14,19,17,.95)); border: 1px solid var(--hair); border-radius: 16px; padding: 32px; overflow: hidden; }
.panel::after { content: ''; position: absolute; top: -40%; right: -20%; width: 60%; height: 160%; background: radial-gradient(ellipse, var(--mint-bg), transparent 70%); pointer-events: none; }
.p-title { font-size: 30px; font-weight: 800; letter-spacing: -.02em; position: relative; }
.p-sub { margin-top: 8px; color: var(--ink-2); font-size: 14px; position: relative; }

.done-banner { margin-top: 18px; padding: 14px 16px; background: var(--ok-bg); border: 1px solid rgba(74,222,128,.4); border-radius: 12px; color: var(--ok); font-weight: 700; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.go-btn { background: var(--ok); color: var(--on-mint); border: none; padding: 8px 14px; border-radius: 8px; font-weight: 700; cursor: pointer; }
.flash { margin-top: 14px; padding: 10px 14px; border-radius: 8px; font-size: 14px; }
.flash.success { background: var(--ok-bg); color: var(--ok); }
.flash.error { background: var(--danger-bg); color: var(--danger); }

.block { margin-top: 26px; position: relative; }
.block-label { font-family: var(--mono); font-size: 11px; letter-spacing: .12em; color: var(--mint); padding-bottom: 10px; }
.hint { color: var(--ink-4); letter-spacing: 0; }

/* 듀얼 슬라이더 */
.dual { position: relative; height: 36px; }
.track { position: absolute; top: 16px; left: 0; right: 0; height: 4px; background: var(--fill); border-radius: 999px; }
.track-fill { position: absolute; top: 0; height: 100%; background: linear-gradient(90deg, var(--mint-deep), var(--mint)); border-radius: 999px; box-shadow: 0 0 10px var(--mint-dim); }
.rng { position: absolute; top: 6px; left: 0; width: 100%; height: 24px; -webkit-appearance: none; appearance: none; background: transparent; pointer-events: none; margin: 0; }
.rng::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 20px; height: 20px; border-radius: 50%; background: #fff; border: 3px solid var(--mint); box-shadow: 0 2px 8px rgba(0,0,0,.5); cursor: pointer; pointer-events: auto; }
.rng::-moz-range-thumb { width: 20px; height: 20px; border-radius: 50%; background: #fff; border: 3px solid var(--mint); cursor: pointer; pointer-events: auto; }
.rng:focus { outline: none; box-shadow: none; }
.dual-cap { margin-top: 8px; display: flex; justify-content: space-between; align-items: center; font-family: var(--mono); font-size: 11px; color: var(--ink-4); }
.dual-cap .selected { color: var(--mint); letter-spacing: .04em; }

.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { padding: 8px 16px; border: 1px solid var(--line); border-radius: 999px; background: var(--surface); cursor: pointer; font-size: 13px; color: var(--ink-2); transition: all .12s; }
.chip:hover { border-color: var(--mint-dim); }
.chip.on { background: var(--mint-bg); border-color: var(--mint); color: var(--mint); }
.chip.all { font-weight: 700; }

.p-foot { margin-top: 30px; display: flex; justify-content: space-between; align-items: center; }
.cancel { background: none; border: none; color: var(--ink-3); font-family: var(--mono); font-size: 12px; letter-spacing: .08em; cursor: pointer; }
.save { background: var(--mint); color: var(--on-mint); border: none; padding: 13px 28px; border-radius: 10px; font-weight: 700; font-size: 14px; cursor: pointer; transition: background .15s; }
.save:hover:not(:disabled) { background: var(--mint-br); }
.save:disabled { opacity: .6; cursor: wait; }

.doc-card { margin: 22px 0 0 34px; background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 22px; }
.doc-card.complete { border-color: rgba(110,231,183,.4); }
.dc-head { display: flex; align-items: center; gap: 10px; }
.hint2 { margin-top: 8px; color: var(--ink-3); font-size: 13px; }
.row { margin-top: 12px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.title-input { flex: 1; min-width: 220px; padding: 9px 12px; border: 1px solid var(--line); border-radius: 8px; font-size: 14px; }
.upload-btn { padding: 10px 18px; border-radius: 8px; border: 1px solid var(--mint-dim); background: var(--mint-bg); color: var(--mint); font-weight: 600; cursor: pointer; font-size: 14px; }
.upload-btn:disabled { opacity: .6; cursor: wait; }
.badge { font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 999px; background: var(--fill); color: var(--ink-3); }
.badge.ok { background: var(--ok-bg); color: var(--ok); }
.doc-list { margin-top: 14px; list-style: none; }
.doc-list li { padding: 6px 0; font-size: 14px; }
.doc-list a { color: var(--mint); font-weight: 600; }

@media (max-width: 640px) {
  .panel-wrap { padding-left: 24px; } .vlabel { font-size: 9px; }
  .panel { padding: 22px; } .doc-card { margin-left: 24px; }
  .steps { display: none; }
}
</style>
