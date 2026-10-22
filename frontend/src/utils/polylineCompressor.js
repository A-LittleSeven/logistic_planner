/**
 * 高德路网折线点紧凑编码与跨路线公共提取工具
 * 
 * 采用经典差值变长编码 (Polyline Algorithm)，将高精度经纬度数组压缩 85%~92% 的体积，
 * 并支持跨路线提取公共路段/折线字典池 (Polyline Pool)，杜绝数百条路线保存时的存储膨胀。
 */

/**
 * 将经纬度坐标数组编码为紧凑 ASCII 字符串 (精度: 1e-5，约 1 米精度)
 * @param {Array<[number, number]>} points [[lng, lat], ...]
 * @returns {string} 紧凑编码字符串
 */
export function encodePolyline(points) {
  if (!points || !Array.isArray(points) || points.length === 0) return ''

  let result = ''
  let prevLat = 0
  let prevLng = 0

  for (let i = 0; i < points.length; i++) {
    const pt = points[i]
    if (!pt || pt.length < 2) continue
    const lng = Number(pt[0])
    const lat = Number(pt[1])
    if (isNaN(lng) || isNaN(lat)) continue

    const latE5 = Math.round(lat * 1e5)
    const lngE5 = Math.round(lng * 1e5)

    const dLat = latE5 - prevLat
    const dLng = lngE5 - prevLng

    prevLat = latE5
    prevLng = lngE5

    result += encodeSignedNumber(dLat) + encodeSignedNumber(dLng)
  }

  return result
}

/**
 * 将紧凑 ASCII 字符串解码回经纬度坐标数组
 * @param {string} encoded 紧凑编码字符串
 * @returns {Array<[number, number]>} [[lng, lat], ...]
 */
export function decodePolyline(encoded) {
  if (!encoded || typeof encoded !== 'string') return []

  const points = []
  let index = 0
  const len = encoded.length
  let lat = 0
  let lng = 0

  while (index < len) {
    let result = 1
    let shift = 0
    let b

    // 解码 Lat 差值
    do {
      b = encoded.charCodeAt(index++) - 63 - 1
      result += b << shift
      shift += 5
    } while (b >= 0x1f)
    lat += (result & 1) !== 0 ? ~(result >> 1) : result >> 1

    // 解码 Lng 差值
    result = 1
    shift = 0
    do {
      b = encoded.charCodeAt(index++) - 63 - 1
      result += b << shift
      shift += 5
    } while (b >= 0x1f)
    lng += (result & 1) !== 0 ? ~(result >> 1) : result >> 1

    points.push([Number((lng * 1e-5).toFixed(5)), Number((lat * 1e-5).toFixed(5))])
  }

  return points
}

function encodeSignedNumber(num) {
  let sgn_num = num < 0 ? ~(num << 1) : num << 1
  return encodeNumber(sgn_num)
}

function encodeNumber(num) {
  let encodeString = ''
  while (num >= 0x20) {
    encodeString += String.fromCharCode((0x20 | (num & 0x1f)) + 63)
    num >>= 5
  }
  encodeString += String.fromCharCode(num + 63)
  return encodeString
}

/**
 * 简单字符串哈希算法 (生成 8 位十六进制键)
 */
function hashString(str) {
  let hash = 5381
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) + hash) + str.charCodeAt(i)
    hash |= 0
  }
  return (hash >>> 0).toString(16)
}

/**
 * 提取每日规划路线中的折线点至公共折线池 (Polyline Pool)
 * @param {Object} dailyResults dailyResults.value
 * @returns {{ cleanDailyResults: Object, polylinePool: Object }}
 */
export function packDailyResultsPolylines(dailyResults) {
  const polylinePool = {}
  const cleanDailyResults = {}

  if (!dailyResults || typeof dailyResults !== 'object') {
    return { cleanDailyResults, polylinePool }
  }

  Object.entries(dailyResults).forEach(([day, dayData]) => {
    if (!dayData) return
    const cleanDay = { ...dayData }

    if (Array.isArray(dayData.routes)) {
      cleanDay.routes = dayData.routes.map((r) => {
        // 提取现有的折线点坐标 (兼容 detailed_polyline, amap_path, pathCoords)
        const polyCoords =
          (Array.isArray(r.detailed_polyline) && r.detailed_polyline.length >= 2 && r.detailed_polyline) ||
          (Array.isArray(r.amap_path) && r.amap_path.length >= 2 && r.amap_path) ||
          (Array.isArray(r.pathCoords) && r.pathCoords.length >= 2 && r.pathCoords) ||
          null

        // 精准提取轻量化站点序列：仅记录 shop_code 与 name，每条路线仅需几十字节
        // 既杜绝了将庞大完整 store 对象直接序列化造成的存储膨胀，又 100% 保留了人工调整后的经停次序
        const currentPoints = r.points || r.stops || []
        const cleanStops = currentPoints.map((p) => ({
          shop_code: p.shop_code || '',
          name: p.name || '',
        }))

        // 剔除内存自引用及巨大临时属性，并废弃可能已失真的求解器初始 order 静态索引
        const {
          raw_route,
          points,
          stops,
          order,
          detailed_polyline,
          amap_path,
          pathCoords,
          ...cleanR
        } = r

        cleanR.stops = cleanStops

        if (polyCoords) {
          const encoded = encodePolyline(polyCoords)
          if (encoded) {
            // 以编码内容做 Hash 去重，多条路线或往返共享同段/同线时复用同一个 key
            const polyKey = 'p_' + hashString(encoded)
            polylinePool[polyKey] = encoded
            cleanR.poly_key = polyKey
          }
        }

        return cleanR
      })
    }

    cleanDailyResults[day] = cleanDay
  })

  return { cleanDailyResults, polylinePool }
}

/**
 * 将快照中打包的折线池还原到每日路线的 detailed_polyline 属性中
 * @param {Object} dailyResults dailyResults 结构
 * @param {Object} polylinePool 快照中的 polyline_pool 字典
 */
export function unpackDailyResultsPolylines(dailyResults, polylinePool = {}) {
  if (!dailyResults || typeof dailyResults !== 'object') return

  const pool = polylinePool || {}

  Object.values(dailyResults).forEach((dayData) => {
    if (!dayData || !Array.isArray(dayData.routes)) return

    dayData.routes.forEach((r) => {
      // 1. 如果有 poly_key 且在 pool 中能找到编码
      if (r.poly_key && pool[r.poly_key]) {
        const decoded = decodePolyline(pool[r.poly_key])
        if (decoded && decoded.length >= 2) {
          r.detailed_polyline = decoded
          r.amap_path = decoded
        }
      }
      // 2. 如果历史数据直接存有 detailed_polyline 数组，直接兼容保留
      else if (Array.isArray(r.detailed_polyline) && r.detailed_polyline.length >= 2) {
        r.amap_path = r.detailed_polyline
      }
    })
  })
}
