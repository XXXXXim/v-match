<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'

const router = useRouter()
const coffeechats = ref([])
const loading = ref(true)
const errorMessage = ref('')
let timer = null

const goThread = (item) => router.push({ name: 'coffeechat-thread', params: { id: item.id } })
const goMatches = () => router.push({ name: 'matches' })

const sentCount = computed(() => coffeechats.value.filter((item) => item.is_sender).length)
const receivedCount = computed(() => coffeechats.value.length - sentCount.value)

// 상태 → 다크테마 배지 클래스
// 오픈 전(잠금)=대기 / 채팅 중(PENDING)=진행 중 / 일정 확정(ACCEPTED)=수락
const badgeInfo = (item) => {
  if (item.locked) return { text: '대기', cls: 'b-muted' }
  if (item.status === 'ACCEPTED') return { text: '수락', cls: 'b-ok' }
  return { text: '진행 중', cls: 'b-live' }
}

const formatDate = (value) => new Intl.DateTimeFormat('ko-KR', {
  month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
}).format(new Date(value))

const loadCoffeeChats = async (initial = false) => {
  if (initial) loading.value = true
  errorMessage.value = ''
  try {
    const response = await api.get('/coffeechats/my-requests/')
    coffeechats.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    if (initial) errorMessage.value = error.response?.data?.error || '커피챗 목록을 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

const meetingLabel = (item) => {
  if (item.status !== 'ACCEPTED' || !item.meeting_at) return ''
  const t = item.meeting_type === 'online' ? '온라인' : '오프라인'
  return `${t} · ${formatDate(item.meeting_at)}`
}

// 상대 이름/역할
const partnerName = (item) => (item.is_sender ? item.receiver_name : item.sender_name)
const partnerRole = (item) => (item.is_sender ? item.receiver_role : item.sender_role)

onMounted(async () => {
  await loadCoffeeChats(true)
  // 미리보기 실시간 갱신(가벼운 폴링)
  timer = setInterval(() => loadCoffeeChats(false), 5000)
})
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<template>
  <section class="cc-list">
    <div class="head">
      <div>
        <span class="eyebrow">1:1 NETWORKING</span>
        <h1 class="title">커피챗</h1>
        <p class="sub">매칭된 파트너와 주고받은 제안을 확인하세요.</p>
      </div>
      <div v-if="!loading" class="counts">
        <span class="pill">보낸 제안 {{ sentCount }}</span>
        <span class="pill">받은 제안 {{ receivedCount }}</span>
      </div>
    </div>

    <div v-if="loading" class="info">불러오는 중...</div>

    <div v-else-if="errorMessage" class="error-box">
      <span>{{ errorMessage }}</span>
      <button class="btn ghost sm" @click="loadCoffeeChats(true)">다시 시도</button>
    </div>

    <div v-else-if="!coffeechats.length" class="empty">
      <div class="emoji">☕</div>
      <h2>아직 커피챗 제안이 없어요</h2>
      <p>매칭 상세에서 대화를 시작해보세요.</p>
    </div>

    <div v-else class="cards">
      <article v-for="item in coffeechats" :key="item.id" class="card">
        <div class="row1">
          <div class="who">
            <span class="dir" :class="item.is_sender ? 'd-sent' : 'd-recv'">
              {{ item.is_sender ? '보낸 제안' : '받은 제안' }}
            </span>
            <strong class="name">{{ partnerName(item) }}</strong>
            <span class="role">{{ partnerRole(item) }}</span>
          </div>
          <span class="badge" :class="badgeInfo(item).cls">{{ badgeInfo(item).text }}</span>
        </div>

        <!-- 최신 메시지 미리보기(실시간) -->
        <p class="preview">{{ item.preview }}</p>
        <time class="ts">{{ formatDate(item.created_at) }}</time>

        <!-- 확정 미팅 일정 -->
        <div v-if="meetingLabel(item)" class="meeting">
          <span>📅</span>
          <div>
            <strong>{{ meetingLabel(item) }}</strong>
            <span v-if="item.meeting_location" class="loc">{{ item.meeting_location }}</span>
          </div>
        </div>

        <div class="actions">
          <!-- 매칭 수락 전: 채팅 불가 -->
          <template v-if="item.locked">
            <button v-if="!item.is_sender" class="btn primary sm" @click="goMatches">✋ 매칭에서 수락하기</button>
            <span v-else class="wait">⏳ 상대 수락 대기 중</span>
          </template>
          <!-- 수락 후: 상대가 마지막으로 말했으면 '답장하기', 아니면 '채팅 열기' -->
          <template v-else>
            <button v-if="!item.last_from_me" class="btn primary sm" @click="goThread(item)">↩️ 답장하기</button>
            <button v-else class="btn ghost sm" @click="goThread(item)">💬 채팅 열기</button>
          </template>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.cc-list { max-width: 860px; margin: 0 auto; }
.head { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; margin-bottom: 22px; flex-wrap: wrap; }
.eyebrow { font-family: var(--mono); font-size: 12px; font-weight: 700; letter-spacing: .12em; color: var(--mint); }
.title { font-size: 26px; font-weight: 800; margin-top: 6px; color: var(--ink); }
.sub { color: var(--ink-2); font-size: 14px; margin-top: 4px; }
.counts { display: flex; gap: 8px; }
.pill { background: var(--surface-2); border: 1px solid var(--line); color: var(--ink-2); font-size: 13px; padding: 6px 14px; border-radius: 999px; }
.info { color: var(--ink-2); padding: 30px 0; }
.error-box { display: flex; justify-content: space-between; align-items: center; gap: 12px; background: var(--danger-bg); border: 1px solid rgba(248,113,113,.3); color: var(--danger); padding: 14px 16px; border-radius: 10px; }

.empty { background: var(--surface); border: 1px solid var(--line); border-radius: 14px; text-align: center; padding: 54px 20px; }
.empty .emoji { font-size: 40px; margin-bottom: 12px; }
.empty h2 { font-size: 17px; font-weight: 700; color: var(--ink); }
.empty p { color: var(--ink-2); font-size: 14px; margin-top: 6px; }

.cards { display: grid; gap: 14px; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 18px 20px; transition: border-color .15s; }
.card:hover { border-color: var(--mint-dim); }
.row1 { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.who { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.dir { font-size: 11px; font-weight: 700; padding: 3px 9px; border-radius: 6px; }
.d-sent { background: var(--mint-bg); color: var(--mint); }
.d-recv { background: var(--violet-bg); color: var(--violet); }
.name { font-size: 16px; font-weight: 700; color: var(--ink); }
.role { font-size: 12px; color: var(--ink-3); }
.badge { font-size: 12px; font-weight: 700; padding: 3px 11px; border-radius: 999px; white-space: nowrap; }
.b-warn { background: var(--warn-bg); color: var(--warn); }
.b-ok { background: var(--ok-bg); color: var(--ok); }
.b-muted { background: var(--fill); color: var(--ink-3); }
.b-live { background: rgba(56,189,248,.16); color: #38bdf8; }

.preview { color: var(--ink); font-size: 14px; line-height: 1.6; margin-bottom: 6px; word-break: break-word; }
.ts { display: block; color: var(--ink-3); font-size: 12px; margin-bottom: 4px; }

.meeting { display: flex; align-items: center; gap: 10px; background: var(--ok-bg); border: 1px solid rgba(74,222,128,.25); border-radius: 8px; padding: 8px 12px; margin: 10px 0; }
.meeting strong { color: var(--ok); font-size: 13px; }
.meeting .loc { display: block; color: var(--ink-2); font-size: 12px; }

.actions { margin-top: 12px; }
.wait { color: var(--ink-3); font-size: 13px; }
.btn { border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
.btn.sm { padding: 8px 16px; font-size: 13px; }
.btn.primary { background: var(--mint); color: var(--on-mint); }
.btn.ghost { background: var(--surface-2); color: var(--mint); border: 1px solid var(--mint-dim); }
</style>
