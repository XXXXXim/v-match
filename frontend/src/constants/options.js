// 백엔드 추천 로직과 반드시 일치해야 하는 선택지
export const INDUSTRIES = [
  'SaaS', 'Fintech', 'Healthcare', 'AI/ML', 'E-commerce',
  'EdTech', 'Bio', 'Gaming', 'Mobility', 'Other',
]

// VC 선호 산업 선택지: 'All'(전 산업) 포함
export const ALL_INDUSTRY = 'All'
export const VC_INDUSTRY_OPTIONS = [ALL_INDUSTRY, ...INDUSTRIES]

export const STAGES = ['Seed', 'Pre-A', 'Series A', 'Series B', 'Series C+']

export const REGIONS = ['서울', '경기', '부산', '대전', '기타']

// VC 선호 지역: '전국'(전 지역) 포함
export const ALL_REGION = '전국'
export const VC_REGION_OPTIONS = [ALL_REGION, ...REGIONS]
