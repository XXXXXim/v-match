<script setup>
import { onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const goStart = () => router.push({ name: 'get-started' })
const goLogin = () => router.push({ name: 'login' })

// 스크롤하면서 섹션이 뷰포트에 들어올 때 한 번씩 부드럽게 드러나는 모션.
// 동작 최소화(prefers-reduced-motion) 환경에서는 즉시 표시한다.
let observer = null
onMounted(() => {
  const els = Array.from(document.querySelectorAll('.lp .reveal'))
  const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  if (reduce || typeof IntersectionObserver === 'undefined') {
    els.forEach((el) => el.classList.add('is-in'))
    return
  }
  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-in')
          observer.unobserve(entry.target)
        }
      })
    },
    { threshold: 0.16, rootMargin: '0px 0px -8% 0px' },
  )
  els.forEach((el) => observer.observe(el))
})
onBeforeUnmount(() => observer?.disconnect())
</script>

<template>
  <div class="lp">
    <!-- 배경 레이어: 그리드 + 민트 글로우 + 레이더 -->
    <div class="lp-grid" aria-hidden="true"></div>
    <div class="lp-glow" aria-hidden="true"></div>

    <!-- 자체 다크 헤더 -->
    <header class="lp-top">
      <a class="brand" href="#top" @click.prevent>
        <span class="brand-mark" aria-hidden="true">
          <span class="brand-core"></span>
        </span>
        <span class="brand-name">V&#8209;MATCH</span>
      </a>
      <div class="lp-top-right">
        <div class="sysline" aria-hidden="true">
          <span>SYSTEM: <em>ACTIVE</em> / L-NODE_04</span>
          <span>MATCH_ENGINE: <em>OPTIMIZED</em></span>
        </div>
        <button class="login-link" @click="goLogin">로그인 →</button>
      </div>
    </header>

    <!-- HERO -->
    <section class="hero" id="top">
      <!-- 레이더 그래픽 -->
      <svg class="radar" viewBox="0 0 600 600" aria-hidden="true" focusable="false">
        <defs>
          <radialGradient id="rg" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="rgba(47,227,176,0.16)" />
            <stop offset="55%" stop-color="rgba(47,227,176,0.04)" />
            <stop offset="100%" stop-color="transparent" />
          </radialGradient>
        </defs>
        <circle cx="300" cy="300" r="280" fill="url(#rg)" />
        <circle class="ring" cx="300" cy="300" r="278" />
        <circle class="ring" cx="300" cy="300" r="208" />
        <circle class="ring" cx="300" cy="300" r="138" />
        <circle class="ring ring--pulse" cx="300" cy="300" r="78" />
        <line class="cross" x1="300" y1="20" x2="300" y2="580" />
        <line class="cross" x1="20" y1="300" x2="580" y2="300" />
        <circle class="node" cx="300" cy="300" r="3.5" />
      </svg>

      <div class="hero-copy">
        <h1 class="headline">
          투자할 곳도, 투자받을 곳도<br />찾는 시간을 줄여드립니다
        </h1>
        <p class="sub">
          VC는 검토할 팀을, 스타트업은 맞는 투자자를 — 서로를 찾느라 드는 수고를 V&#8209;Match가 대신 좁혀드립니다.
        </p>
        <p class="desc">
          V&#8209;Match는 양쪽의 투자 단계·섹터·thesis를 학습해, 서로에게 맞는 상대만 골라
          <span class="hl">AI Fit 리포트</span>와 함께 전달합니다.
        </p>

        <button class="cta" @click="goStart">
          <span class="cta-bracket">[</span>
          회원가입하고 추천 리포트 받기
          <span class="cta-bracket">]</span>
        </button>
        <p class="cta-note">· 신용카드 없이, 회원가입만 하면 바로 추천 리포트 제공</p>
      </div>

      <!-- 떠 있는 분석 카드 -->
      <div class="floats" aria-hidden="true">
        <article class="fcard fcard--a">
          <div class="fcard-head">
            <span class="fcard-tag">MATCH ANALYTICS</span>
            <span class="fcard-meta mint">88% CONFIDENCE</span>
          </div>
          <p class="fcard-title">Series A / SaaS</p>
          <p class="fcard-line">Retained ARR: $2.4M&nbsp;·&nbsp;Fit Score: 9.4</p>
          <div class="fcard-bar mint"></div>
        </article>

        <article class="fcard fcard--b">
          <div class="fcard-head">
            <span class="fcard-tag violet">REAL-TIME FEED</span>
            <span class="fcard-meta live"><span class="live-dot"></span>LIVE</span>
          </div>
          <p class="fcard-title">Bio-Tech Early</p>
          <p class="fcard-line">Thesis Alignment: Sector A-1</p>
          <div class="fcard-bar violet"></div>
        </article>
      </div>

      <div class="hero-foot">
        <span class="mono dim">LATENCY: 14MS&nbsp;&nbsp;//&nbsp;&nbsp;DEALS_PROCESSED: 12,842</span>
        <span class="mono dim">© 2026 V-MATCH INTELLIGENCE SYSTEM</span>
      </div>
    </section>

    <!-- PROBLEM -->
    <section class="problem">
      <p class="eyebrow reveal">THE PROBLEM</p>
      <h2 class="problem-title reveal reveal--t2">양쪽 다, 맞는 상대를 찾는 게 가장 어렵습니다</h2>

      <div class="pgrid">
        <!-- 카드 1 -->
        <article class="pcard reveal">
          <span class="picon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M3 13l3-8h12l3 8" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
              <path d="M3 13h5l1.5 2.5h5L21 13v6H3v-6z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
            </svg>
          </span>
          <h3 class="pcard-title">VC — 검토할 딜은 많은데, 맞는 건 드뭅니다</h3>
          <p class="pcard-body">
            받은 IR 100건 중 단계·섹터가 맞는 건 <span class="stat">5건</span> 남짓.
            나머지를 걸러내는 데만 심사역 한 명이 주당 <span class="stat">8시간</span>을 씁니다.
          </p>
        </article>

        <!-- 카드 2 -->
        <article class="pcard reveal">
          <span class="picon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <circle cx="11" cy="11" r="6.5" stroke="currentColor" stroke-width="1.6" />
              <path d="M16 16l4.5 4.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
            </svg>
          </span>
          <h3 class="pcard-title">스타트업 — 좋은 투자자일수록 닿을 길이 없습니다</h3>
          <p class="pcard-body">
            어느 VC가 우리 단계·섹터에 맞는지 알기 어렵고, 콜드 메일은 대부분 읽히지 않습니다.
            결국 <span class="stat">아는 사람</span>을 통해야만 미팅이 잡힙니다.
          </p>
        </article>

        <!-- 카드 3 (강조) -->
        <article class="pcard pcard--accent reveal">
          <span class="pcard-flag" aria-hidden="true">CORE GAP</span>
          <span class="picon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
            </svg>
          </span>
          <h3 class="pcard-title">결국 양쪽 다 "인맥"에서 멈춥니다</h3>
          <p class="pcard-body">
            정보가 서로에게 닿지 않으니, 판단은 "누구 소개인지"로 흘러갑니다.
            비수도권·비주류의 좋은 팀과, 그들을 만났어야 할 투자자가 구조적으로 어긋납니다.
          </p>
        </article>
      </div>
    </section>

    <!-- SERVICES -->
    <section class="services">
      <p class="eyebrow reveal">THE ENGINE</p>
      <h2 class="sec-title reveal reveal--t2">인맥이 아니라, <span class="hl">데이터</span>로 서로를 찾습니다</h2>

      <div class="sgrid">
        <article class="scard reveal">
          <span class="snum mono">01</span>
          <span class="sicon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.5" />
              <circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.5" />
              <path d="M12 1.5v4M12 18.5v4M1.5 12h4M18.5 12h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
            </svg>
          </span>
          <h3 class="scard-title">양방향 매칭 엔진</h3>
          <p class="scard-body">
            양쪽의 조건을 학습해 VC에게는 맞는 팀을, 스타트업에게는 맞는 투자자를 동시에
            추천합니다. 미스매치가 줄어 서로의 검토 시간이 본질에 쓰입니다.
          </p>
          <div class="metric">
            <span class="metric-label">단계·섹터 미스매치</span>
            <span class="metric-flow"><span class="m-from">60%</span><span class="m-arrow">→</span><span class="m-to">12%</span></span>
          </div>
        </article>

        <article class="scard reveal">
          <span class="snum mono">02</span>
          <span class="sicon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M6 3h8l4 4v14H6V3z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" />
              <path d="M14 3v4h4M9 12h6M9 16h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
            </svg>
          </span>
          <h3 class="scard-title">AI Fit 적합도 리포트</h3>
          <p class="scard-body">
            점수는 규칙·임베딩 기반으로 결정론적으로 산출하고, AI는 “왜 맞는지”를 7개 섹터로
            설명합니다. 회원가입만 하면 양쪽 모두 이 리포트를 바로 받아, 첫 검토 시간이 크게 단축됩니다.
          </p>
          <div class="metric">
            <span class="metric-label">첫 스크리닝 / 건</span>
            <span class="metric-flow"><span class="m-from">30분</span><span class="m-arrow">→</span><span class="m-to">6분</span></span>
          </div>
        </article>

        <article class="scard reveal">
          <span class="snum mono">03</span>
          <span class="sicon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.5" />
              <path d="M3 12h18M12 3c2.5 2.5 3.8 5.7 3.8 9S14.5 18.5 12 21M12 3C9.5 5.5 8.2 8.7 8.2 12s1.3 6.5 3.8 9" stroke="currentColor" stroke-width="1.5" />
            </svg>
          </span>
          <h3 class="scard-title">인맥 밖의 상대까지 발굴</h3>
          <p class="scard-body">
            소개 경로가 없는 초기 팀도, 아직 알려지지 않은 투자자도 풀에 포함됩니다.
            기존 채널로는 닿기 어려웠던 상대를 구조적으로 찾아냅니다.
          </p>
          <div class="metric">
            <span class="metric-label">파일럿 중 신규 발견</span>
            <span class="metric-flow"><span class="m-to">월 4건</span></span>
          </div>
        </article>
      </div>
      <p class="data-note mono reveal">* 수치는 베타·파일럿 목표치 기준 — 실측 데이터로 갱신 예정</p>
    </section>

    <!-- TESTIMONIALS -->
    <section class="quotes">
      <p class="eyebrow reveal">FIELD NOTES&nbsp;·&nbsp;<span class="sample-tag">예시</span></p>
      <h2 class="sec-title reveal reveal--t2">심사역이 시간을 어디에 쓰는지가 바뀝니다</h2>

      <div class="qgrid">
        <figure class="qcard reveal">
          <span class="qmark" aria-hidden="true">“</span>
          <blockquote class="qbody">
            초기에 들어오던 딜의 절반은 우리 단계랑 안 맞았는데, V-Match는 처음부터 시드 단계 팀만
            추려서 보내줬어요. Fit 리포트가 점수만 던지는 게 아니라 근거를 설명해줘서, 파트너 미팅에
            그대로 올릴 수 있었습니다.
          </blockquote>
          <figcaption class="qmeta">
            <span class="qname">김 OO 심사역</span>
            <span class="qfirm mono">OO벤처스 · 시드~프리A 집중</span>
          </figcaption>
        </figure>

        <figure class="qcard reveal">
          <span class="qmark" aria-hidden="true">“</span>
          <blockquote class="qbody">
            매주 콜드 IR 거르는 데 반나절씩 썼는데, 지금은 Fit 리포트로 먼저 우선순위가 잡혀요.
            덕분에 실제 좋은 팀이랑 통화할 시간이 늘었습니다. 비수도권 팀 두 곳을 여기서 처음 만났고,
            그중 한 곳은 검토를 진행 중이에요.
          </blockquote>
          <figcaption class="qmeta">
            <span class="qname">이 OO 파트너</span>
            <span class="qfirm mono">OO액셀러레이터</span>
          </figcaption>
        </figure>
      </div>
      <p class="data-note mono reveal">* 런칭 시 실명·동의를 확보한 실제 파일럿 고객 후기로 교체 예정</p>
    </section>

    <!-- CTA -->
    <section class="cta-band">
      <div class="cta-inner reveal reveal--up">
        <p class="eyebrow center">GET MATCHED</p>
        <h2 class="cta-title">양쪽 모두에게 딱 맞는 연결</h2>
        <p class="cta-lede">
          회원가입만 하면 끝입니다. VC에게는 검토할 팀을, 스타트업에게는 맞는 투자자를
          AI Fit 리포트로 바로 추천해드려요. 비용도, 신용카드 등록도 없습니다.
        </p>
        <button class="cta cta--lg" @click="goStart">
          <span class="cta-bracket">[</span>
          회원가입하고 추천 리포트 받기
          <span class="cta-bracket">]</span>
        </button>
        <p class="cta-proof">
          <span class="proof-dot"></span>
          파일럿 파트너 모집 중 · 초기 합류 시 매칭 우선권
        </p>
      </div>

      <footer class="lp-footer">
        <span class="brand-name sm">V&#8209;MATCH</span>
        <span class="mono dim">© 2026 V-MATCH INTELLIGENCE SYSTEM</span>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.lp {
  --bg:        #070908;
  --panel:     rgba(16, 21, 19, 0.62);
  --panel-2:   #0c100e;
  --mint:      #2fe3b0;
  --mint-br:   #5cf2c8;
  --mint-dim:  rgba(47, 227, 176, 0.42);
  --violet:    #9d74ef;
  --ink:       #f3f6f4;
  --ink-2:     #aab3ae;
  --ink-3:     #717b76;
  --hair:      rgba(255, 255, 255, 0.08);
  --hair-2:    rgba(255, 255, 255, 0.045);

  position: relative;
  min-height: 100vh;
  background: var(--bg);
  color: var(--ink);
  font-family: 'Pretendard', system-ui, -apple-system, 'Segoe UI', sans-serif;
  overflow: hidden;
  isolation: isolate;
}
.mono { font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace; }

/* ---------- 배경 레이어 ---------- */
.lp-grid {
  position: absolute; inset: 0; z-index: -2; pointer-events: none;
  background-image:
    linear-gradient(var(--hair-2) 1px, transparent 1px),
    linear-gradient(90deg, var(--hair-2) 1px, transparent 1px);
  background-size: 66px 66px;
  -webkit-mask-image: radial-gradient(120% 90% at 50% 30%, #000 0%, rgba(0,0,0,0.35) 55%, transparent 100%);
  mask-image: radial-gradient(120% 90% at 50% 30%, #000 0%, rgba(0,0,0,0.35) 55%, transparent 100%);
}
.lp-glow {
  position: absolute; inset: 0; z-index: -3; pointer-events: none;
  background:
    radial-gradient(680px 520px at 60% 18%, rgba(47,227,176,0.10), transparent 60%),
    radial-gradient(520px 420px at 88% 70%, rgba(157,116,239,0.06), transparent 60%);
}

/* ---------- 헤더 ---------- */
.lp-top {
  position: relative; z-index: 2;
  display: flex; align-items: flex-start; justify-content: space-between;
  padding: 30px max(28px, calc((100% - 1200px) / 2)) 0;
}
.brand { display: inline-flex; align-items: center; gap: 11px; text-decoration: none; }
.brand-mark {
  width: 26px; height: 26px; border-radius: 50%;
  border: 1.5px solid var(--mint); display: grid; place-items: center;
  box-shadow: 0 0 14px rgba(47,227,176,0.35);
}
.brand-core { width: 8px; height: 8px; border-radius: 50%; background: var(--mint); box-shadow: 0 0 8px var(--mint); }
.brand-name { color: var(--ink); font-size: 19px; font-weight: 800; letter-spacing: 1px; }

.lp-top-right { display: flex; flex-direction: column; align-items: flex-end; gap: 12px; }
.sysline {
  display: grid; gap: 3px; text-align: right;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 11px; letter-spacing: 1px; color: var(--ink-3);
}
.sysline em { color: var(--mint); font-style: normal; }
.login-link {
  background: rgba(47,227,176,0.07); border: 1px solid var(--mint-dim); border-radius: 7px;
  cursor: pointer;
  color: var(--mint-br); font-size: 15px; font-weight: 700; font-family: inherit;
  padding: 9px 18px; transition: color 0.15s, background 0.15s, border-color 0.15s;
}
.login-link:hover { color: #fff; background: rgba(47,227,176,0.16); border-color: var(--mint); }

/* ---------- HERO ---------- */
.hero {
  position: relative; z-index: 1;
  padding: 64px max(28px, calc((100% - 1200px) / 2)) 26px;
  min-height: 78vh;
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr);
  align-items: center;
  column-gap: 40px;
}
.radar {
  position: absolute; z-index: -1; pointer-events: none;
  width: 760px; height: 760px;
  top: 46%; left: 52%; transform: translate(-50%, -50%);
  opacity: 0.85;
}
.radar .ring { fill: none; stroke: rgba(255,255,255,0.07); stroke-width: 1; }
.radar .cross { stroke: rgba(255,255,255,0.045); stroke-width: 1; }
.radar .node { fill: var(--mint); filter: drop-shadow(0 0 6px var(--mint)); }
.radar .ring--pulse { stroke: var(--mint-dim); transform-origin: 300px 300px; animation: radarPulse 4.8s ease-out infinite; }
@keyframes radarPulse {
  0%   { transform: scale(0.55); opacity: 0.9; }
  70%  { transform: scale(1.9);  opacity: 0; }
  100% { transform: scale(1.9);  opacity: 0; }
}

.hero-copy { max-width: 680px; animation: rise 0.7s ease both; }
.headline {
  color: #fff; font-weight: 800; letter-spacing: -1px; line-height: 1.22;
  font-size: clamp(32px, 4.2vw, 48px);
  word-break: keep-all;
  text-wrap: balance;
}
.sub { margin-top: 26px; color: var(--ink); font-size: clamp(17px, 1.5vw, 20px); font-weight: 500; line-height: 1.55; }
.desc { margin-top: 18px; color: var(--ink-2); font-size: clamp(15px, 1.2vw, 17px); line-height: 1.75; }
.desc .hl { color: var(--mint-br); font-weight: 600; }
.sec-title .hl { color: var(--mint); }

.cta {
  margin-top: 38px;
  display: inline-flex; align-items: center; gap: 10px;
  padding: 16px 30px; cursor: pointer;
  background: rgba(47,227,176,0.07);
  color: var(--mint-br); font-family: inherit; font-size: 17px; font-weight: 700;
  border: 1px solid var(--mint-dim); border-radius: 4px;
  box-shadow: 0 0 0 0 rgba(47,227,176,0.35);
  transition: background 0.18s, box-shadow 0.22s, transform 0.18s, border-color 0.18s;
}
.cta-bracket { color: var(--mint); opacity: 0.7; font-weight: 500; }
.cta:hover {
  background: rgba(47,227,176,0.14); border-color: var(--mint);
  box-shadow: 0 0 28px rgba(47,227,176,0.22); transform: translateY(-1px);
}
.cta-note { margin-top: 16px; color: var(--ink-3); font-size: 13px; letter-spacing: 0.3px; }

/* ---------- 떠 있는 카드 ---------- */
.floats { position: relative; height: 100%; min-height: 420px; }
.fcard {
  position: absolute; width: 300px;
  padding: 20px 22px;
  background: var(--panel); backdrop-filter: blur(10px);
  border: 1px solid var(--hair); border-radius: 10px;
  box-shadow: 0 24px 60px rgba(0,0,0,0.5);
}
.fcard--a { top: 26px; right: 0; animation: float 7s ease-in-out infinite; }
.fcard--b { bottom: 18px; right: 36px; animation: float 7s ease-in-out infinite 1.6s; }
.fcard-head { display: flex; align-items: center; justify-content: space-between; }
.fcard-tag {
  font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 1.2px;
  color: var(--mint);
}
.fcard-tag.violet { color: var(--violet); }
.fcard-meta { font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 0.8px; color: var(--ink-2); }
.fcard-meta.mint { color: var(--mint); }
.fcard-meta.live { display: inline-flex; align-items: center; gap: 6px; color: var(--ink); }
.live-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--violet); box-shadow: 0 0 8px var(--violet); animation: blink 1.4s ease-in-out infinite; }
.fcard-title { margin-top: 14px; color: #fff; font-size: 22px; font-weight: 800; letter-spacing: -0.4px; }
.fcard-line { margin-top: 7px; color: var(--ink-3); font-size: 13px; }
.fcard-bar { margin-top: 16px; height: 2px; border-radius: 2px; }
.fcard-bar.mint { background: linear-gradient(90deg, var(--mint), transparent); }
.fcard-bar.violet { background: linear-gradient(90deg, var(--violet), transparent); }

.hero-foot {
  grid-column: 1 / -1;
  margin-top: 30px; padding-top: 18px; border-top: 1px solid var(--hair-2);
  display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap;
}
.mono.dim { font-size: 11px; letter-spacing: 1px; color: var(--ink-3); }

/* ---------- PROBLEM ---------- */
.problem {
  position: relative; z-index: 1;
  padding: 92px max(28px, calc((100% - 1200px) / 2)) 110px;
}
.eyebrow {
  font-family: 'JetBrains Mono', monospace; font-size: 12px; letter-spacing: 3px;
  color: var(--mint); text-transform: uppercase;
}
.problem-title {
  margin-top: 18px; color: #fff; font-weight: 800; letter-spacing: -1px;
  font-size: clamp(28px, 3.4vw, 46px); line-height: 1.2;
}
.pgrid {
  margin-top: 56px; display: grid; gap: 22px;
  grid-template-columns: repeat(3, 1fr);
}
.pcard {
  position: relative;
  padding: 32px 28px 34px;
  background: var(--panel-2); border: 1px solid var(--hair); border-radius: 14px;
  transition: border-color 0.2s, transform 0.2s, box-shadow 0.2s;
}
.pcard:hover { transform: translateY(-3px); border-color: rgba(255,255,255,0.16); }
.pcard--accent {
  border-color: var(--mint-dim);
  box-shadow: inset 0 0 0 1px rgba(47,227,176,0.12), 0 0 40px rgba(47,227,176,0.07);
  background:
    linear-gradient(180deg, rgba(47,227,176,0.05), transparent 40%),
    var(--panel-2);
}
.pcard--accent:hover { border-color: var(--mint); box-shadow: inset 0 0 0 1px rgba(47,227,176,0.2), 0 0 52px rgba(47,227,176,0.12); }
.pcard-flag {
  position: absolute; top: 18px; right: 20px;
  font-family: 'JetBrains Mono', monospace; font-size: 10px; letter-spacing: 1.5px;
  color: var(--mint); padding: 3px 8px; border: 1px solid var(--mint-dim); border-radius: 4px;
}
.picon { display: inline-grid; place-items: center; width: 42px; height: 42px; color: var(--mint); }
.picon svg { width: 30px; height: 30px; }
.pcard--accent .picon { color: var(--mint-br); }
.pcard-title { margin-top: 22px; color: #fff; font-size: 20px; font-weight: 700; line-height: 1.4; letter-spacing: -0.3px; }
.pcard-body { margin-top: 16px; color: var(--ink-2); font-size: 15px; line-height: 1.78; }
.stat {
  display: inline-block; margin: 0 1px; padding: 1px 9px;
  color: var(--mint-br); font-weight: 700; font-variant-numeric: tabular-nums;
  border: 1px solid var(--mint-dim); border-radius: 5px;
  background: rgba(47,227,176,0.06);
}

/* 공통 섹션 타이틀 */
.sec-title {
  margin-top: 18px; color: #fff; font-weight: 800; letter-spacing: -1px;
  font-size: clamp(28px, 3.4vw, 46px); line-height: 1.2;
}
.data-note { margin-top: 28px; font-size: 11px; letter-spacing: 0.4px; color: var(--ink-4); }

/* ---------- SERVICES ---------- */
.services {
  position: relative; z-index: 1;
  padding: 30px max(28px, calc((100% - 1200px) / 2)) 100px;
  border-top: 1px solid var(--hair-2);
}
.sgrid { margin-top: 56px; display: grid; gap: 22px; grid-template-columns: repeat(3, 1fr); }
.scard {
  position: relative; padding: 34px 30px 30px;
  background: var(--panel-2); border: 1px solid var(--hair); border-radius: 14px;
  transition: border-color 0.2s, transform 0.2s;
}
.scard:hover { transform: translateY(-3px); border-color: var(--mint-dim); }
.snum {
  position: absolute; top: 26px; right: 28px;
  font-size: 13px; letter-spacing: 1px; color: var(--ink-4);
}
.sicon { display: inline-grid; place-items: center; width: 46px; height: 46px; color: var(--mint); border: 1px solid var(--mint-dim); border-radius: 11px; background: rgba(47,227,176,0.05); }
.sicon svg { width: 26px; height: 26px; }
.scard-title { margin-top: 22px; color: #fff; font-size: 21px; font-weight: 700; letter-spacing: -0.3px; }
.scard-body { margin-top: 14px; color: var(--ink-2); font-size: 15px; line-height: 1.75; }
.metric {
  margin-top: 24px; padding-top: 18px; border-top: 1px dashed var(--hair);
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
}
.metric-label { color: var(--ink-3); font-size: 13px; }
.metric-flow { display: inline-flex; align-items: center; gap: 9px; font-family: 'JetBrains Mono', monospace; }
.m-from { color: var(--ink-4); font-size: 15px; text-decoration: line-through; text-decoration-color: var(--ink-4); }
.m-arrow { color: var(--mint); font-size: 14px; }
.m-to { color: var(--mint-br); font-size: 18px; font-weight: 600; }

/* ---------- TESTIMONIALS ---------- */
.quotes {
  position: relative; z-index: 1;
  padding: 88px max(28px, calc((100% - 1200px) / 2)) 100px;
  border-top: 1px solid var(--hair-2);
}
.sample-tag {
  color: var(--violet); border: 1px solid rgba(157,116,239,0.4); border-radius: 4px;
  padding: 1px 7px; font-size: 10px; letter-spacing: 1px;
}
.qgrid { margin-top: 52px; display: grid; gap: 22px; grid-template-columns: repeat(2, 1fr); }
.qcard {
  position: relative; padding: 36px 34px 30px;
  background: var(--panel-2); border: 1px solid var(--hair); border-radius: 16px;
}
.qmark { position: absolute; top: 14px; left: 26px; color: var(--mint-dim); font-size: 60px; font-weight: 800; line-height: 1; font-family: Georgia, serif; }
.qbody { position: relative; margin-top: 22px; color: var(--ink); font-size: 16px; line-height: 1.8; font-weight: 400; }
.qmeta { margin-top: 26px; padding-top: 18px; border-top: 1px solid var(--hair); display: grid; gap: 5px; }
.qname { color: #fff; font-size: 15px; font-weight: 700; }
.qfirm { color: var(--ink-3); font-size: 12px; letter-spacing: 0.4px; }

/* ---------- CTA ---------- */
.cta-band {
  position: relative; z-index: 1;
  padding: 0 max(28px, calc((100% - 1200px) / 2));
  border-top: 1px solid var(--hair-2);
}
.cta-inner {
  position: relative; overflow: hidden;
  margin: 80px 0 0; padding: 72px 40px 76px; text-align: center;
  border: 1px solid var(--mint-dim); border-radius: 20px;
  background:
    radial-gradient(620px 320px at 50% 0%, rgba(47,227,176,0.12), transparent 70%),
    var(--panel-2);
}
.eyebrow.center { display: block; }
.cta-title { margin-top: 16px; color: #fff; font-weight: 800; letter-spacing: -1px; font-size: clamp(28px, 3.6vw, 48px); line-height: 1.18; }
.cta-lede { max-width: 560px; margin: 20px auto 0; color: var(--ink-2); font-size: 16px; line-height: 1.75; }
.cta--lg { margin-top: 36px; padding: 18px 36px; font-size: 18px; }
.cta-proof { margin-top: 22px; display: inline-flex; align-items: center; gap: 9px; color: var(--ink-3); font-size: 13px; letter-spacing: 0.3px; }
.proof-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--mint); box-shadow: 0 0 10px var(--mint); }
.lp-footer {
  margin-top: 70px; padding: 28px 0 60px;
  display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap;
  border-top: 1px solid var(--hair-2);
}
.brand-name.sm { font-size: 15px; letter-spacing: 1px; color: var(--ink-2); }

/* ---------- 모션 ---------- */
@keyframes rise { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: none; } }
@keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-9px); } }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }

/* ---------- 스크롤 리빌 ---------- */
/* translate(독립 속성)로 드러내, 카드의 hover transform 과 충돌하지 않게 한다.
   기본: 옆에서(오른쪽→) 슬라이드인 — 페이지를 옆으로 넘기는 느낌.
   .reveal--up: 마지막 CTA 섹션만 아래→위로 등장. */
.reveal {
  opacity: 0;
  translate: 56px 0;
  transition: opacity 0.6s ease, translate 0.72s cubic-bezier(0.22, 0.61, 0.36, 1);
  will-change: opacity, translate;
}
.reveal--up { translate: 0 40px; }
.reveal.is-in { opacity: 1; translate: 0 0; }
.reveal--t2 { transition-delay: 0.06s; }
/* 그리드 카드: 왼→오 순으로 가볍게 스태거 */
.pgrid .reveal:nth-child(2) { transition-delay: 0.09s; }
.pgrid .reveal:nth-child(3) { transition-delay: 0.18s; }
.sgrid .reveal:nth-child(2) { transition-delay: 0.09s; }
.sgrid .reveal:nth-child(3) { transition-delay: 0.18s; }
.qgrid .reveal:nth-child(2) { transition-delay: 0.09s; }

/* ---------- 포커스 접근성 ---------- */
.cta:focus-visible, .login-link:focus-visible {
  outline: 2px solid var(--mint); outline-offset: 3px; border-radius: 4px;
}

/* ---------- 반응형 ---------- */
@media (max-width: 980px) {
  .hero {
    grid-template-columns: 1fr; row-gap: 8px; min-height: auto;
    padding-top: 40px; padding-bottom: 20px;
  }
  .radar { width: 540px; height: 540px; top: 38%; opacity: 0.5; }
  .floats { min-height: 0; height: auto; display: grid; gap: 18px; margin-top: 40px; }
  .fcard { position: static; width: 100%; max-width: 360px; animation: none; }
  .hero-foot { margin-top: 26px; }
  .pgrid, .sgrid, .qgrid { grid-template-columns: 1fr; gap: 16px; }
  .cta-inner { padding: 52px 24px 56px; }
}
@media (max-width: 560px) {
  .lp-top { flex-direction: column; gap: 18px; align-items: flex-start; padding-top: 22px; }
  .lp-top-right { align-items: flex-start; }
  .sysline { text-align: left; }
  .hero { padding-left: 20px; padding-right: 20px; }
  .problem, .services, .quotes, .cta-band { padding-left: 20px; padding-right: 20px; }
  .hero-foot { flex-direction: column; gap: 8px; }
  .cta { width: 100%; justify-content: center; }
}

/* ---------- 모션 최소화 선호 ---------- */
@media (prefers-reduced-motion: reduce) {
  .hero-copy, .fcard--a, .fcard--b, .radar .ring--pulse, .live-dot { animation: none !important; }
  .reveal { opacity: 1 !important; translate: none !important; transition: none !important; }
}
</style>
