<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'

const router = useRouter()
const loading = ref(true)
const matches = ref([])
const openingChat = ref(null)   // '커피챗으로 이동' 중복 클릭 방지

// NDA 모달 상태
const ndaOpen = ref(false)
const ndaChecked = ref(false)
const ndaAction = ref(null) // 'request' | 'accept'
const ndaMatchId = ref(null)
const submitting = ref(false)


const STATUS_LABEL = {
  matched: '매칭됨', requested: '커피챗 요청됨', accepted: '수락 완료', declined: '거절됨',
}

const fetchMatches = async () => {
  loading.value = true
  try {
    matches.value = (await api.get('/matches/')).data
  } catch {
    matches.value = []
  } finally {
    loading.value = false
  }
}

const counterpart = (m) => (m.my_role === 'vc' ? m.startup.name : m.vc.firm_name)

// IR 원본은 공개 URL 이 아니라 권한 검사를 거치는 게이트 엔드포인트에서 받는다.
// 토큰 헤더가 필요하므로 axios(api)로 blob 을 받아 다운로드한다.
const downloadIr = async (deck) => {
  try {
    const res = await api.get(deck.download_url, { responseType: 'blob' })
    const blobUrl = window.URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = `IR_deck_${deck.id}.pdf`
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(blobUrl)
  } catch (e) {
    window.alert(
      e.response?.status === 403
        ? 'IR 원본 접근 권한이 없습니다. (매칭 후 양측 NDA 동의가 필요합니다)'
        : 'IR 다운로드에 실패했습니다.',
    )
  }
}

const openNda = (m, action) => {
  ndaMatchId.value = m.id
  ndaAction.value = action
  ndaChecked.value = false
  ndaOpen.value = true
}

const confirmNda = async () => {
  if (!ndaChecked.value) return
  submitting.value = true
  try {
    const url = `/matches/${ndaMatchId.value}/${ndaAction.value}/`
    await api.post(url, { nda_agreed: true })
    ndaOpen.value = false
    await fetchMatches()
  } catch (e) {
    window.alert(e.response?.data?.error || '처리에 실패했습니다.')
  } finally {
    submitting.value = false
  }
}

// 수락된 매칭에서 '커피챗으로 이동' → 연결된 스레드를 찾거나 만들어 채팅창으로 이동
const openCoffeeChat = async (m) => {
  openingChat.value = m.id
  try {
    const res = await api.post(`/matches/${m.id}/coffeechat/`)
    router.push({ name: 'coffeechat-thread', params: { id: res.data.coffeechat_id } })
  } catch (e) {
    window.alert(e.response?.data?.error || '커피챗을 열지 못했습니다.')
  } finally {
    openingChat.value = null
  }
}

// 상대(VC/스타트업) 정보 상세 보기 → AI 심층 분석 리포트
const goDetail = (m) => {
  if (m.my_role === 'vc') {
    router.push({ name: 'match-detail', params: { kind: 'startup', id: m.startup.id } })
  } else {
    router.push({ name: 'match-detail', params: { kind: 'vc', id: m.vc.id } })
  }
}

onMounted(fetchMatches)
</script>

<template>
  <div>
    <h2 class="page-title">매칭</h2>
    <p class="hint">서로 좋아요한 상대와의 매칭입니다. 커피챗을 요청하고 NDA에 동의하면 연락처·IR 원본이 열리고, 커피챗 채팅이 시작됩니다.</p>

    <p v-if="loading" class="info">불러오는 중...</p>
    <p v-else-if="matches.length === 0" class="info">아직 성사된 매칭이 없습니다. (서로 좋아요하면 매칭됩니다)</p>

    <div v-else>
      <div v-for="m in matches" :key="m.id" class="card">
        <div class="top">
          <div>
            <h3>{{ counterpart(m) }}</h3>
            <span class="badge" :class="m.status">{{ STATUS_LABEL[m.status] }}</span>
          </div>
          <RouterLink class="deep-link"
            :to="m.my_role === 'vc'
              ? { name: 'match-detail', params: { kind: 'startup', id: m.startup.id } }
              : { name: 'match-detail', params: { kind: 'vc', id: m.vc.id } }">
            🔍 AI 심층 분석 보기
          </RouterLink>
        </div>

        <!-- 액션 -->
        <div class="actions" v-if="m.status !== 'accepted' && m.status !== 'declined'">
          <button v-if="m.can_request" class="btn primary" @click="openNda(m, 'request')">
            ☕ 커피챗 요청 (NDA)
          </button>
          <button v-if="m.can_accept" class="btn primary" @click="openNda(m, 'accept')">
            ✅ 요청 수락 (NDA)
          </button>
          <span v-if="m.waiting" class="waiting">상대의 수락을 기다리는 중...</span>
        </div>

        <!-- 잠금 해제 패널 -->
        <div v-if="m.status === 'accepted'" class="unlocked">
          <div class="unlock-head">🔓 블라인드 해제됨</div>

          <div class="block">
            <strong>📇 연락처</strong>
            <p>VC: {{ m.contact.vc_email }}</p>
            <p>스타트업: {{ m.contact.startup_email }}</p>
          </div>

          <div class="block" v-if="m.my_role === 'vc'">
            <strong>📄 IR 덱 원본</strong>
            <template v-if="m.ir_decks && m.ir_decks.length">
              <p v-for="d in m.ir_decks" :key="d.id">
                <a href="#" @click.prevent="downloadIr(d)" class="dl">원본 PDF 다운로드 →</a>
                <span class="muted"> ({{ new Date(d.uploaded_at).toLocaleDateString() }})</span>
              </p>
            </template>
            <p v-else class="muted">등록된 IR Deck 파일이 없습니다.</p>
          </div>

          <!-- 수락 완료 시: 채팅 이동 + 상대 상세보기 -->
          <div class="cta-row">
            <button class="btn primary" :disabled="openingChat === m.id" @click="openCoffeeChat(m)">
              {{ openingChat === m.id ? '여는 중...' : '💬 커피챗으로 이동' }}
            </button>
            <button class="btn ghost" @click="goDetail(m)">🔍 상세보기</button>
          </div>
        </div>
      </div>
    </div>

    <!-- NDA 모달 -->
    <div v-if="ndaOpen" class="modal-overlay" @click.self="ndaOpen = false">
      <div class="vm-modal">
        <h3>비밀유지계약(NDA) 동의</h3>
        <p class="nda-text">
          본 미팅에서 오가는 사업 정보·IR 자료·기술 내용 등 일체에 대해 비밀을 유지하며,
          상대의 동의 없이 제3자에게 공유하지 않을 것에 동의합니다.
        </p>
        <label class="nda-check">
          <input type="checkbox" v-model="ndaChecked" />
          위 비밀유지(NDA) 내용에 동의합니다.
        </label>
        <div class="modal-actions">
          <button class="btn ghost" @click="ndaOpen = false">취소</button>
          <button class="btn primary" :disabled="!ndaChecked || submitting" @click="confirmNda">
            {{ submitting ? '처리 중...' : '동의하고 진행' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-title { margin-bottom: 6px; color: var(--ink); }
.hint { color: var(--ink-2); font-size: 14px; margin-bottom: 18px; }
.info { color: var(--ink-2); }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 20px; margin-bottom: 14px; }
.top { display: flex; justify-content: space-between; align-items: center; }
.deep-link { font-size: 13px; color: var(--mint); font-weight: 600; white-space: nowrap; }
/* 상대 기업명: 또렷하게 */
.top h3 { font-size: 18px; font-weight: 700; display: inline-block; margin-right: 10px; color: var(--ink); }
.badge { font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 999px; }
.badge.matched { background: var(--pink-bg); color: var(--pink); }
.badge.requested { background: var(--warn-bg); color: var(--warn); }
.badge.accepted { background: var(--ok-bg); color: var(--ok); }
.badge.declined { background: var(--fill); color: var(--ink-3); }
.actions { margin-top: 14px; }
.waiting { color: var(--ink-2); font-size: 14px; }
.btn { padding: 10px 18px; border-radius: 8px; font-weight: 600; font-size: 14px; cursor: pointer; border: none; }
.btn.primary { background: var(--mint); color: var(--on-mint); }
.btn.primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn.ghost { background: var(--surface); color: var(--mint); border: 1px solid var(--mint-dim); }
.cta-row { display: flex; gap: 10px; margin-top: 16px; flex-wrap: wrap; }
.unlocked { margin-top: 14px; border-top: 1px dashed var(--line); padding-top: 14px; }
.unlock-head { font-weight: 700; color: var(--ok); margin-bottom: 10px; }
.block { margin-bottom: 12px; font-size: 14px; }
/* 섹션 라벨(연락처/IR/브리핑 제목): 또렷하게 */
.block strong { display: block; margin-bottom: 4px; color: var(--ink); }
.block p { color: var(--ink-2); }
.dl { color: var(--mint); font-weight: 600; }
.muted { color: var(--ink-3); }
/* AI 브리핑 박스: 본문 글씨가 안 보이던 문제 수정(밝은 색으로) */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.55); display: flex; align-items: center; justify-content: center; z-index: 50; }
.vm-modal { background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 24px; width: 92%; max-width: 440px; }
.vm-modal h3 { font-size: 18px; font-weight: 700; margin-bottom: 12px; color: var(--ink); }
.nda-text { font-size: 14px; color: var(--ink-2); line-height: 1.6; background: var(--bg-2); border-radius: 8px; padding: 14px; }
.nda-check { display: flex; align-items: center; gap: 8px; margin-top: 14px; font-size: 14px; color: var(--ink); }
.modal-actions { margin-top: 20px; display: flex; gap: 10px; justify-content: flex-end; }
</style>
