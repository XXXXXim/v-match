import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api',
})

// 모든 요청에 토큰 자동 첨부
api.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Token ${auth.token}`
  }
  return config
})

// 토큰이 만료/무효(401)면 자동 로그아웃 → 로그인 화면으로.
// 이메일 미인증(403)이면 인증 화면으로 유도.
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status
    if (status === 401) {
      const auth = useAuthStore()
      if (auth.isLogin) {
        auth.logOut()
        window.alert('로그인이 만료되었습니다. 다시 로그인해주세요.')
      }
    } else if (status === 403 && err.response?.data?.detail?.includes('이메일 인증')) {
      // 백엔드의 이메일 인증 게이트에 막힌 경우에만 인증 화면으로 이동.
      router.push({ name: 'verify-email' }).catch(() => {})
    }
    return Promise.reject(err)
  },
)

export default api
