<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const presetRole = ['vc', 'startup'].includes(route.query.role) ? route.query.role : 'vc'

const name = ref('')
const phone = ref('')
const username = ref('')
const password = ref('')
const passwordConfirm = ref('')
const email = ref('')
const role = ref(presetRole)

const errorMsg = ref('')
const submitting = ref(false)

// 아이디 중복확인 상태
const usernameChecked = ref(false)   // 사용 가능으로 확인된 상태인지
const checking = ref(false)
const usernameMsg = ref('')          // 중복확인 결과 메시지
const usernameOk = ref(false)        // 메시지 색상 (true=초록, false=빨강)

// 아이디를 수정하면 다시 중복확인하도록 상태 초기화
watch(username, () => {
  usernameChecked.value = false
  usernameMsg.value = ''
})

const onCheckUsername = async () => {
  usernameMsg.value = ''
  usernameOk.value = false
  usernameChecked.value = false

  const value = username.value.trim()
  if (!value) {
    usernameMsg.value = '아이디를 입력해주세요.'
    return
  }
  if (value.length < 4) {
    usernameMsg.value = '아이디는 4자 이상으로 입력해주세요.'
    return
  }
  try {
    checking.value = true
    const res = await auth.checkUsername(value)
    if (res.available) {
      usernameOk.value = true
      usernameChecked.value = true
      usernameMsg.value = res.message || '사용 가능한 아이디입니다.'
    } else {
      usernameOk.value = false
      usernameChecked.value = false
      usernameMsg.value = res.error || '이미 있는 아이디입니다.'
    }
  } catch (err) {
    if (!err.response) {
      usernameMsg.value = '서버에 연결할 수 없습니다. 백엔드가 켜져 있는지 확인하세요.'
    } else {
      usernameMsg.value = err.response.data?.error || '중복확인에 실패했습니다.'
    }
  } finally {
    checking.value = false
  }
}

const onSubmit = async () => {
  errorMsg.value = ''

  if (!name.value.trim()) {
    errorMsg.value = '이름을 입력해주세요.'
    return
  }
  if (!phone.value.trim()) {
    errorMsg.value = '연락처를 입력해주세요.'
    return
  }
  if (!username.value.trim()) {
    errorMsg.value = '아이디를 입력해주세요.'
    return
  }
  if (!usernameChecked.value) {
    errorMsg.value = '아이디 중복확인을 해주세요.'
    return
  }
  if (!password.value) {
    errorMsg.value = '비밀번호를 입력해주세요.'
    return
  }
  if (password.value.length < 8) {
    errorMsg.value = '비밀번호는 8자 이상으로 입력해주세요.'
    return
  }
  if (password.value !== passwordConfirm.value) {
    errorMsg.value = '비밀번호가 일치하지 않습니다.'
    return
  }
  if (!email.value.trim()) {
    errorMsg.value = '이메일을 입력해주세요. (가입 시 이메일 인증이 필요합니다)'
    return
  }
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.value)) {
    errorMsg.value = '올바른 이메일 형식이 아닙니다.'
    return
  }

  try {
    submitting.value = true
    await auth.signUp({
      name: name.value.trim(),
      phone: phone.value.trim(),
      username: username.value.trim(),
      password: password.value,
      password_confirm: passwordConfirm.value,
      email: email.value.trim(),
      role: role.value,
    })
  } catch (err) {
    if (!err.response) {
      errorMsg.value = '서버에 연결할 수 없습니다. 백엔드(python manage.py runserver)가 켜져 있는지, 8000 포트인지 확인하세요.'
    } else if (err.response.status >= 500) {
      errorMsg.value = '서버 오류(500). DB 마이그레이션을 했는지 확인하세요: python manage.py migrate'
    } else {
      errorMsg.value = err.response.data?.error || '회원가입에 실패했습니다.'
      // 백엔드에서도 중복으로 막혔다면 중복확인 상태 리셋
      if ((errorMsg.value || '').includes('아이디')) {
        usernameChecked.value = false
      }
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <form class="form-card" @submit.prevent="onSubmit">
    <button type="button" class="back" @click="router.push({ name: 'get-started' })">← 유형 다시 선택</button>
    <span class="role-context">{{ role === 'vc' ? 'VC 회원가입' : '스타트업 회원가입' }}</span>
    <h2>계정을 만들어볼까요?</h2>
    <p class="intro">가입 후 이메일 인증과 프로필 등록을 순서대로 안내해드려요.</p>

    <label>이름 <span class="req">*</span></label>
    <input v-model.trim="name" type="text" placeholder="이름" autocomplete="name" />

    <label>연락처 <span class="req">*</span></label>
    <input v-model.trim="phone" type="tel" placeholder="010-1234-5678" autocomplete="tel" />

    <label>아이디 <span class="req">*</span></label>
    <div class="id-row">
      <input
        v-model.trim="username"
        type="text"
        placeholder="4자 이상"
        autocomplete="username"
        class="id-input"
      />
      <button
        type="button"
        class="check-btn"
        :disabled="checking || !username"
        @click="onCheckUsername"
      >
        {{ checking ? '확인 중...' : '중복확인' }}
      </button>
    </div>
    <p v-if="usernameMsg" class="id-msg" :class="usernameOk ? 'ok' : 'bad'">{{ usernameMsg }}</p>

    <label>비밀번호 <span class="req">*</span></label>
    <input v-model="password" type="password" placeholder="8자 이상" autocomplete="new-password" />

    <label>비밀번호 확인 <span class="req">*</span></label>
    <input v-model="passwordConfirm" type="password" placeholder="비밀번호 다시 입력" autocomplete="new-password" />
    <p v-if="passwordConfirm && password !== passwordConfirm" class="id-msg bad">비밀번호가 일치하지 않습니다.</p>

    <label>이메일 <span class="req">*</span></label>
    <input v-model.trim="email" type="email" placeholder="name@company.com" autocomplete="email" />

    <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

    <button class="submit-btn" type="submit" :disabled="submitting">{{ submitting ? '가입 중...' : '가입하고 이메일 인증하기' }}</button>

    <p class="hint">
      이미 계정이 있으신가요?
      <RouterLink :to="{ name: 'login' }">로그인</RouterLink>
    </p>
  </form>
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
  margin-top: 8px;
  font-size: 26px;
}
.back { align-self: flex-start; padding: 0; color: #8a938e; background: none; border: 0; cursor: pointer; }
.role-context { align-self: flex-start; margin-top: 30px; padding: 5px 9px; color: #2fe3b0; background: #10201b; border-radius: 999px; font-size: 12px; font-weight: 800; }
.intro { margin-top: 8px; margin-bottom: 10px; color: #8a938e; font-size: 14px; }
label {
  font-size: 14px;
  font-weight: 600;
  color: #cdd4d0;
  margin-bottom: 6px;
  margin-top: 14px;
}
input, select {
  padding: 12px 13px;
  border: 1px solid #283029;
  border-radius: 8px;
  font-size: 15px;
}

/* 아이디 + 중복확인 버튼 한 줄 배치 */
.id-row { display: flex; gap: 8px; }
.id-input { flex: 1; min-width: 0; }
.check-btn {
  flex-shrink: 0;
  padding: 0 16px;
  border: 1px solid #2fe3b0;
  border-radius: 8px;
  background: #10201b;
  color: #2fe3b0;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s, opacity 0.15s;
}
.check-btn:hover:not(:disabled) { background: #163029; }
.check-btn:disabled { opacity: .5; cursor: not-allowed; }
.id-msg { margin-top: 8px; font-size: 13px; }
.id-msg.ok { color: #34d399; }
.id-msg.bad { color: #f87171; }

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
.submit-btn:disabled { opacity: .65; cursor: wait; }
.error {
  color: #f87171;
  font-size: 14px;
  margin-top: 12px;
}
.req { color: #f87171; }
.hint {
  margin-top: 16px;
  text-align: center;
  font-size: 14px;
  color: #8a938e;
}
</style>
