<script setup>
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

const auth = useAuthStore()
const route = useRoute()
const unread = ref(0)
const accountOpen = ref(false)
let timer = null

const discoveryRoute = computed(() => auth.user?.role === 'vc' ? 'startup-results' : 'vc-recommend')
const discoveryLabel = computed(() => auth.user?.role === 'vc' ? '스타트업 찾기' : 'VC 찾기')

const refreshUnread = async () => {
  if (!auth.isLogin) { unread.value = 0; return }
  try {
    const res = await api.get('/notifications/')
    unread.value = res.data?.unread || 0
  } catch { /* 알림 실패가 탐색을 막지 않도록 한다. */ }
}
const stopPolling = () => { if (timer) { clearInterval(timer); timer = null } }
const startPolling = () => { stopPolling(); refreshUnread(); timer = setInterval(refreshUnread, 20000) }

watch(() => auth.isLogin, (value) => value ? startPolling() : (stopPolling(), (unread.value = 0)))
watch(() => route.name, () => { accountOpen.value = false; refreshUnread() })
onMounted(() => { if (auth.isLogin) startPolling(); window.addEventListener('notif-read', refreshUnread) })
onUnmounted(() => { stopPolling(); window.removeEventListener('notif-read', refreshUnread) })
</script>

<template>
  <div class="app-wrapper">
    <header v-if="!(route.name === 'home' && !auth.isLogin)" class="navbar">
      <RouterLink :to="{ name: 'home' }" class="logo" aria-label="V-Match 홈">
        <span class="logo-mark">V</span><span>Match</span>
      </RouterLink>

      <nav v-if="auth.isLogin" class="nav-links" aria-label="주요 메뉴">
        <RouterLink :to="{ name: discoveryRoute }">{{ discoveryLabel }}</RouterLink>
        <RouterLink :to="{ name: 'matches' }">매칭</RouterLink>
        <RouterLink :to="{ name: 'coffeechats' }">커피챗</RouterLink>
        <RouterLink :to="{ name: 'bookmarks' }">저장</RouterLink>
      </nav>

      <div v-if="auth.isLogin" class="nav-actions">
        <RouterLink :to="{ name: 'notifications' }" class="icon-link" aria-label="알림">
          <span aria-hidden="true">🔔</span>
          <span v-if="unread" class="noti-badge">{{ unread > 99 ? '99+' : unread }}</span>
        </RouterLink>
        <div class="account">
          <button class="account-btn" :aria-expanded="accountOpen" @click="accountOpen = !accountOpen">
            <span class="avatar">{{ auth.user?.username?.slice(0, 1)?.toUpperCase() }}</span>
            <span class="account-copy">
              <strong>{{ auth.user?.username }}</strong>
              <small>{{ auth.user?.role === 'vc' ? 'VC' : '스타트업' }}</small>
            </span>
            <span aria-hidden="true">⌄</span>
          </button>
          <div v-if="accountOpen" class="account-menu">
            <RouterLink :to="{ name: 'mypage' }">마이페이지</RouterLink>
            <button @click="auth.logOut">로그아웃</button>
          </div>
        </div>
      </div>

      <nav v-else class="guest-links" aria-label="계정 메뉴">
        <RouterLink :to="{ name: 'login' }">로그인</RouterLink>
        <RouterLink :to="{ name: 'get-started' }" class="signup-link">무료로 시작하기</RouterLink>
      </nav>
    </header>

    <main :class="['container', { 'container--landing': route.name === 'home' }]">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.navbar { height: 66px; padding: 0 32px; display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; background: rgba(8,11,10,.82); border-bottom: 1px solid var(--hair); position: sticky; top: 0; z-index: 20; backdrop-filter: blur(14px); }
.logo { display: inline-flex; align-items: center; gap: 9px; width: max-content; color: var(--ink); font-size: 20px; font-weight: 800; text-decoration: none; letter-spacing: -.3px; }
.logo-mark { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 50%; color: var(--mint); border: 1.5px solid var(--mint); box-shadow: 0 0 12px rgba(47,227,176,.35); font-size: 14px; font-weight: 800; }
.nav-links { display: flex; align-items: center; gap: 6px; }
.nav-links a { padding: 9px 14px; border-radius: 9px; color: var(--ink-2); font-weight: 600; text-decoration: none; transition: background .15s, color .15s; }
.nav-links a:hover { background: var(--fill); color: var(--ink); }
.nav-links a.router-link-active { color: var(--mint); background: var(--mint-bg); }
.nav-actions,.guest-links { justify-self: end; display: flex; align-items: center; gap: 10px; }
.guest-links a { text-decoration: none; color: var(--ink-2); font-weight: 600; padding: 9px 12px; }
.guest-links a:hover { color: var(--ink); }
.guest-links .signup-link { color: var(--on-mint); background: var(--mint); border-radius: 8px; padding-inline: 17px; font-weight: 700; }
.guest-links .signup-link:hover { background: var(--mint-br); color: var(--on-mint); }
.icon-link { position: relative; display: grid; place-items: center; width: 40px; height: 40px; border-radius: 10px; text-decoration: none; background: var(--surface-2); border: 1px solid var(--hair); }
.icon-link:hover { border-color: var(--mint-dim); }
.noti-badge { position: absolute; top: -4px; right: -5px; min-width: 18px; height: 18px; padding: 0 5px; display: grid; place-items: center; color: var(--on-mint); background: var(--mint); border: 2px solid var(--bg); border-radius: 999px; font-size: 10px; font-weight: 800; }
.account { position: relative; }
.account-btn { display: flex; align-items: center; gap: 8px; padding: 5px 8px; background: transparent; border: 0; border-radius: 11px; cursor: pointer; color: var(--ink); }
.account-btn:hover { background: var(--fill); }
.avatar { width: 34px; height: 34px; display: grid; place-items: center; border-radius: 9px; background: var(--mint-bg); color: var(--mint); font-weight: 800; border: 1px solid var(--mint-dim); }
.account-copy { display: grid; text-align: left; line-height: 1.15; }
.account-copy strong { font-size: 13px; color: var(--ink); }.account-copy small { margin-top: 3px; color: var(--ink-3); font-size: 11px; }
.account-menu { position: absolute; right: 0; top: 48px; width: 156px; padding: 7px; display: grid; background: var(--surface); border: 1px solid var(--hair); border-radius: 12px; box-shadow: var(--shadow); }
.account-menu a,.account-menu button { padding: 10px 11px; text-align: left; color: var(--ink-2); background: none; border: 0; border-radius: 8px; text-decoration: none; font-size: 14px; cursor: pointer; }
.account-menu a:hover,.account-menu button:hover { background: var(--fill); color: var(--ink); }.account-menu button { color: var(--danger); }
.container { max-width: 1120px; margin: 0 auto; padding: 36px 24px; }.container--landing { max-width: none; padding: 0; }
@media (max-width: 760px) {
  .navbar { padding: 0 16px; grid-template-columns: 1fr auto; }.nav-links { position: fixed; bottom: 0; left: 0; right: 0; z-index: 30; justify-content: space-around; padding: 8px 12px calc(8px + env(safe-area-inset-bottom)); background: rgba(10,14,12,.92); backdrop-filter: blur(14px); border-top: 1px solid var(--hair); }.nav-links a { font-size: 13px; padding: 8px; }.account-copy { display: none; }.guest-links a:first-child { display: none; }.container { padding: 24px 16px 90px; }.container--landing { padding: 0 0 70px; }
}
</style>
