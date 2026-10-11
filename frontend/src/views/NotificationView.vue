<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(true)
const items = ref([])

const fetchNotis = async () => {
  loading.value = true
  try {
    const res = await api.get('/notifications/')
    items.value = res.data.results
    if (res.data.unread > 0) {
      await api.post('/notifications/read/')
      window.dispatchEvent(new CustomEvent('notif-read'))
    }
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

// 알림 클릭 시 이동: 커피챗 → 커피챗 목록, 매칭 → 매칭 페이지, 좋아요 → 상대 상세
const onClickNoti = (n) => {
  if (n.kind === 'coffeechat') {
    router.push({ name: 'coffeechats' })
    return
  }
  if (n.kind === 'match') {
    router.push({ name: 'matches' })
    return
  }
  if (auth.user?.role === 'startup' && n.vc_id) {
    router.push({ name: 'vc-detail', params: { id: n.vc_id } })
  } else if (auth.user?.role === 'vc' && n.startup_id) {
    router.push({ name: 'match-detail', params: { kind: 'startup', id: n.startup_id } })
  } else {
    router.push({ name: 'matches' })
  }
}

const fmt = (s) => new Date(s).toLocaleString('ko-KR')

onMounted(fetchNotis)
</script>

<template>
  <div>
    <h2 class="page-title">알림</h2>
    <p v-if="loading" class="info">불러오는 중...</p>
    <p v-else-if="items.length === 0" class="info">알림이 없습니다.</p>
    <div v-else>
      <div
        v-for="n in items"
        :key="n.id"
        class="noti"
        :class="{ unread: !n.is_read }"
        @click="onClickNoti(n)"
      >
        <p class="msg">{{ n.message }}</p>
        <div class="bottom">
          <span class="time">{{ fmt(n.created_at) }}</span>
          <span class="go">{{ n.kind === 'coffeechat' ? '커피챗 보기 →' : n.kind === 'match' ? '매칭 보기 →' : '자세히 보기 →' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-title { margin-bottom: 20px; }
.info { color: #8a938e; }
.noti {
  background: #0e1311; border: 1px solid #1c2320; border-radius: 10px;
  padding: 14px 16px; margin-bottom: 10px; cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.noti:hover { border-color: #5cf2c8; box-shadow: 0 4px 12px rgba(79,70,229,0.1); }
.noti.unread { border-left: 4px solid #2fe3b0; background: #161d19; }
.msg { font-size: 14px; color: #e6ebe8; }
.bottom { margin-top: 6px; display: flex; justify-content: space-between; align-items: center; }
.time { font-size: 12px; color: #717b76; }
.go { font-size: 12px; font-weight: 600; color: #2fe3b0; }
</style>
