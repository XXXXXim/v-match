import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

import HomeView from '@/views/HomeView.vue'
import GetStartedView from '@/views/GetStartedView.vue'
import SignUpView from '@/views/SignUpView.vue'
import SignInView from '@/views/SignInView.vue'
import VerifyEmailView from '@/views/VerifyEmailView.vue'
import VCProfileView from '@/views/VCProfileView.vue'
import StartupProfileView from '@/views/StartupProfileView.vue'
import RecommendView from '@/views/RecommendView.vue'
import StartupResultsView from '@/views/StartupResultsView.vue'
import VCRecommendView from '@/views/VCRecommendView.vue'
import VCDetailView from '@/views/VCDetailView.vue'
import MatchDetailView from '@/views/MatchDetailView.vue'
import MatchesView from '@/views/MatchesView.vue'
import NotificationView from '@/views/NotificationView.vue'
import BookmarkView from '@/views/BookmarkView.vue'
import MyPageView from '@/views/MyPageView.vue'
import CoffeeChatListView from '@/views/CoffeeChatListView.vue'
import CoffeeChatThreadView from '@/views/CoffeeChatThreadView.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/get-started', name: 'get-started', component: GetStartedView },
  { path: '/signup', name: 'signup', component: SignUpView },
  { path: '/login', name: 'login', component: SignInView, alias: '/signin' },
  { path: '/verify-email', name: 'verify-email', component: VerifyEmailView, meta: { requiresAuth: true } },
  { path: '/vc-profile', name: 'vc-profile', component: VCProfileView, meta: { requiresAuth: true } },
  { path: '/startup-profile', name: 'startup-profile', component: StartupProfileView, meta: { requiresAuth: true } },
  { path: '/recommend', name: 'recommend', component: RecommendView, meta: { requiresAuth: true } },
  { path: '/vc/startup-results', name: 'startup-results', component: StartupResultsView, meta: { requiresAuth: true } },
  { path: '/vc-recommend', name: 'vc-recommend', component: VCRecommendView, meta: { requiresAuth: true } },
  { path: '/vc-detail/:id', name: 'vc-detail', component: VCDetailView, meta: { requiresAuth: true } },
  { path: '/match/:kind/:id', name: 'match-detail', component: MatchDetailView, meta: { requiresAuth: true } },
  { path: '/matches', name: 'matches', component: MatchesView, meta: { requiresAuth: true } },
  { path: '/notifications', name: 'notifications', component: NotificationView, meta: { requiresAuth: true } },
  { path: '/bookmarks', name: 'bookmarks', component: BookmarkView, meta: { requiresAuth: true } },
  { path: '/mypage', name: 'mypage', component: MyPageView, meta: { requiresAuth: true } },
  { path: '/community/coffeechats', name: 'coffeechats', component: CoffeeChatListView, meta: { requiresAuth: true } },
  { path: '/community/coffeechats/:id', name: 'coffeechat-thread', component: CoffeeChatThreadView, meta: { requiresAuth: true } },
  // 없는 주소로 들어오면 빈 화면 대신 홈으로 보낸다.
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLogin) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  // 로그인했지만 이메일 미인증 → 인증 화면으로 강제 이동
  if (auth.isLogin && !auth.emailVerified && to.name !== 'verify-email') {
    return { name: 'verify-email' }
  }
})

export default router
