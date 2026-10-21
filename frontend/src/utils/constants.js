export const DAYS_LIST = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

export const formatDuration = (seconds, unit = 's') => {
  if (!seconds || seconds <= 0) return '0分钟'
  const num = Number(seconds)
  if (isNaN(num)) return '0分钟'

  const totalSeconds = unit === 'm' ? Math.round(num * 60) : Math.round(num)
  const totalMinutes = Math.round(totalSeconds / 60)

  if (totalMinutes <= 0) {
    return '1分钟'
  }

  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60

  if (hours > 0) {
    return minutes > 0 ? `${hours}小时${minutes}分钟` : `${hours}小时`
  }
  return `${minutes}分钟`
}

// 基于经纬度估算直线距离（km）
export const getDistanceBetweenCoords = (p1, p2) => {
  if (!p1 || !p2) return 0
  const lat1 = Number(p1.lat || p1.latitude)
  const lon1 = Number(p1.lng || p1.longitude)
  const lat2 = Number(p2.lat || p2.latitude)
  const lon2 = Number(p2.lng || p2.longitude)
  if (!lat1 || !lon1 || !lat2 || !lon2) return 0
  const R = 6371
  const dLat = ((lat2 - lat1) * Math.PI) / 180
  const dLon = ((lon2 - lon1) * Math.PI) / 180
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return R * c
}
