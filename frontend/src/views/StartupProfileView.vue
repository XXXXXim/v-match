<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'

const router = useRouter()
const loading = ref(true)

const pitchUploaded = ref(false)
const irUploaded = ref(false)
const pitchFile = ref(null)
const irFile = ref(null)
const pitchUploading = ref(false)
const irUploading = ref(false)
const msg = ref('')
const msgType = ref('success')
const allUploading = ref(false)

const registered = computed(() => pitchUploaded.value && irUploaded.value)

const loadStatus = async () => {
  loading.value = true
  try {
    const res = await api.get('/profile-status/')
    pitchUploaded.value = !!res.data.pitch_uploaded
    irUploaded.value = !!res.data.ir_uploaded
  } catch {
    /* 미등록 상태 */
  } finally {
    loading.value = false
  }
}

const pickPitch = (e) => { pitchFile.value = e.target.files[0] || null }
const pickIr = (e) => { irFile.value = e.target.files[0] || null }

const flash = (text, type = 'success') => {
  msg.value = text; msgType.value = type
  setTimeout(() => { if (msg.value === text) msg.value = '' }, 4000)
}

const uploadPitch = async () => {
  if (!pitchFile.value) return flash('피치덱 PDF를 선택해주세요.', 'error')
  if (!pitchFile.value.name.toLowerCase().endsWith('.pdf')) return flash('PDF 파일만 업로드 가능합니다.', 'error')
  pitchUploading.value = true
  try {
    const fd = new FormData()
    fd.append('pitch_deck', pitchFile.value)
    await api.post('/startup-profile/pitch-deck/', fd)
    pitchUploaded.value = true
    flash('피치덱이 등록되었습니다.')
  } catch (e) {
    flash(e.response?.data?.error || '피치덱 등록에 실패했습니다.', 'error')
  } finally {
    pitchUploading.value = false
  }
}

const uploadIr = async () => {
  if (!irFile.value) return flash('IR덱 PDF를 선택해주세요.', 'error')
  if (!irFile.value.name.toLowerCase().endsWith('.pdf')) return flash('PDF 파일만 업로드 가능합니다.', 'error')
  irUploading.value = true
  try {
    const fd = new FormData()
    fd.append('ir_deck', irFile.value)
    await api.post('/startup-profile/ir-deck/', fd)
    irUploaded.value = true
    flash('IR덱이 등록되었습니다.')
  } catch (e) {
    flash(e.response?.data?.error || 'IR덱 등록에 실패했습니다.', 'error')
  } finally {
    irUploading.value = false
  }
}

const completeProfile = async () => {
  if (registered.value) return goRecommend()
  if (!pitchUploaded.value && !pitchFile.value) return flash('피치덱 PDF를 선택해주세요.', 'error')
  if (!irUploaded.value && !irFile.value) return flash('IR덱 PDF를 선택해주세요.', 'error')
  const files = [pitchFile.value, irFile.value].filter(Boolean)
  if (files.some((f) => !f.name.toLowerCase().endsWith('.pdf'))) return flash('PDF 파일만 업로드 가능합니다.', 'error')
  allUploading.value = true
  try {
    if (!pitchUploaded.value || pitchFile.value) {
      const pitchData = new FormData(); pitchData.append('pitch_deck', pitchFile.value)
      await api.post('/startup-profile/pitch-deck/', pitchData)
      pitchUploaded.value = true
    }
    if (!irUploaded.value || irFile.value) {
      const irData = new FormData(); irData.append('ir_deck', irFile.value)
      await api.post('/startup-profile/ir-deck/', irData)
      irUploaded.value = true
    }
    flash('프로필 등록이 완료되었습니다.')
    setTimeout(goRecommend, 700)
  } catch (e) {
    flash(e.response?.data?.error || '등록 중 문제가 발생했습니다. 완료된 파일은 안전하게 저장되어 있습니다.', 'error')
  } finally { allUploading.value = false }
}

const goRecommend = () => router.push({ name: 'vc-recommend' })

onMounted(loadStatus)
</script>

<template>
  <div class="wrap">
    <span class="step">가입 절차 3 / 3</span>
    <h2 class="title">마지막으로 자료를 등록해주세요</h2>
    <p class="sub">두 PDF를 선택한 뒤 한 번에 제출할 수 있어요. IR덱은 매칭 전에는 공개되지 않습니다.</p>

    <p v-if="loading" class="info">불러오는 중...</p>

    <template v-else>
      <!-- 완료 배너 -->
      <div v-if="registered" class="done-banner">
        프로필 등록이 완료되었습니다.
        <button class="btn primary" @click="goRecommend">VC 추천 보기 →</button>
      </div>

      <div v-if="msg" class="flash" :class="msgType">{{ msg }}</div>

      <!-- 피치덱 -->
      <div class="upload-card" :class="{ complete: pitchUploaded }">
        <div class="card-head">
          <h3>피치덱 <small>외부 공개 자료</small></h3>
          <span v-if="pitchUploaded" class="chip ok">등록 완료</span>
          <span v-else class="chip">미등록</span>
        </div>
        <p class="hint">투자자에게 보여줄 간결한 소개 슬라이드 (PDF)</p>
        <div class="row">
          <input type="file" accept="application/pdf" @change="pickPitch" />
        </div>
      </div>

      <!-- IR덱 -->
      <div class="upload-card" :class="{ complete: irUploaded }">
        <div class="card-head">
          <h3>IR덱 <small>매칭 후 분석 자료</small></h3>
          <span v-if="irUploaded" class="chip ok">등록 완료</span>
          <span v-else class="chip">미등록</span>
        </div>
        <p class="hint">상세 사업 자료 (PDF) — 매칭 후 AI 리포트 분석에 사용됩니다.</p>
        <div class="row">
          <input type="file" accept="application/pdf" @change="pickIr" />
        </div>
      </div>

      <div class="privacy-note"><span>🔒</span><p><b>자료 공개 범위를 지켜드려요.</b><br>피치덱은 추천에 사용되고, IR덱 원문은 상호 매칭 전까지 상대에게 공개되지 않습니다.</p></div>
      <button class="complete-btn" :disabled="allUploading" @click="completeProfile">{{ allUploading ? '자료를 안전하게 등록하는 중...' : registered ? 'VC 추천 보러 가기 →' : '프로필 완성하고 추천 보기 →' }}</button>
    </template>
  </div>
</template>

<style scoped>
.wrap { max-width: 640px; margin: 0 auto; padding: 30px 20px; }
.title { font-size: 24px; font-weight: 800; }
.step { color:#2fe3b0;font-size:12px;font-weight:850;letter-spacing:.5px; }
.sub { margin-top: 8px; color: #8a938e; }
.info { color: #8a938e; margin-top: 20px; }
.done-banner {
  margin: 20px 0; padding: 16px 18px; background: #0d1f17; border: 1px solid #6ee7b7;
  border-radius: 12px; color: #4ade80; font-weight: 700;
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
}
.flash { margin: 14px 0; padding: 10px 14px; border-radius: 8px; font-size: 14px; }
.flash.success { background: #0d1f17; color: #4ade80; }
.flash.error { background: #2a1416; color: #f87171; }
.upload-card {
  margin-top: 18px; background: #0e1311; border: 1px solid #1c2320; border-radius: 14px; padding: 20px;
}
.upload-card.complete { border-color: #6ee7b7; background: #0d1f17; }
.card-head { display: flex; align-items: center; gap: 10px; }
.card-head h3 { font-size: 17px; font-weight: 700; }
.card-head h3 small { margin-left:6px;color:#717b76;font-size:11px;font-weight:600; }
.chip { font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 999px; background: #161d19; color: #8a938e; }
.chip.ok { background: #10241a; color: #34d399; }
.hint { margin-top: 8px; color: #8a938e; font-size: 13px; }
.row { margin-top: 14px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.row input[type='file'] { font-size: 13px; }
.btn { padding: 9px 18px; border-radius: 8px; border: 1px solid #1f3a32; background: #10201b; color: #25c79a; font-weight: 600; cursor: pointer; font-size: 14px; }
.btn:disabled { opacity: 0.6; cursor: wait; }
.btn.primary { background: #2fe3b0; color: #0e1311; border-color: #2fe3b0; }
.foot-note { margin-top: 22px; font-size: 13px; color: #717b76; }
.privacy-note { margin-top:20px;padding:14px;display:flex;gap:10px;background:#121815;border-radius:10px;color:#9aa39e;font-size:13px;line-height:1.55; }.privacy-note b{color:#3f3f50}.complete-btn{width:100%;margin-top:16px;padding:13px;color:#0e1311;background:#2fe3b0;border:0;border-radius:10px;font-size:15px;font-weight:750;cursor:pointer}.complete-btn:disabled{opacity:.65;cursor:wait}
</style>
