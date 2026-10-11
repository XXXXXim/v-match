<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
const goStartup = () => router.push({ name: 'signup', query: { role: 'startup' } })
const goVC = () => router.push({ name: 'signup', query: { role: 'vc' } })
</script>

<template>
  <div class="role-select">
    <button class="back" @click="router.push({ name: 'home' })">← 처음으로</button>
    <h1>어떤 사용자이신가요?</h1>
    <p class="tagline">V-Match는 스타트업과 VC 모두를 위한 양방향 추천 서비스입니다.</p>

    <div class="choice-grid">
      <div class="choice-card startup" @click="goStartup">
        <div class="emoji">🧑‍💻</div>
        <h2>스타트업인가요?</h2>
        <p>투자자를 찾고 있는 스타트업이라면 선택하세요.</p>
        <span class="go">스타트업으로 시작 →</span>
      </div>

      <div class="choice-card vc" @click="goVC">
        <div class="emoji">💼</div>
        <h2>VC인가요?</h2>
        <p>좋은 스타트업을 찾고 있는 투자자라면 선택하세요.</p>
        <span class="go">VC로 시작 →</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.role-select { max-width: 860px; margin: 0 auto; padding: 50px 20px; text-align: center; }
.back { background: none; border: none; color: #2fe3b0; cursor: pointer; font-size: 14px; margin-bottom: 24px; }
.role-select h1 { font-size: 32px; font-weight: 800; color: #f3f6f4; }
.tagline { margin-top: 12px; font-size: 16px; color: #8a938e; }
.choice-grid { margin-top: 44px; display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.choice-card {
  background: #0e1311; border: 1px solid #1c2320; border-radius: 18px; padding: 40px 28px;
  cursor: pointer; transition: transform 0.18s, box-shadow 0.18s, border-color 0.18s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.choice-card:hover { transform: translateY(-6px); box-shadow: 0 16px 36px rgba(79,70,229,0.18); border-color: #5cf2c8; }
.choice-card .emoji { font-size: 40px; }
.choice-card h2 { margin-top: 14px; font-size: 23px; font-weight: 800; color: #f3f6f4; }
.choice-card p { margin-top: 10px; font-size: 15px; color: #8a938e; line-height: 1.6; }
.choice-card .go { display: inline-block; margin-top: 18px; font-weight: 700; color: #2fe3b0; }
.choice-card.startup:hover { border-color: #86efac; }
.choice-card.vc:hover { border-color: #5cf2c8; }
@media (max-width: 720px) { .choice-grid { grid-template-columns: 1fr; } }
</style>
