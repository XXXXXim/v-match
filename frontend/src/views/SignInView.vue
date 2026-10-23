<script setup>
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const username = ref('')
const password = ref('')
const errorMsg = ref('')

// 공개 데모 배포(VITE_DEMO=true)에서만 데모 계정 버튼을 보여준다.
const isDemo = import.meta.env.VITE_DEMO === 'true'
const DEMO_PASSWORD = 'demo1234'
const useDemo = (name) => {
  username.value = name
  password.value = DEMO_PASSWORD
  onSubmit()
}

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

    <div v-if="isDemo" class="demo-box">
      <p class="demo-title">데모 계정으로 바로 둘러보기</p>
      <div class="demo-btns">
        <button type="button" @click="useDemo('demo_vc')">VC로 로그인</button>
        <button type="button" @click="useDemo('demo_startup')">스타트업으로 로그인</button>
      </div>
      <p class="demo-note">두 계정이 서로 좋아요를 누르면 매칭되고 AI 실사 리포트가 열립니다. 데모 데이터는 주기적으로 초기화됩니다.</p>
    </div>

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
.demo-box {
  border: 1px solid #2f6b4f;
  background: #10201a;
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 8px;
}
.demo-title {
  font-weight: 700;
  margin: 0 0 10px;
  color: #cdd4d0;
}
.demo-btns {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.demo-btns button {
  flex: 1;
  min-width: 140px;
  padding: 9px 10px;
  border-radius: 8px;
  border: 1px solid #2f6b4f;
  background: #173326;
  color: #e6efe9;
  font-weight: 600;
  cursor: pointer;
}
.demo-btns button:hover {
  background: #1e4432;
}
.demo-note {
  font-size: 12px;
  color: #8fa198;
  margin: 10px 0 0;
}
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
