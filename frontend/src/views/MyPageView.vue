<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const isVC = computed(() => auth.user?.role === 'vc')

const nav = computed(() => {
  const items = [
    { key: 'account', label: 'ACCOUNT', tag: 'YOU', to: null },
    { key: 'profile', label: isVC.value ? 'INVESTMENT THESIS' : 'COMPANY PROFILE', tag: 'EDIT', to: isVC.value ? 'vc-profile' : 'startup-profile' },
  ]
  if (isVC.value) {
    items.push({ key: 'discovery', label: 'DEAL FLOW', tag: 'LIVE', to: 'startup-results' })
    items.push({ key: 'saved', label: 'BOOKMARKS', tag: '★', to: 'bookmarks' })
  } else {
    items.push({ key: 'discovery', label: 'VC DISCOVERY', tag: 'LIVE', to: 'vc-recommend' })
  }
  return items
})

const go = (name) => name && router.push({ name })
</script>

<template>
  <div class="cfg">
    <div class="cfg-top">
      <div class="brand"><span class="dot"></span> V-MATCH</div>
      <div class="access">
        ACCESS_LEVEL: {{ isVC ? 'PARTNER' : 'FOUNDER' }} / P-NODE_01<br />
        SESSION: {{ auth.user?.username || '—' }}
      </div>
    </div>

    <div class="layout">
      <!-- 사이드바 -->
      <aside class="side">
        <button class="side-item active"><span>FIRM SETTINGS</span><span class="arrow">→</span></button>
        <button v-for="it in nav.slice(1)" :key="it.key" class="side-item" @click="go(it.to)">
          <span>{{ it.label }}</span><span class="side-tag">{{ it.tag }}</span>
        </button>
      </aside>

      <!-- 메인 -->
      <main class="main">
        <h1 class="m-title">System Configuration</h1>
        <p class="m-sub">계정 정보와 프로필·탐색 설정을 관리합니다.</p>

        <!-- 계정 -->
        <section class="sect">
          <div class="sect-label">ACCOUNT IDENTITY</div>
          <div class="acct">
            <div class="acct-row"><span class="ak">아이디</span><span class="av">{{ auth.user?.username }}</span></div>
            <div class="acct-row"><span class="ak">이메일</span><span class="av">{{ auth.user?.email || '-' }}</span></div>
            <div class="acct-row"><span class="ak">역할</span><span class="role-badge">{{ isVC ? 'VC · 투자자' : 'STARTUP · 창업자' }}</span></div>
          </div>
        </section>

        <!-- 바로가기 -->
        <section class="sect">
          <div class="sect-label">QUICK ACTIONS</div>
          <p class="sect-desc">자주 쓰는 작업으로 바로 이동합니다.</p>
          <div class="links">
            <button class="link-card" @click="go(isVC ? 'vc-profile' : 'startup-profile')">
              <h3>{{ isVC ? '투자 조건 관리' : '회사 프로필 관리' }}</h3>
              <p>{{ isVC ? '선호 산업·지역·투자금 범위를 등록·수정합니다.' : '회사 정보와 IR 자료를 등록·수정합니다.' }}</p>
              <span class="lc-go">설정 →</span>
            </button>

            <button v-if="isVC" class="link-card" @click="go('startup-results')">
              <h3>딜 플로우 보기</h3>
              <p>투자 논리에 맞는 스타트업을 추천받습니다.</p>
              <span class="lc-go">탐색 →</span>
            </button>
            <button v-else class="link-card" @click="go('vc-recommend')">
              <h3>VC 추천 보기</h3>
              <p>우리 회사에 맞는 VC를 추천받습니다.</p>
              <span class="lc-go">탐색 →</span>
            </button>

            <button v-if="isVC" class="link-card" @click="go('bookmarks')">
              <h3>관심 스타트업</h3>
              <p>북마크한 스타트업을 확인합니다.</p>
              <span class="lc-go">열기 →</span>
            </button>

            <button class="link-card danger" @click="auth.logOut">
              <h3>로그아웃</h3>
              <p>현재 세션을 종료합니다.</p>
              <span class="lc-go">종료 →</span>
            </button>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<style scoped>
.cfg { max-width: 1080px; margin: 0 auto; }
.cfg-top { display: flex; justify-content: space-between; align-items: flex-start; padding-bottom: 18px; margin-bottom: 22px; }
.brand { display: flex; align-items: center; gap: 8px; font-family: var(--mono); font-weight: 700; letter-spacing: .1em; font-size: 14px; }
.brand .dot { width: 14px; height: 14px; border-radius: 50%; border: 2px solid var(--mint); box-shadow: 0 0 10px var(--mint-dim); }
.access { font-family: var(--mono); font-size: 10px; line-height: 1.7; letter-spacing: .06em; color: var(--ink-4); text-align: right; }

.layout { display: grid; grid-template-columns: 240px 1fr; gap: 20px; align-items: start; }

.side { display: flex; flex-direction: column; gap: 2px; }
.side-item { display: flex; justify-content: space-between; align-items: center; padding: 13px 14px; border: 1px solid transparent; border-radius: 10px; background: none; color: var(--ink-2); font-family: var(--mono); font-size: 12px; letter-spacing: .04em; cursor: pointer; text-align: left; transition: background .12s; }
.side-item:hover { background: var(--fill); color: var(--ink); }
.side-item.active { background: var(--mint-bg); border-color: var(--mint-dim); color: var(--mint); }
.arrow { color: var(--mint); }
.side-tag { font-size: 10px; color: var(--ink-4); }
.side-item.active .side-tag { color: var(--mint); }

.main { background: var(--surface); border: 1px solid var(--hair); border-radius: 14px; padding: 30px; }
.m-title { font-size: 26px; font-weight: 800; letter-spacing: -.01em; }
.m-sub { margin-top: 6px; color: var(--ink-2); font-size: 14px; padding-bottom: 22px; border-bottom: 1px solid var(--hair); }

.sect { margin-top: 26px; }
.sect-label { font-family: var(--mono); font-size: 11px; letter-spacing: .12em; color: var(--mint); margin-bottom: 14px; }
.sect-desc { margin-top: -8px; margin-bottom: 14px; color: var(--ink-3); font-size: 13px; }

.acct { border: 1px solid var(--hair); border-radius: 12px; overflow: hidden; }
.acct-row { display: flex; justify-content: space-between; align-items: center; padding: 15px 18px; border-bottom: 1px solid var(--hair-2); }
.acct-row:last-child { border-bottom: none; }
.ak { color: var(--ink-3); font-size: 13px; }
.av { font-size: 14px; font-weight: 600; color: var(--ink); }
.role-badge { font-family: var(--mono); background: var(--mint-bg); color: var(--mint); padding: 4px 12px; border-radius: 999px; font-size: 11px; letter-spacing: .06em; border: 1px solid var(--mint-dim); }

.links { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
.link-card { text-align: left; background: var(--surface-2); border: 1px solid var(--hair); border-radius: 12px; padding: 18px; cursor: pointer; transition: border-color .15s, transform .15s; }
.link-card:hover { border-color: var(--mint-dim); transform: translateY(-2px); }
.link-card h3 { font-size: 15px; font-weight: 700; color: var(--ink); }
.link-card p { margin-top: 6px; color: var(--ink-3); font-size: 13px; line-height: 1.5; }
.lc-go { display: inline-block; margin-top: 12px; font-family: var(--mono); font-size: 11px; color: var(--mint); letter-spacing: .06em; }
.link-card.danger:hover { border-color: var(--danger); }
.link-card.danger .lc-go { color: var(--danger); }

@media (max-width: 760px) {
  .layout { grid-template-columns: 1fr; }
  .side { flex-direction: row; flex-wrap: wrap; }
  .side-item { flex: 1; min-width: 130px; }
  .main { padding: 22px; }
}
</style>
