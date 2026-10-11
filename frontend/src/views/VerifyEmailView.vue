<script setup>
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const code = ref('')
const errorMsg = ref('')
const info = ref('')

const onVerify = async () => {
  errorMsg.value = ''
  if (!code.value.trim()) {
    errorMsg.value = '인증코드를 입력해주세요.'
    return
  }
  try {
    await auth.verifyEmail(code.value.trim())
  } catch (err) {
    errorMsg.value = err.response?.data?.error || '인증에 실패했습니다.'
  }
}

const onResend = async () => {
  errorMsg.value = ''
  try {
    info.value = await auth.resendCode()
  } catch {
    errorMsg.value = '재발송에 실패했습니다.'
  }
}
</script>

<template>
  <div class="form-card">
    <h2>이메일 인증</h2>
    <p class="desc">
      <strong>{{ auth.user?.email }}</strong> 으로 보낸 6자리 인증코드를 입력하세요.
    </p>

    <div v-if="auth.devCode" class="dev-banner">
      🔧 데모 인증코드: <strong>{{ auth.devCode }}</strong>
      <span>(개발 모드에서만 표시됩니다)</span>
    </div>

    <label>인증코드</label>
    <input v-model="code" type="text" inputmode="numeric" maxlength="6" placeholder="6자리 숫자" />

    <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
    <p v-if="info" class="info">{{ info }}</p>

    <button class="submit-btn" @click="onVerify">인증 완료</button>
    <button class="resend-btn" @click="onResend">코드 다시 받기</button>
  </div>
</template>

<style scoped>
.form-card {
  max-width: 420px; margin: 0 auto; background: #0e1311; border: 1px solid #1c2320;
  border-radius: 12px; padding: 32px; display: flex; flex-direction: column;
}
.form-card h2 { margin-bottom: 12px; text-align: center; }
.desc { font-size: 14px; color: #8a938e; text-align: center; margin-bottom: 16px; }
.dev-banner {
  background: #241d0c; border: 1px solid #3a2f14; color: #fbbf24; border-radius: 8px;
  padding: 10px 12px; font-size: 14px; margin-bottom: 16px; text-align: center;
}
.dev-banner span { display: block; font-size: 11px; color: #fbbf24; margin-top: 2px; }
label { font-size: 14px; font-weight: 600; color: #cdd4d0; margin-bottom: 6px; }
input {
  padding: 12px; border: 1px solid #283029; border-radius: 8px; font-size: 18px;
  letter-spacing: 4px; text-align: center;
}
.submit-btn {
  margin-top: 20px; padding: 12px; background: #2fe3b0; color: #0e1311; border: none;
  border-radius: 8px; font-weight: 600; font-size: 16px; cursor: pointer;
}
.resend-btn {
  margin-top: 10px; padding: 10px; background: none; color: #2fe3b0; border: none;
  font-size: 14px; cursor: pointer;
}
.error { color: #f87171; font-size: 14px; margin-top: 12px; }
.info { color: #34d399; font-size: 14px; margin-top: 12px; }
</style>
