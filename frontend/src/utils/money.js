// 금액 단위는 '만원'으로 저장된다.
// formatMan(30000) -> '3억 원', formatMan(35000) -> '3억 5,000만 원', formatMan(600) -> '600만 원'
export function formatMan(man) {
  const n = Math.round(Number(man) || 0)
  if (n === 0) return '0원'
  const eok = Math.floor(n / 10000)
  const rem = n % 10000
  if (eok && rem) return `${eok}억 ${rem.toLocaleString()}만 원`
  if (eok) return `${eok}억 원`
  return `${n.toLocaleString()}만 원`
}
