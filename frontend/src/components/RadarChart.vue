<script setup>
import { computed } from 'vue'

const props = defineProps({
  subScores: { type: Object, required: true },
})

// recommend.py WEIGHTS 와 일치 (축 순서 = 표시 순서)
const AXES = [
  { key: 'industry', label: '산업', max: 40 },
  { key: 'stage', label: '단계', max: 25 },
  { key: 'funding', label: '투자금', max: 20 },
  { key: 'region', label: '지역', max: 15 },
]

const SIZE = 220
const CX = SIZE / 2
const CY = SIZE / 2
const R = 78

// 각 축의 각도 (위에서 시작, 시계방향)
const angleFor = (i) => (-90 + (360 / AXES.length) * i) * (Math.PI / 180)

const pointAt = (i, ratio) => {
  const a = angleFor(i)
  return [CX + Math.cos(a) * R * ratio, CY + Math.sin(a) * R * ratio]
}

// 격자(25/50/75/100%) 폴리곤
const gridPolygons = computed(() =>
  [0.25, 0.5, 0.75, 1].map((ring) =>
    AXES.map((_, i) => pointAt(i, ring).join(',')).join(' ')
  )
)

// 데이터 폴리곤
const dataPoints = computed(() =>
  AXES.map((ax, i) => {
    const val = props.subScores[ax.key] || 0
    const ratio = Math.max(0, Math.min(1, val / ax.max))
    return pointAt(i, ratio)
  })
)
const dataPolygon = computed(() => dataPoints.value.map((p) => p.join(',')).join(' '))

const labelAt = (i) => pointAt(i, 1.22)
</script>

<template>
  <svg :viewBox="`0 0 ${SIZE} ${SIZE}`" class="radar">
    <!-- 격자 -->
    <polygon
      v-for="(poly, idx) in gridPolygons"
      :key="'g' + idx"
      :points="poly"
      fill="none"
      stroke="#1c2320"
      stroke-width="1"
    />
    <!-- 축선 -->
    <line
      v-for="(ax, i) in AXES"
      :key="'axis' + i"
      :x1="CX" :y1="CY"
      :x2="pointAt(i, 1)[0]" :y2="pointAt(i, 1)[1]"
      stroke="#1c2320" stroke-width="1"
    />
    <!-- 데이터 영역 -->
    <polygon
      :points="dataPolygon"
      fill="rgba(99,102,241,0.25)"
      stroke="#2fe3b0"
      stroke-width="2"
    />
    <circle
      v-for="(p, i) in dataPoints"
      :key="'pt' + i"
      :cx="p[0]" :cy="p[1]" r="3" fill="#2fe3b0"
    />
    <!-- 라벨 -->
    <text
      v-for="(ax, i) in AXES"
      :key="'lbl' + i"
      :x="labelAt(i)[0]" :y="labelAt(i)[1]"
      text-anchor="middle"
      dominant-baseline="middle"
      class="axis-label"
    >{{ ax.label }} {{ subScores[ax.key] || 0 }}</text>
  </svg>
</template>

<style scoped>
.radar {
  width: 220px;
  height: 220px;
  display: block;
  margin: 0 auto;
}
.axis-label {
  font-size: 11px;
  fill: #aab3ae;
  font-weight: 600;
}
</style>
