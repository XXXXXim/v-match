<script setup>
import { formatMan } from '@/utils/money'

const props = defineProps({ data: { type: Object, required: true } })

const ratingColor = (r) => ({
  'Strong Buy': '#2fe3b0', 'Buy': '#5cf2c8', 'Neutral': '#aab3ae',
  'Caution': '#fbbf24', 'Reject': '#f87171',
}[r] || '#aab3ae')

const scoreColor = (n) =>
  (n >= 80 ? 'var(--mint)' : n >= 60 ? '#5cf2c8' : n >= 40 ? 'var(--warn)' : '#f87171')

const levelColor = (lv) =>
  ({ '높음': '#f87171', '보통': 'var(--warn)', '낮음': 'var(--mint)' }[lv] || 'var(--ink-3)')

// Exit·모방가능성 등은 '높음'이 좋을 수도/나쁠 수도 → 문맥별로 구분
const imitationColor = (lv) =>
  ({ '낮음': 'var(--mint)', '보통': 'var(--warn)', '높음': '#f87171' }[lv] || 'var(--ink-3)')

const won = (v) => {
  if (v == null || v === '') return '–'
  if (typeof v === 'string') return v
  return (v < 0 ? '-' : '') + formatMan(Math.abs(v))
}

const psLabels = { severity: '문제 심각성', pain_point: '고객 Pain Point', market_need: '시장 니즈', solution_fit: '솔루션 적합도' }
const teamLabels = { dev: '개발', biz: '사업', sales: '영업', ops: '운영' }
const attLabels = { market: '시장성', product: '제품력', team: '팀', growth: '성장성', profitability: '수익성', scalability: '확장성', exit: '투자회수' }
const vcLabels = { seed: 'Seed VC', series_a: 'Series A VC', growth: 'Growth VC' }
</script>

<template>
  <div class="ib-report">
    <!-- 헤더 -->
    <div class="ib-head">
      <div>
        <span class="ib-kicker">INVESTMENT ANALYSIS REPORT</span>
        <h2 class="ib-title">{{ data.company_overview?.name }} 투자 분석 리포트</h2>
      </div>
      <div class="rating-badge" :style="{ borderColor: ratingColor(data.rating), color: ratingColor(data.rating) }">
        {{ data.rating }}
      </div>
    </div>

    <!-- 1. Executive Summary -->
    <section class="ib-sec">
      <h3><span class="num">01</span> Executive Summary</h3>
      <p class="one-liner" v-if="data.executive_summary?.one_liner">{{ data.executive_summary.one_liner }}</p>
      <div class="two-grid">
        <div class="mini-card">
          <h4 class="pos">핵심 투자 포인트</h4>
          <ul><li v-for="(p, i) in data.executive_summary?.investment_points || []" :key="i">{{ p }}</li></ul>
        </div>
        <div class="mini-card">
          <h4 class="neg">주요 리스크</h4>
          <ul><li v-for="(r, i) in data.executive_summary?.key_risks || []" :key="i">{{ r }}</li></ul>
        </div>
      </div>
      <p class="opinion" v-if="data.executive_summary?.opinion">{{ data.executive_summary.opinion }}</p>
    </section>

    <!-- 2. 기업 개요 -->
    <section class="ib-sec" v-if="data.company_overview">
      <h3><span class="num">02</span> 기업 개요</h3>
      <div class="kv-grid">
        <div><span class="k">회사명</span><span class="v">{{ data.company_overview.name }}</span></div>
        <div><span class="k">설립연도</span><span class="v">{{ data.company_overview.founded }}</span></div>
        <div><span class="k">업종</span><span class="v">{{ data.company_overview.industry }}</span></div>
        <div><span class="k">투자 단계</span><span class="v">{{ data.company_overview.stage }}</span></div>
      </div>
      <p class="biz-model" v-if="data.company_overview.business_model">{{ data.company_overview.business_model }}</p>
    </section>

    <!-- 3. 시장 분석 (TAM/SAM/SOM) -->
    <section class="ib-sec" v-if="data.market?.sizing">
      <h3><span class="num">03</span> 시장 분석
        <span class="cagr-tag" v-if="data.market.sizing.cagr">CAGR {{ data.market.sizing.cagr }}%</span>
      </h3>
      <div class="funnel">
        <div v-for="key in ['tam','sam','som']" :key="key" class="funnel-row" v-show="data.market.sizing[key]">
          <div class="funnel-bar" :class="key">
            <span class="funnel-label">{{ key.toUpperCase() }}</span>
            <span class="funnel-value">{{ data.market.sizing[key].display }}</span>
          </div>
          <span class="funnel-basis">{{ data.market.sizing[key].basis }}</span>
        </div>
      </div>
      <div class="chips" v-if="data.market.trends?.length || data.market.drivers?.length || data.market.regulations?.length">
        <template v-for="(t, i) in data.market.trends || []" :key="'t'+i"><span class="chip trend">트렌드 · {{ t }}</span></template>
        <template v-for="(d, i) in data.market.drivers || []" :key="'d'+i"><span class="chip driver">동력 · {{ d }}</span></template>
        <template v-for="(r, i) in data.market.regulations || []" :key="'r'+i"><span class="chip reg">규제 · {{ r }}</span></template>
      </div>
      <p class="sec-note" v-if="data.market.comment">{{ data.market.comment }}</p>
    </section>

    <!-- 4. 문제 해결력 -->
    <section class="ib-sec" v-if="data.problem_solving?.scores && Object.keys(data.problem_solving.scores).length">
      <h3><span class="num">04</span> 문제 해결력 분석
        <span class="total-tag" v-if="data.problem_solving.total != null">총점 {{ data.problem_solving.total }}/100</span>
      </h3>
      <div class="score-bars">
        <div v-for="(k) in Object.keys(psLabels)" :key="k" class="score-bar" v-show="data.problem_solving.scores[k] != null">
          <span class="sb-label">{{ psLabels[k] }}</span>
          <div class="sb-track"><div class="sb-fill" :style="{ width: data.problem_solving.scores[k] + '%', background: scoreColor(data.problem_solving.scores[k]) }"></div></div>
          <span class="sb-val" :style="{ color: scoreColor(data.problem_solving.scores[k]) }">{{ data.problem_solving.scores[k] }}</span>
        </div>
      </div>
      <p class="sec-note" v-if="data.problem_solving.comment">{{ data.problem_solving.comment }}</p>
    </section>

    <!-- 5. 제품 경쟁력 -->
    <section class="ib-sec" v-if="data.product">
      <h3><span class="num">05</span> 제품 경쟁력 분석
        <span class="pill" v-if="data.product.imitation_risk" :style="{ color: imitationColor(data.product.imitation_risk), borderColor: imitationColor(data.product.imitation_risk) }">모방 가능성 {{ data.product.imitation_risk }}</span>
      </h3>
      <p class="biz-model" v-if="data.product.differentiation">{{ data.product.differentiation }}</p>
      <div class="chips" v-if="data.product.barriers?.length">
        <span class="chip moat" v-for="(b, i) in data.product.barriers" :key="i">🛡 {{ b }}</span>
      </div>
      <p class="sec-note" v-if="data.product.comment">{{ data.product.comment }}</p>
    </section>

    <!-- 6. 경쟁사 비교 -->
    <section class="ib-sec" v-if="data.competitors?.length">
      <h3><span class="num">06</span> 경쟁사 비교 분석</h3>
      <div class="table-wrap">
        <table class="cmp-table">
          <thead><tr><th>경쟁사</th><th>점유율</th><th>기술력</th><th>투자유치</th><th>차별점</th></tr></thead>
          <tbody>
            <tr v-for="(c, i) in data.competitors" :key="i">
              <td class="cname">{{ c.name }}</td>
              <td>{{ c.market_share || '–' }}</td>
              <td>{{ c.tech || '–' }}</td>
              <td>{{ c.funding || '–' }}</td>
              <td class="diff">{{ c.differentiator || '–' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 7. 창업자 및 팀 -->
    <section class="ib-sec" v-if="data.team">
      <h3><span class="num">07</span> 창업자 및 팀 분석</h3>
      <p class="biz-model" v-if="data.team.founder_fit"><strong>Founder Fit ·</strong> {{ data.team.founder_fit }}</p>
      <div class="score-bars" v-if="data.team.completeness && Object.keys(data.team.completeness).length">
        <div v-for="k in Object.keys(teamLabels)" :key="k" class="score-bar" v-show="data.team.completeness[k] != null">
          <span class="sb-label">{{ teamLabels[k] }}</span>
          <div class="sb-track"><div class="sb-fill" :style="{ width: data.team.completeness[k] + '%', background: scoreColor(data.team.completeness[k]) }"></div></div>
          <span class="sb-val" :style="{ color: scoreColor(data.team.completeness[k]) }">{{ data.team.completeness[k] }}</span>
        </div>
      </div>
      <p class="sec-note" v-if="data.team.comment">{{ data.team.comment }}</p>
    </section>

    <!-- 8. 비즈니스 모델 -->
    <section class="ib-sec" v-if="data.business_model">
      <h3><span class="num">08</span> 비즈니스 모델 분석</h3>
      <div class="kv-grid">
        <div v-if="data.business_model.revenue_structure"><span class="k">수익 구조</span><span class="v">{{ data.business_model.revenue_structure }}</span></div>
        <div v-if="data.business_model.acquisition"><span class="k">고객 확보</span><span class="v">{{ data.business_model.acquisition }}</span></div>
        <div v-if="data.business_model.unit_economics"><span class="k">Unit Economics</span><span class="v">{{ data.business_model.unit_economics }}</span></div>
      </div>
      <p class="sec-note" v-if="data.business_model.comment">{{ data.business_model.comment }}</p>
    </section>

    <!-- 9. 재무 분석 -->
    <section class="ib-sec" v-if="data.financials">
      <h3><span class="num">09</span> 재무 분석
        <span class="src-tag" v-if="data.financials.source">{{ data.financials.source }}</span>
      </h3>
      <div class="fin-grid">
        <div class="fin-cell"><span class="fc-k">매출</span><span class="fc-v">{{ won(data.financials.revenue) }}</span></div>
        <div class="fin-cell"><span class="fc-k">영업이익</span><span class="fc-v" :class="{ neg: data.financials.operating_income < 0 }">{{ won(data.financials.operating_income) }}</span></div>
        <div class="fin-cell"><span class="fc-k">당기순이익</span><span class="fc-v" :class="{ neg: data.financials.net_income < 0 }">{{ won(data.financials.net_income) }}</span></div>
        <div class="fin-cell"><span class="fc-k">월 Burn rate</span><span class="fc-v">{{ won(data.financials.burn_rate) }}</span></div>
        <div class="fin-cell"><span class="fc-k">Runway</span><span class="fc-v">{{ data.financials.runway_months ? data.financials.runway_months + '개월' : '–' }}</span></div>
        <div class="fin-cell" v-if="data.financials.debt_ratio != null"><span class="fc-k">부채비율</span><span class="fc-v">{{ data.financials.debt_ratio }}%</span></div>
      </div>
      <p class="warn-line" v-if="data.financials.capital_impairment">⚠ 자본잠식 상태 — 자본구조 면밀 검토 필요</p>
    </section>

    <!-- 10. 투자 매력도 -->
    <section class="ib-sec" v-if="data.attractiveness?.scores && Object.keys(data.attractiveness.scores).length">
      <h3><span class="num">10</span> 투자 매력도 분석
        <span class="total-tag" v-if="data.attractiveness.total != null">종합 {{ data.attractiveness.total }}/100</span>
      </h3>
      <div class="score-bars">
        <div v-for="k in Object.keys(attLabels)" :key="k" class="score-bar" v-show="data.attractiveness.scores[k] != null">
          <span class="sb-label">{{ attLabels[k] }}</span>
          <div class="sb-track"><div class="sb-fill" :style="{ width: data.attractiveness.scores[k] + '%', background: scoreColor(data.attractiveness.scores[k]) }"></div></div>
          <span class="sb-val" :style="{ color: scoreColor(data.attractiveness.scores[k]) }">{{ data.attractiveness.scores[k] }}</span>
        </div>
      </div>
    </section>

    <!-- 11. 리스크 -->
    <section class="ib-sec" v-if="data.risks?.length">
      <h3><span class="num">11</span> 리스크 분석</h3>
      <div class="risk-list">
        <div v-for="(r, i) in data.risks" :key="i" class="risk-card">
          <div class="risk-top">
            <span class="risk-type">{{ r.type }}</span>
            <span class="risk-meta">발생 <b :style="{ color: levelColor(r.probability) }">{{ r.probability }}</b> · 영향 <b :style="{ color: levelColor(r.impact) }">{{ r.impact }}</b></span>
          </div>
          <p>{{ r.desc }}</p>
        </div>
      </div>
    </section>

    <!-- 12. Exit -->
    <section class="ib-sec" v-if="data.exit?.scenarios?.length">
      <h3><span class="num">12</span> Exit 가능성 분석</h3>
      <div class="exit-row">
        <div v-for="(s, i) in data.exit.scenarios" :key="i" class="exit-card">
          <div class="exit-head"><span class="exit-type">{{ s.type }}</span><span class="exit-score" :style="{ color: scoreColor(s.score) }">{{ s.score }}</span></div>
          <div class="sb-track"><div class="sb-fill" :style="{ width: s.score + '%', background: scoreColor(s.score) }"></div></div>
          <p>{{ s.desc }}</p>
        </div>
      </div>
      <p class="sec-note" v-if="data.exit.comment">{{ data.exit.comment }}</p>
    </section>

    <!-- 13. VC 적합도 -->
    <section class="ib-sec" v-if="data.vc_fit && Object.keys(data.vc_fit).length">
      <h3><span class="num">13</span> VC 적합도 분석</h3>
      <div class="score-bars">
        <div v-for="k in Object.keys(vcLabels)" :key="k" class="score-bar" v-show="data.vc_fit[k] != null">
          <span class="sb-label">{{ vcLabels[k] }}</span>
          <div class="sb-track"><div class="sb-fill" :style="{ width: data.vc_fit[k] + '%', background: scoreColor(data.vc_fit[k]) }"></div></div>
          <span class="sb-val" :style="{ color: scoreColor(data.vc_fit[k]) }">{{ data.vc_fit[k] }}</span>
        </div>
      </div>
      <p class="sec-note" v-if="data.vc_fit.recommended"><strong>추천 VC 유형 ·</strong> {{ data.vc_fit.recommended }}</p>
    </section>

    <!-- 14. 심사역 코멘트 -->
    <section class="ib-sec" v-if="data.analyst_comment">
      <h3><span class="num">14</span> 투자 심사역 코멘트</h3>
      <div class="three-grid">
        <div class="mini-card">
          <h4 class="pos">찬성</h4>
          <ul><li v-for="(p, i) in data.analyst_comment.pros || []" :key="i">{{ p }}</li></ul>
        </div>
        <div class="mini-card">
          <h4 class="neg">반대</h4>
          <ul><li v-for="(c, i) in data.analyst_comment.cons || []" :key="i">{{ c }}</li></ul>
        </div>
        <div class="mini-card">
          <h4 class="dd">추가 실사</h4>
          <ul><li v-for="(d, i) in data.analyst_comment.due_diligence || []" :key="i">{{ d }}</li></ul>
        </div>
      </div>
    </section>

    <!-- 15. 최종 투자 의견 -->
    <section class="ib-sec final" v-if="data.final">
      <h3><span class="num">15</span> 최종 투자 의견</h3>
      <div class="final-head">
        <div class="rating-badge lg" :style="{ borderColor: ratingColor(data.rating), color: ratingColor(data.rating) }">{{ data.rating }}</div>
        <div class="final-kv">
          <div v-if="data.final.target_valuation"><span class="k">목표 기업가치</span><span class="v">{{ data.final.target_valuation }}</span></div>
          <div v-if="data.final.recommended_amount"><span class="k">권장 투자금액</span><span class="v">{{ data.final.recommended_amount }}</span></div>
        </div>
      </div>
      <p class="conclusion" v-if="data.final.conclusion">{{ data.final.conclusion }}</p>
    </section>

    <p class="ib-disclaimer">본 리포트는 AI가 제공된 데이터를 기반으로 생성한 분석이며, 실제 투자 결정의 근거가 아닙니다.</p>
  </div>
</template>

<style scoped>
.ib-report { display: flex; flex-direction: column; gap: 22px; }

.ib-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; padding-bottom: 18px; border-bottom: 1px solid var(--line); }
.ib-kicker { font-family: var(--mono); font-size: 11px; letter-spacing: 0.12em; color: var(--ink-3); }
.ib-title { font-size: 22px; margin-top: 4px; color: var(--ink); }
.rating-badge { flex-shrink: 0; padding: 8px 16px; border: 1.5px solid; border-radius: 8px; font-weight: 800; font-size: 16px; letter-spacing: 0.02em; }
.rating-badge.lg { font-size: 22px; padding: 12px 22px; }

.ib-sec { display: flex; flex-direction: column; gap: 12px; }
.ib-sec h3 { display: flex; align-items: center; gap: 10px; font-size: 16px; color: var(--ink); flex-wrap: wrap; }
.ib-sec h3 .num { font-family: var(--mono); font-size: 12px; color: var(--mint); background: var(--mint-bg); padding: 3px 7px; border-radius: 5px; }
.ib-sec.final { background: var(--bg-2); border: 1px solid var(--line); border-radius: var(--radius); padding: 20px; }

.one-liner { font-size: 16px; font-weight: 600; color: var(--ink); line-height: 1.6; }
.opinion { font-size: 14px; color: var(--ink-2); line-height: 1.7; padding: 12px 14px; background: var(--mint-bg); border-radius: 8px; }
.sec-note { font-size: 13px; color: var(--ink-2); line-height: 1.7; }
.biz-model { font-size: 14px; color: var(--ink-2); line-height: 1.7; }

.two-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.three-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
.mini-card { background: var(--bg-2); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }
.mini-card h4 { font-size: 13px; margin-bottom: 8px; }
.mini-card h4.pos { color: var(--mint); }
.mini-card h4.neg { color: #f87171; }
.mini-card h4.dd { color: #38bdf8; }
.mini-card ul { margin: 0; padding-left: 16px; }
.mini-card li { font-size: 13px; color: var(--ink-2); line-height: 1.6; margin-bottom: 4px; }

.kv-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 18px; }
.kv-grid > div { display: flex; gap: 10px; align-items: baseline; }
.kv-grid .k { font-size: 12px; color: var(--ink-3); min-width: 72px; }
.kv-grid .v { font-size: 14px; color: var(--ink); }

.cagr-tag, .total-tag, .src-tag { font-family: var(--mono); font-size: 12px; padding: 2px 8px; border-radius: 5px; background: var(--bg-2); color: var(--ink-2); border: 1px solid var(--line); }
.total-tag { color: var(--mint); }

.funnel { display: flex; flex-direction: column; gap: 8px; }
.funnel-row { display: flex; align-items: center; gap: 12px; }
.funnel-bar { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; border-radius: 8px; color: #06120e; font-weight: 700; }
.funnel-bar.tam { width: 100%; background: var(--mint); }
.funnel-bar.sam { width: 70%; background: var(--mint-deep); }
.funnel-bar.som { width: 45%; background: #1a9a78; color: var(--ink); }
.funnel-label { font-family: var(--mono); font-size: 12px; }
.funnel-value { font-weight: 800; }
.funnel-basis { font-size: 11px; color: var(--ink-3); flex: 1; }

.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { font-size: 12px; padding: 4px 9px; border-radius: 999px; border: 1px solid var(--line); color: var(--ink-2); }
.chip.trend { border-color: var(--mint-dim); }
.chip.driver { color: var(--mint); border-color: var(--mint-dim); }
.chip.reg { color: var(--warn); border-color: rgba(251,191,36,0.3); }
.chip.moat { background: var(--bg-2); }

.pill { font-size: 12px; padding: 2px 9px; border: 1px solid; border-radius: 999px; font-weight: 700; }

.score-bars { display: flex; flex-direction: column; gap: 9px; }
.score-bar { display: grid; grid-template-columns: 100px 1fr 36px; align-items: center; gap: 10px; }
.sb-label { font-size: 13px; color: var(--ink-2); }
.sb-track { height: 7px; background: var(--line); border-radius: 4px; overflow: hidden; }
.sb-fill { height: 100%; border-radius: 4px; transition: width .4s ease; }
.sb-val { font-family: var(--mono); font-size: 13px; font-weight: 700; text-align: right; }

.table-wrap { overflow-x: auto; }
.cmp-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.cmp-table th { text-align: left; padding: 9px 12px; color: var(--ink-3); font-weight: 600; border-bottom: 1px solid var(--line); white-space: nowrap; }
.cmp-table td { padding: 10px 12px; color: var(--ink-2); border-bottom: 1px solid var(--line); vertical-align: top; }
.cmp-table .cname { color: var(--ink); font-weight: 700; white-space: nowrap; }
.cmp-table .diff { min-width: 180px; }

.fin-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.fin-cell { background: var(--bg-2); border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; display: flex; flex-direction: column; gap: 4px; }
.fc-k { font-size: 12px; color: var(--ink-3); }
.fc-v { font-family: var(--mono); font-size: 16px; font-weight: 800; color: var(--ink); }
.fc-v.neg { color: #f87171; }
.warn-line { font-size: 13px; color: #f87171; font-weight: 600; }

.risk-list { display: flex; flex-direction: column; gap: 8px; }
.risk-card { background: var(--bg-2); border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; }
.risk-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; gap: 10px; }
.risk-type { font-weight: 700; font-size: 13px; color: var(--ink); }
.risk-meta { font-size: 12px; color: var(--ink-3); }
.risk-card p { font-size: 13px; color: var(--ink-2); line-height: 1.6; }

.exit-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.exit-card { background: var(--bg-2); border: 1px solid var(--line); border-radius: 8px; padding: 14px; display: flex; flex-direction: column; gap: 8px; }
.exit-head { display: flex; justify-content: space-between; align-items: baseline; }
.exit-type { font-weight: 700; font-size: 14px; color: var(--ink); }
.exit-score { font-family: var(--mono); font-size: 20px; font-weight: 800; }
.exit-card p { font-size: 12px; color: var(--ink-2); line-height: 1.6; }

.final-head { display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }
.final-kv { display: flex; flex-direction: column; gap: 6px; }
.final-kv > div { display: flex; gap: 10px; align-items: baseline; }
.final-kv .k { font-size: 12px; color: var(--ink-3); min-width: 92px; }
.final-kv .v { font-size: 15px; color: var(--ink); font-weight: 600; }
.conclusion { font-size: 14px; color: var(--ink); line-height: 1.8; padding: 14px; background: var(--bg); border-radius: 8px; border-left: 3px solid var(--mint); }

.ib-disclaimer { font-size: 11px; color: var(--ink-3); text-align: center; padding-top: 8px; border-top: 1px solid var(--line); }

@media (max-width: 720px) {
  .two-grid, .three-grid, .fin-grid, .exit-row { grid-template-columns: 1fr; }
  .kv-grid { grid-template-columns: 1fr; }
  .score-bar { grid-template-columns: 84px 1fr 32px; }
}
</style>
