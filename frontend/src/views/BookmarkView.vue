<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import { formatMan } from '@/utils/money'

const router = useRouter()
const loading = ref(true)
const role = ref(null)
const items = ref([])

onMounted(async () => {
  try {
    const res = await api.get('/bookmarks/')
    role.value = res.data.role
    items.value = res.data.results
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}) 

const openDetail = (item) => {
  if (role.value === 'vc') router.push({ name: 'match-detail', params: { kind: 'startup', id: item.id } })
  else router.push({ name: 'match-detail', params: { kind: 'vc', id: item.id } })
}
</script>

<template>
  <div>
    <h2 class="page-title">북마크</h2>
    <p v-if="loading" class="info">불러오는 중...</p>
    <p v-else-if="items.length === 0" class="info">
      아직 북마크한 {{ role === 'startup' ? 'VC' : '스타트업' }}가 없습니다.
    </p>
    <div v-else>
      <div v-for="item in items" :key="item.id" class="card" @click="openDetail(item)">
        <div>
          <h3>{{ role === 'startup' ? item.firm_name : item.name }}</h3>
          <p class="sub" v-if="role === 'startup'">
            선호: {{ item.preferred_industries.join(', ') }} · {{ formatMan(item.min_investment) }} ~ {{ formatMan(item.max_investment) }}
          </p>
          <p class="sub" v-else>
            {{ item.industry }} · {{ item.stage }} · {{ item.region }}
          </p>
        </div>
        <span class="go">매칭 상세 →</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-title { margin-bottom: 20px; color: var(--ink); }
.info { color: var(--ink-2); }
/* flex-direction 을 명시(가로) — 부트스트랩 .card 의 column 강제와 충돌해
   세로로 쌓이며 가운데 정렬되던 문제 해결. 내용은 왼쪽 정렬. */
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 18px 20px; margin-bottom: 12px; display: flex; flex-direction: row; justify-content: space-between; align-items: center; text-align: left; gap: 16px; cursor: pointer; transition: border-color 0.15s; }
.card:hover { border-color: var(--mint-dim); }
.card h3 { font-size: 16px; font-weight: 700; color: var(--ink); text-align: left; }
.sub { margin-top: 4px; font-size: 13px; color: var(--ink-2); text-align: left; }
.go { color: var(--mint); font-size: 13px; font-weight: 600; white-space: nowrap; }
</style>
