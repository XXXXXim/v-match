<script setup>
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const username = ref('')
const password = ref('')
const errorMsg = ref('')

const onSubmit = async () => {
  errorMsg.value = ''
  if (!username.value || !password.value) {
    errorMsg.value = '아이디와 비밀번호를 입력해주세요.'
    return
  }
  try {
    await auth.logIn({
      username: username.value,
      password: password.value,
    })
  } catch (err) {
    if (!err.response) {
      errorMsg.value = '서버에 연결할 수 없습니다. 백엔드(python manage.py runserver)가 켜져 있는지, 8000 포트인지 확인하세요.'
    } else if (err.response.status >= 500) {
      errorMsg.value = '서버 오류(500). DB 마이그레이션을 했는지 확인하세요: python manage.py migrate'
    } else {
      errorMsg.value = err.response.data?.error || '로그인에 실패했습니다.'
    }
  }
}
</script>

<template>
  <div class="form-card">
    <h2>로그인</h2>

    <label>아이디</label>
    <input v-model="username" type="text" placeholder="아이디" @keyup.enter="onSubmit" />

    <label>비밀번호</label>
    <input v-model="password" type="password" placeholder="비밀번호" @keyup.enter="onSubmit" />

    <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

    <button class="submit-btn" @click="onSubmit">로그인</button>

    <p class="hint">
      계정이 없으신가요?
      <RouterLink :to="{ name: 'signup' }">회원가입</RouterLink>
    </p>
  </div>
</template>

<style scoped>
.form-card {
  max-width: 420px;
  margin: 0 auto;
  background: #0e1311;
  border: 1px solid #1c2320;
  border-radius: 12px;
  padding: 32px;
  display: flex;
  flex-direction: column;
}
.form-card h2 {
  margin-bottom: 20px;
  text-align: center;
}
label {
  font-size: 14px;
  font-weight: 600;
  color: #cdd4d0;
  margin-bottom: 6px;
  margin-top: 14px;
}
input {
  padding: 10px 12px;
  border: 1px solid #283029;
  border-radius: 8px;
  font-size: 15px;
}
.submit-btn {
  margin-top: 24px;
  padding: 12px;
  background: #2fe3b0;
  color: #0e1311;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 16px;
  cursor: pointer;
}
.error {
  color: #f87171;
  font-size: 14px;
  margin-top: 12px;
}
.hint {
  margin-top: 16px;
  text-align: center;
  font-size: 14px;
  color: #8a938e;
}
</style>
