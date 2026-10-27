// 坐标系工具：WGS-84 <-> GCJ-02 转换、坐标静态校验、坐标系自动检测
// 系统内部统一使用 GCJ-02（高德坐标系）；WGS-84 数据在导入时转换。
import { loadAMap } from '../composables/useAMap.js'

const PI = Math.PI
const A = 6378245.0 // 长半轴
const EE = 0.00669342162296594323 // 偏心率平方

function transformLat(lng, lat) {
  let ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + 0.1 * lng * lat + 0.2 * Math.sqrt(Math.abs(lng))
  ret += ((20.0 * Math.sin(6.0 * lng * PI) + 20.0 * Math.sin(2.0 * lng * PI)) * 2.0) / 3.0
  ret += ((20.0 * Math.sin(lat * PI) + 40.0 * Math.sin((lat / 3.0) * PI)) * 2.0) / 3.0
  ret += ((160.0 * Math.sin((lat / 12.0) * PI) + 320 * Math.sin((lat * PI) / 30.0)) * 2.0) / 3.0
  return ret
}

function transformLng(lng, lat) {
  let ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + 0.1 * lng * lat + 0.1 * Math.sqrt(Math.abs(lng))
  ret += ((20.0 * Math.sin(6.0 * lng * PI) + 20.0 * Math.sin(2.0 * lng * PI)) * 2.0) / 3.0
  ret += ((20.0 * Math.sin(lng * PI) + 40.0 * Math.sin((lng / 3.0) * PI)) * 2.0) / 3.0
  ret += ((150.0 * Math.sin((lng / 12.0) * PI) + 300.0 * Math.sin((lng / 30.0) * PI)) * 2.0) / 3.0
  return ret
}

/** 是否在中国大陆范围外（范围外无偏移，无需转换） */
export function outOfChina(lng, lat) {
  return lng < 72.004 || lng > 137.8347 || lat < 0.8293 || lat > 55.8271
}

/** WGS-84 (GPS 原始) -> GCJ-02 (高德/火星坐标) */
export function wgs84ToGcj02(lng, lat) {
  if (outOfChina(lng, lat)) return [lng, lat]
  let dLat = transformLat(lng - 105.0, lat - 35.0)
  let dLng = transformLng(lng - 105.0, lat - 35.0)
  const radLat = (lat / 180.0) * PI
  let magic = Math.sin(radLat)
  magic = 1 - EE * magic * magic
  const sqrtMagic = Math.sqrt(magic)
  dLat = (dLat * 180.0) / (((A * (1 - EE)) / (magic * sqrtMagic)) * PI)
  dLng = (dLng * 180.0) / (A / sqrtMagic * Math.cos(radLat) * PI)
  return [lng + dLng, lat + dLat]
}

/** GCJ-02 -> WGS-84（近似逆变换，误差 < 1-2m，仅用于比对/展示） */
export function gcj02ToWgs84(lng, lat) {
  if (outOfChina(lng, lat)) return [lng, lat]
  const [gLng, gLat] = wgs84ToGcj02(lng, lat)
  return [lng * 2 - gLng, lat * 2 - gLat]
}

/** 两经纬度点间球面距离（米） */
export function haversineMeters(p1, p2) {
  const R = 6378137
  const dLat = ((p2.lat - p1.lat) * PI) / 180
  const dLng = ((p2.lng - p1.lng) * PI) / 180
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((p1.lat * PI) / 180) * Math.cos((p2.lat * PI) / 180) * Math.sin(dLng / 2) ** 2
  return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

/**
 * 静态坐标校验（不依赖网络）：
 * - 非法范围 / 超出中国域 / 疑似经纬度互换 / 疑似度分格式（如 10818.34 而非 108.18）
 * 返回 warnings: string[]
 */
export function validateCoordinatePoints(points) {
  const warnings = []
  if (!points || points.length === 0) return warnings

  const lats = points.map((p) => p.lat)
  const lngs = points.map((p) => p.lng)

  // 疑似经纬度列互换（中国业务：lng≈73-136, lat≈3-54）
  const lngLooksLikeLat = lngs.every((v) => v > 0 && v < 60) && lats.every((v) => v >= 60 && v < 140)
  if (lngLooksLikeLat) {
    warnings.push('检测到所有点的“经度”数值落在纬度区间、“纬度”数值落在经度区间——疑似两列互换，请检查 Excel 列顺序')
  }

  let outOfChinaCount = 0
  const badRows = []
  points.forEach((p, i) => {
    const label = p.shop_code || p.name || `第 ${i + 1} 条`
    if (Math.abs(p.lng) > 180 || Math.abs(p.lat) > 90) {
      badRows.push(`${label} (${p.lng}, ${p.lat})`)
    } else if (p.lng === 0 || p.lat === 0) {
      warnings.push(`${label} 坐标为 (0, 0)，疑似缺失占位值，请核对`)
    } else if (outOfChina(p.lng, p.lat)) {
      outOfChinaCount++
    }
    // 疑似度分格式（ddmm.mmmm）：整数部分 > 180 不可能，这里捕获 1000-9999 段
    if ((Math.abs(p.lng) >= 1000 && Math.abs(p.lng) < 10000) || (Math.abs(p.lat) >= 1000 && Math.abs(p.lat) < 10000)) {
      warnings.push(`${label} 坐标数值异常偏大（${p.lng}, ${p.lat}），疑似度分格式（ddmm.mmmm），需先转换为十进制度`)
    }
  })
  if (badRows.length > 0) {
    warnings.push(`有 ${badRows.length} 条记录经纬度超出合法范围：${badRows.slice(0, 3).join('； ')}${badRows.length > 3 ? ' ...' : ''}`)
  }
  if (outOfChinaCount > 0 && outOfChinaCount === points.length) {
    warnings.push('全部坐标均落在中国大陆范围之外——若数据确在中国，请检查坐标系/列顺序是否正确')
  }
  return warnings
}

/**
 * 基于地址地理编码的坐标系自动检测（抽样）。
 * 原理：高德 Geocoder 返回 GCJ-02 坐标。对每个样本分别计算：
 *   errGcj = dist(导入坐标, 编码坐标)         —— 若导入为 GCJ-02 应较小
 *   errWgs = dist(wgs84ToGcj02(导入), 编码坐标) —— 若导入为 WGS-84 应较小
 * 多数投票 + 偏移量中位数给出结论。
 *
 * @returns {Promise<{system:'gcj02'|'wgs84'|'unknown', tested:number, medianOffsetMeters:number, reason:string}>}
 */
export async function detectCoordinateSystemByAddress(points, { sampleSize = 5 } = {}) {
  // 取带地址、且地址含足够信息（>=4 字）的样本
  const candidates = points.filter((p) => (p.address || '').replace(/\s/g, '').length >= 4)
  if (candidates.length === 0) {
    return { system: 'unknown', tested: 0, medianOffsetMeters: 0, reason: '数据中无可用地址，无法自动比对' }
  }
  const step = Math.max(1, Math.floor(candidates.length / sampleSize))
  const samples = []
  for (let i = 0; i < candidates.length && samples.length < sampleSize; i += step) samples.push(candidates[i])

  let AMap
  try {
    AMap = await loadAMap()
  } catch (e) {
    return { system: 'unknown', tested: 0, medianOffsetMeters: 0, reason: '地图服务加载失败，无法自动检测（' + (e.message || e) + '）' }
  }

  const geocodeOne = (addr) =>
    new Promise((resolve) => {
      const geocoder = new AMap.Geocoder({ city: '全国' })
      const timer = setTimeout(() => resolve(null), 5000)
      geocoder.getLocation(addr, (status, result) => {
        clearTimeout(timer)
        if (status === 'complete' && result?.geocodes?.[0]?.location) {
          resolve({ lng: result.geocodes[0].location.lng, lat: result.geocodes[0].location.lat })
        } else {
          resolve(null)
        }
      })
    })

  let voteGcj = 0
  let voteWgs = 0
  const offsets = []
  let tested = 0

  for (const p of samples) {
    const geo = await geocodeOne(p.address)
    if (!geo) continue
    tested++
    const errGcj = haversineMeters({ lng: p.lng, lat: p.lat }, geo)
    const [cLng, cLat] = wgs84ToGcj02(p.lng, p.lat)
    const errWgs = haversineMeters({ lng: cLng, lat: cLat }, geo)
    // 地址编码本身有误差（门牌级 ~100-200m），只信任显著差异
    if (errGcj < 150 && errWgs > errGcj * 1.5) voteGcj++
    else if (errWgs < 150 && errGcj > errWgs * 1.5) voteWgs++
    offsets.push(Math.min(errGcj, errWgs))
  }

  if (tested === 0) {
    return { system: 'unknown', tested: 0, medianOffsetMeters: 0, reason: '地址地理编码全部失败（地址过短或服务不可用）' }
  }
  const sorted = [...offsets].sort((a, b) => a - b)
  const median = sorted[Math.floor(sorted.length / 2)]

  if (voteWgs > voteGcj && voteWgs >= Math.ceil(tested / 2)) {
    return { system: 'wgs84', tested, medianOffsetMeters: Math.round(median), reason: `抽样 ${tested} 条地址比对：按 WGS-84 解释时与高德编码位置吻合（中位偏差 ${Math.round(median)}m），按 GCJ-02 解释存在系统性偏移` }
  }
  if (voteGcj > voteWgs && voteGcj >= Math.ceil(tested / 2)) {
    return { system: 'gcj02', tested, medianOffsetMeters: Math.round(median), reason: `抽样 ${tested} 条地址比对：导入坐标与高德编码位置直接吻合，为 GCJ-02（高德）坐标` }
  }
  return { system: 'unknown', tested, medianOffsetMeters: Math.round(median), reason: `抽样 ${tested} 条地址比对差异不显著（中位偏差 ${Math.round(median)}m），无法自动判断，请人工确认` }
}
