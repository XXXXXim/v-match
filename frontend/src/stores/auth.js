import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import axios from 'axios'
import router from '@/router'

export const useAuthStore = defineStore(
  'auth',
  () => {
    const API_URL = 'http://127.0.0.1:8000/api'
    const token = ref(null)
    const user = ref(null)
    const devCode = ref('')   // 데모용: DEBUG 시 인증코드 표시

    const isLogin = computed(() => token.value !== null)
    const emailVerified = computed(() => !!user.value?.email_verified)

    const checkUsername = async (username) => {
      const res = await axios.get(`${API_URL}/accounts/check-username/`, {
        params: { username },
      })
      return res.data   // { available, message? , error? }
    }

    const signUp = async (payload) => {
      const res = await axios.post(`${API_URL}/accounts/signup/`, payload)
      token.value = res.data.token
      user.value = res.data.user
      devCode.value = res.data.dev_code || ''
      // 이메일 인증 전 → 인증 화면으로
      router.push({ name: user.value?.email_verified ? 'home' : 'verify-email' })
    }

    const logIn = async (payload) => {
      const res = await axios.post(`${API_URL}/accounts/login/`, payload)
      token.value = res.data.token
      user.value = res.data.user
      router.push({ name: user.value?.email_verified ? 'home' : 'verify-email' })
    }

    const verifyEmail = async (code) => {
      const res = await axios.post(
        `${API_URL}/accounts/verify-email/`,
        { code },
        { headers: { Authorization: `Token ${token.value}` } },
      )
      user.value = res.data.user
      devCode.value = ''
      router.push({ name: 'home' })
    }

    const resendCode = async () => {
      const res = await axios.post(
        `${API_URL}/accounts/resend-code/`,
        {},
        { headers: { Authorization: `Token ${token.value}` } },
      )
      devCode.value = res.data.dev_code || ''
      return res.data.message
    }

    const logOut = async () => {
      // 서버 토큰 삭제(실제 세션 종료) — 실패해도 클라이언트는 정리
      try {
        if (token.value) {
          await axios.post(
            `${API_URL}/accounts/logout/`,
            {},
            { headers: { Authorization: `Token ${token.value}` } },
          )
        }
      } catch (e) {
        // best-effort: 네트워크/401이어도 무시하고 로컬 정리 진행
      }
      token.value = null
      user.value = null
      router.push({ name: 'login' })
    }

    return { token, user, devCode, isLogin, emailVerified, checkUsername, signUp, logIn, verifyEmail, resendCode, logOut }
  },
  { persist: true },
)
