<script setup>
import { onMounted, onUnmounted, nextTick, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api'

const route = useRoute()
const router = useRouter()
const id = route.params.id

const loading = ref(true)
const errorMessage = ref('')
const chat = ref(null)          // CoffeeChat 정보
const partner = ref('')
const messages = ref([])
const draft = ref('')
const sending = ref(false)
const scroller = ref(null)
let timer = null

// 일정 제안 폼 (요청 받은 쪽이 사용)
const scheduleOpen = ref(false)
const form = reactive({ reply_message: '', meeting_type: 'online', date: '', time: '', meeting_location: '' })

const fmt = (v) => new Intl.DateTimeFormat('ko-KR', {
  month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
}).format(new Date(v))

const scrollDown = () => nextTick(() => { if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight })

const load = async (initial = false) => {
  try {
    const res = await api.get(`/coffeechats/${id}/messages/`)
    chat.value = res.data.coffeechat
    partner.value = res.data.partner_name
    const before = messages.value.length
    messages.value = res.data.messages
    if (initial || messages.value.length !== before) scrollDown()
  } catch (error) {
    errorMessage.value = error.response?.data?.error || '대화를 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

const send = async () => {
  const text = draft.value.trim()
  if (!text) return
  sending.value = true
  try {
    const res = await api.post(`/coffeechats/${id}/messages/`, { text })
    messages.value.push(res.data)
    draft.value = ''
    scrollDown()
  } catch (error) {
    window.alert(error.response?.data?.error || '전송에 실패했습니다.')
  } finally {
    sending.value = false
  }
}

// action: 'propose'(받은 쪽이 일정 제안) | 'confirm' | 'reject'(보낸 쪽이 확정/거절)
const submitSchedule = async (action) => {
  try {
    const payload = { action }
    if (action === 'propose') {
      if (!form.date || !form.time) { window.alert('날짜와 시간을 선택해주세요.'); return }
      payload.reply_message = form.reply_message
      payload.meeting_type = form.meeting_type
      payload.meeting_at = `${form.date}T${form.time}`
      payload.meeting_location = form.meeting_location
    }
    await api.post(`/coffeechats/${id}/respond/`, payload)
    scheduleOpen.value = false
    await load()
  } catch (error) {
    window.alert(error.response?.data?.error || '처리에 실패했습니다.')
  }
}

// 일정 상태: meeting_at 있고 PENDING → 제안됨(확정 대기) / ACCEPTED → 확정
const isProposed = () => !!chat.value?.meeting_at && chat.value?.status === 'PENDING'
const isConfirmed = () => !!chat.value?.meeting_at && chat.value?.status === 'ACCEPTED'
const mLabel = () => {
  if (!chat.value?.meeting_at) return ''
  const t = chat.value.meeting_type === 'online' ? '온라인' : '오프라인'
  return `${t} · ${fmt(chat.value.meeting_at)}`
}

// 상태 표시: 오픈 전(잠금)=대기 / 채팅 중(PENDING)=진행 중 / 일정 확정(ACCEPTED)=수락
const statusInfo = () => {
  if (chat.value?.locked) return { text: '대기', cls: 'b-muted' }
  if (chat.value?.status === 'ACCEPTED') return { text: '수락', cls: 'b-ok' }
  return { text: '진행 중', cls: 'b-live' }
}

onMounted(async () => { await load(true); timer = setInterval(load, 4000) })
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <section class="thread">
    <button class="back" @click="router.push({ name: 'coffeechats' })">← 커피챗 목록</button>

    <div v-if="loading" class="info">불러오는 중...</div>
    <div v-else-if="errorMessage" class="error-box">{{ errorMessage }}</div>

    <div v-else class="chat-card">
      <!-- 헤더 -->
      <div class="c-head">
        <div class="c-who">
          <span class="avatar">{{ partner.charAt(0).toUpperCase() }}</span>
          <div>
            <strong class="p-name">{{ partner }}</strong>
            <span class="badge" :class="statusInfo().cls">{{ statusInfo().text }}</span>
          </div>
        </div>
        <!-- 요청 받은 쪽(receiver)만 일정 제안 버튼 -->
        <button v-if="!chat.locked && !chat.is_sender && !isConfirmed()" class="btn ok sm" @click="scheduleOpen = !scheduleOpen">
          📅 미팅 일정 잡기
        </button>
      </div>

      <!-- 확정된 미팅 -->
      <div v-if="isConfirmed()" class="meeting-banner ok">
        <span>✅</span><strong>확정 · {{ mLabel() }}</strong>
        <span v-if="chat.meeting_location" class="loc">· {{ chat.meeting_location }}</span>
      </div>

      <!-- 제안된 일정(확정 대기) -->
      <div v-else-if="isProposed()" class="meeting-banner pending">
        <div class="mb-info">
          <span>📅</span>
          <div>
            <strong>제안된 일정 · {{ mLabel() }}</strong>
            <span v-if="chat.meeting_location" class="loc">{{ chat.meeting_location }}</span>
          </div>
        </div>
        <!-- 요청 보낸 쪽(sender)만 수락/거절 -->
        <div v-if="chat.is_sender" class="mb-actions">
          <button class="btn ok sm" @click="submitSchedule('confirm')">수락</button>
          <button class="btn ghost sm" @click="submitSchedule('reject')">거절</button>
        </div>
        <span v-else class="mb-wait">상대 확정 대기 중…</span>
      </div>

      <!-- 일정 제안 폼 (요청 받은 쪽) -->
      <div v-if="scheduleOpen && !chat.is_sender" class="sched">
        <textarea v-model="form.reply_message" class="inp" rows="2" placeholder="함께 보낼 메시지 (선택)"></textarea>
        <div class="seg">
          <button type="button" class="seg-btn" :class="{ on: form.meeting_type==='online' }" @click="form.meeting_type='online'">💻 온라인</button>
          <button type="button" class="seg-btn" :class="{ on: form.meeting_type==='offline' }" @click="form.meeting_type='offline'">📍 오프라인</button>
        </div>
        <div class="grid2">
          <input type="date" v-model="form.date" class="inp" />
          <input type="time" v-model="form.time" class="inp" />
        </div>
        <input v-model="form.meeting_location" class="inp"
          :placeholder="form.meeting_type==='online' ? '화상 링크 (선택)' : '장소 (선택)'" />
        <div class="sched-actions">
          <button class="btn ok sm" @click="submitSchedule('propose')">📨 예약하기 (상대에게 제안)</button>
          <button class="btn ghost sm" @click="scheduleOpen = false">취소</button>
        </div>
      </div>

      <!-- 메시지 영역 -->
      <div ref="scroller" class="scroller">
        <div class="sys"><span>커피챗 제안</span></div>
        <div class="msg-row" :class="chat.is_sender ? 'mine' : 'theirs'">
          <div class="bubble" :class="chat.is_sender ? 'b-mine' : 'b-theirs'">{{ chat.message }}</div>
        </div>

        <div v-for="m in messages" :key="m.id" class="msg-row" :class="m.is_mine ? 'mine' : 'theirs'">
          <div class="m-wrap">
            <div class="bubble" :class="m.is_mine ? 'b-mine' : 'b-theirs'">{{ m.text }}</div>
            <small class="m-ts">{{ fmt(m.created_at) }}</small>
          </div>
        </div>

        <p v-if="!messages.length" class="hint">첫 메시지를 보내 대화를 시작하세요.</p>
      </div>

      <!-- 입력 (수락 전에는 잠금) -->
      <div v-if="chat.locked" class="locked-foot">
        🔒
        <span v-if="chat.is_sender">상대가 매칭에서 요청을 <b>수락</b>하면 채팅이 시작됩니다.</span>
        <template v-else>
          <span>먼저 매칭에서 커피챗 요청을 수락해주세요.</span>
          <button class="btn ok sm" @click="router.push({ name: 'matches' })">매칭으로 가기 →</button>
        </template>
      </div>
      <form v-else class="c-foot" @submit.prevent="send">
        <input v-model="draft" class="inp grow" placeholder="메시지를 입력하세요..." :disabled="sending" />
        <button class="btn primary" type="submit" :disabled="sending || !draft.trim()">보내기</button>
      </form>
    </div>
  </section>
</template>

<style scoped>
.thread { max-width: 760px; margin: 0 auto; }
.back { background: none; border: none; color: var(--ink-3); cursor: pointer; font-size: 13px; margin-bottom: 12px; padding: 0; }
.back:hover { color: var(--mint); }
.info { color: var(--ink-2); padding: 24px 0; }
.error-box { background: var(--danger-bg); border: 1px solid rgba(248,113,113,.3); color: var(--danger); padding: 14px 16px; border-radius: 10px; }

.chat-card { background: var(--surface); border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }

/* 헤더 */
.c-head { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; border-bottom: 1px solid var(--line); background: var(--surface-2); }
.c-who { display: flex; align-items: center; gap: 10px; }
.avatar { width: 38px; height: 38px; border-radius: 50%; display: grid; place-items: center; font-weight: 800; color: var(--on-mint); background: linear-gradient(135deg, var(--mint-br), #38bdf8); }
.p-name { color: var(--ink); font-size: 15px; }
.badge { font-size: 11px; font-weight: 700; padding: 2px 9px; border-radius: 999px; margin-left: 8px; }
.b-warn { background: var(--warn-bg); color: var(--warn); }
.b-ok { background: var(--ok-bg); color: var(--ok); }
.b-muted { background: var(--fill); color: var(--ink-3); }
.b-live { background: rgba(56,189,248,.16); color: #38bdf8; }

/* 미팅 배너 */
.meeting-banner { display: flex; align-items: center; gap: 10px; padding: 10px 16px; font-size: 13px; border-bottom: 1px solid var(--line); flex-wrap: wrap; }
.meeting-banner.ok { background: var(--ok-bg); border-bottom-color: rgba(74,222,128,.25); color: var(--ok); }
.meeting-banner.ok strong { color: var(--ok); }
.meeting-banner.pending { background: var(--warn-bg); border-bottom-color: rgba(251,191,36,.25); justify-content: space-between; }
.mb-info { display: flex; align-items: center; gap: 8px; }
.mb-info strong { color: var(--warn); display: block; }
.meeting-banner .loc { color: var(--ink-2); }
.mb-actions { display: flex; gap: 8px; }
.mb-wait { color: var(--ink-2); font-size: 12px; }

/* 일정 폼 */
.sched { padding: 14px 16px; border-bottom: 1px solid var(--line); background: var(--bg-2); display: flex; flex-direction: column; gap: 8px; }
/* color-scheme: dark → 날짜/시간 네이티브 픽커가 다크로 렌더되어 캘린더·시계 아이콘이 밝게 보임 */
.inp { width: 100%; background: var(--surface-2); border: 1px solid var(--line); color: var(--ink); border-radius: 8px; padding: 9px 11px; font-size: 14px; font-family: inherit; color-scheme: dark; }
.inp::placeholder { color: var(--ink-4); }
/* 웹킷 보조: 픽커 아이콘을 확실히 밝게 */
.inp::-webkit-calendar-picker-indicator { filter: brightness(0) invert(1); opacity: 1; cursor: pointer; }
.seg { display: flex; gap: 8px; }
.seg-btn { flex: 1; padding: 8px; border-radius: 8px; border: 1px solid var(--line); background: var(--surface-2); color: var(--ink-2); cursor: pointer; font-size: 13px; font-weight: 600; }
.seg-btn.on { border-color: var(--mint); color: var(--mint); background: var(--mint-bg); }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.sched-actions { display: flex; gap: 8px; }

/* 메시지 영역 — 사이트에 맞춘 하이브리드 다크 배경 */
.scroller {
  height: 52vh; overflow-y: auto; padding: 16px;
  background:
    radial-gradient(120% 60% at 50% 0%, rgba(47,227,176,0.06), transparent 60%),
    linear-gradient(180deg, var(--bg-2), var(--surface));
}
.sys { text-align: center; margin: 6px 0 14px; }
.sys span { font-size: 11px; color: var(--ink-3); background: var(--surface-2); border: 1px solid var(--line); padding: 3px 10px; border-radius: 999px; }
.msg-row { display: flex; margin-bottom: 10px; }
.msg-row.mine { justify-content: flex-end; }
.msg-row.theirs { justify-content: flex-start; }
.m-wrap { max-width: 76%; }
.bubble { padding: 9px 13px; border-radius: 12px; font-size: 14px; line-height: 1.5; word-break: break-word; }
.b-mine { background: var(--mint); color: var(--on-mint); border-bottom-right-radius: 4px; }
.b-theirs { background: var(--surface-2); color: var(--ink); border: 1px solid var(--line); border-bottom-left-radius: 4px; }
.m-ts { display: block; font-size: 11px; color: var(--ink-3); margin-top: 3px; }
.msg-row.mine .m-ts { text-align: right; }
.hint { text-align: center; color: var(--ink-3); font-size: 13px; margin-top: 24px; }

/* 입력 */
.c-foot { display: flex; gap: 8px; padding: 12px 14px; border-top: 1px solid var(--line); background: var(--surface-2); }
.locked-foot { display: flex; align-items: center; gap: 10px; padding: 14px 16px; border-top: 1px solid var(--line); background: var(--surface-2); color: var(--ink-2); font-size: 13px; flex-wrap: wrap; }
.locked-foot b { color: var(--ink); }
.grow { flex: 1; }
.btn { border: none; border-radius: 8px; font-weight: 600; cursor: pointer; padding: 9px 18px; font-size: 14px; }
.btn.sm { padding: 7px 14px; font-size: 13px; }
.btn.primary { background: var(--mint); color: var(--on-mint); }
.btn.primary:disabled { opacity: .5; cursor: not-allowed; }
.btn.ok { background: var(--ok); color: #06140f; }
.btn.ghost { background: var(--surface); color: var(--ink-2); border: 1px solid var(--line); }
</style>
