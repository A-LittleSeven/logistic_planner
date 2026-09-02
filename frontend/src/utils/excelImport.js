// Excel & CSV 批量导入解析引擎 (使用 XLSX + 智能表头映射与编码自适应)
import * as XLSX from 'xlsx'

// 表头别名映射表 (不区分大小写，自动去空格与下划线)
const FIELD_ALIASES = {
  shop_code: ['shop_code', 'shopcode', 'dept_id', 'deptid', 'code', 'store_code', 'storecode', '门店编号', '门店代码', '编号', '客户编号'],
  name: ['name', 'shop_name', 'shopname', 'store_name', 'storename', '名称', '门店名称', '门店', '点名称', '客户名称'],
  dept_id: ['dept_id', 'deptid', '部门id', '部门编号', '部门'],
  district: ['district', '行政区划', '行政区', '区域', '所属区域', '区县'],
  district_sub: ['district_sub', '区划细分', '街道', '区县细分'],
  city_name: ['city_name', 'city', '城市', '城市名称', '市'],
  warzone: ['warzone', '战区', '片区', '所属战区'],
  lng: ['lng', 'longitude', 'store_lon', 'lon', 'x', '经度', '门店经度', '中心经度'],
  lat: ['lat', 'latitude', 'store_lat', 'y', '纬度', '门店纬度', '中心纬度'],
  avg_loads: ['avg_loads', 'avgloads', 'weight', 'loads', 'demand', '需求量', '需求', '箱数', '日均箱数', '运量', '货物量'],
  frequency: ['frequency', 'freq', '配送频次', '频次', '周频次', '配送次数'],
  is_homepot: ['is_homepot', 'ishomepot', '本埠', '是否本埠', '是否本埠门店', '本外埠'],
  service_time: ['service_time', 'servicetime', 'dist_time', 'disttime', '服务时间', '卸货时间', '卸货耗时'],
  available_truck: ['dis_way', 'disway', 'available_truck', 'availabletruck', 'truck', '指定车型', '可用车型', '车型', '配送车型', '车型要求'],
  address: ['address', '详细地址', '地址', '门牌号', '位置'],
  is_depot: ['is_depot', 'depot', '是否仓库', '是否配送中心'],
  warehouse_name: ['warehouse_name', 'warehouse', 'dc_code', 'dccode', '仓库', '所属仓库', '仓库名称', '中心仓', '中心仓库', '所属DC', '仓库编码'],
  cluster_id: ['cluster_id', 'cluster', '店群', '聚类', '所属店群', '店群id', 'assignments', 'cluster_center_id'],
  delivery_days_str: [
    'delivery_days_str', 'delivery_days', 'deliverydays', 'deliverydaysstr', 'days', 'schedule_days', 'scheduledays',
    '计划配送作业日', '配送作业日', '排班作业日', '作业日', '排班日', '送货日', '配送日', '送货周期', '排班结果', '作业排班'
  ],
  is_express: [
    'is_express', 'isexpress', 'express', '是否快递', '快递', '配送方式', '物流方式', '发货方式', '运输方式', '物流类型', '配送模式', '快递直发'
  ]
}

const DEPOT_TRUTHY = new Set(['是', 'true', '1', 'y', 'yes', '✓', '√', 't', 1])

const cleanStr = (val) => {
  if (val === null || val === undefined) return ''
  return String(val).trim()
}

const normalizeHeader = (header) => {
  return cleanStr(header).toLowerCase().replace(/[\s_\-\.\(\)（）]/g, '')
}

/**
 * 智能匹配表头索引
 */
function buildColumnIndexMap(headers) {
  const normalizedHeaders = headers.map(normalizeHeader)
  const colIndex = {}

  for (const [field, aliases] of Object.entries(FIELD_ALIASES)) {
    const aliasNormSet = new Set(aliases.map(normalizeHeader))
    const foundIdx = normalizedHeaders.findIndex(h => h && aliasNormSet.has(h))
    if (foundIdx >= 0) {
      colIndex[field] = foundIdx
    }
  }

  return colIndex
}

/**
 * 将解析出的二维数据映射为规范的 StoreNode 属性点集合
 */
export function map2DArrayToStores(rows) {
  const warnings = []
  if (!rows || rows.length < 2) {
    return { points: [], warnings: ['文件为空或无有效数据行'] }
  }

  const rawHeaders = rows[0].map(cleanStr)
  const colMap = buildColumnIndexMap(rawHeaders)

  if (colMap.lng === undefined || colMap.lat === undefined) {
    return {
      points: [],
      warnings: ['未能识别到“经度 (lng/longitude)”或“纬度 (lat/latitude)”列，请检查表头名称']
    }
  }

  const points = []

  for (let r = 1; r < rows.length; r++) {
    const row = rows[r]
    if (!row || row.every(c => c === null || c === undefined || String(c).trim() === '')) {
      continue // 跳过空行
    }

    const lngRaw = row[colMap.lng]
    const latRaw = row[colMap.lat]

    if (lngRaw === null || lngRaw === undefined || lngRaw === '' || latRaw === null || latRaw === undefined || latRaw === '') {
      warnings.push(`第 ${r + 1} 行经纬度缺失，已自动跳过`)
      continue
    }

    const lng = Number(lngRaw)
    const lat = Number(latRaw)

    if (isNaN(lng) || isNaN(lat) || !isFinite(lng) || !isFinite(lat)) {
      warnings.push(`第 ${r + 1} 行经纬度包含非数字字符，已自动跳过`)
      continue
    }

    // 提取字段
    const shopCode = colMap.shop_code !== undefined ? cleanStr(row[colMap.shop_code]) : ''
    const deptId = colMap.dept_id !== undefined ? cleanStr(row[colMap.dept_id]) : ''
    const finalCode = shopCode || deptId || `STORE_${r}`

    const nameRaw = colMap.name !== undefined ? cleanStr(row[colMap.name]) : ''
    const finalName = nameRaw || `门店_${finalCode}`

    const district = colMap.district !== undefined ? cleanStr(row[colMap.district]) : ''
    const districtSub = colMap.district_sub !== undefined ? cleanStr(row[colMap.district_sub]) : ''
    const cityName = colMap.city_name !== undefined ? cleanStr(row[colMap.city_name]) : ''
    const warzone = colMap.warzone !== undefined ? cleanStr(row[colMap.warzone]) : ''

    // 日均箱数 / 需求量
    let avgLoads = 10.0
    if (colMap.avg_loads !== undefined && row[colMap.avg_loads] !== '' && !isNaN(Number(row[colMap.avg_loads]))) {
      avgLoads = Number(row[colMap.avg_loads])
    }

    // 本埠 / 外埠 (1=本埠, 0=外埠，若未提供列则默认本埠 1)
    let isHomepot = 1
    if (colMap.is_homepot !== undefined) {
      const hVal = row[colMap.is_homepot]
      if (hVal !== null && hVal !== undefined && hVal !== '') {
        const normH = String(hVal).trim().toLowerCase()
        if (normH === '0' || normH === '否' || normH === '外埠' || normH === 'false') {
          isHomepot = 0
        } else if (normH === '1' || normH === '是' || normH === '本埠' || normH === 'true') {
          isHomepot = 1
        }
      }
    }

    // 是否快递直发 (1=快递, 0=常规货车)
    let isExpress = 0
    if (colMap.is_express !== undefined) {
      const eVal = row[colMap.is_express]
      if (eVal !== null && eVal !== undefined && eVal !== '') {
        const normE = String(eVal).trim().toLowerCase()
        if (normE.includes('快递') || normE.includes('express') || normE === '1' || normE === '是' || normE === 'true' || normE.includes('直发')) {
          isExpress = 1
        }
      }
    }

    // 服务时间 (小时)
    let serviceTime = 0.65
    if (colMap.service_time !== undefined && row[colMap.service_time] !== '' && !isNaN(Number(row[colMap.service_time]))) {
      const rawTime = Number(row[colMap.service_time])
      // 如果大于 5，很可能是分钟 (如 40min)，自动换算为小时
      serviceTime = rawTime > 5 ? Number((rawTime / 60).toFixed(2)) : rawTime
    }

    // 车型
    const truck = colMap.available_truck !== undefined ? cleanStr(row[colMap.available_truck]) : ''

    // 详细地址组合
    let address = colMap.address !== undefined ? cleanStr(row[colMap.address]) : ''
    if (!address && (cityName || district || districtSub)) {
      address = `${cityName}${district}${districtSub}`
    }

    // 所属仓库 / 中心仓
    const warehouseName = colMap.warehouse_name !== undefined ? cleanStr(row[colMap.warehouse_name]) : ''

    // 所属店群 / 聚类结果 (cluster_id)
    let clusterId = undefined
    if (colMap.cluster_id !== undefined && row[colMap.cluster_id] !== '' && row[colMap.cluster_id] !== null && row[colMap.cluster_id] !== undefined) {
      const rawCluster = String(row[colMap.cluster_id]).trim()
      const numMatch = rawCluster.match(/\d+/)
      if (numMatch) {
        clusterId = parseInt(numMatch[0], 10)
      } else if (rawCluster) {
        clusterId = rawCluster
      }
    }

    // 计划配送作业日 (delivery_days_str)
    let deliveryDaysStr = ''
    if (colMap.delivery_days_str !== undefined && row[colMap.delivery_days_str] !== '' && row[colMap.delivery_days_str] !== null && row[colMap.delivery_days_str] !== undefined) {
      deliveryDaysStr = cleanStr(row[colMap.delivery_days_str])
        .replace(/[，、；;\/|]/g, ',')
        .replace(/\s+/g, '')
    }

    // 配送频次 (若提供了排班作业日则以作业日天数为基准自动同步)
    const daysArr = deliveryDaysStr ? deliveryDaysStr.split(',').filter(Boolean) : []
    let frequency = daysArr.length > 0 ? daysArr.length : 1
    if (colMap.frequency !== undefined && row[colMap.frequency] !== '' && !isNaN(Number(row[colMap.frequency]))) {
      const parsedFreq = Math.max(1, Math.min(7, Math.round(Number(row[colMap.frequency]))))
      frequency = daysArr.length > 0 ? Math.max(parsedFreq, daysArr.length) : parsedFreq
    }

    const pt = {
      shop_code: finalCode,
      name: finalName,
      dept_id: deptId || finalCode,
      district: district || districtSub || cityName || '',
      warzone,
      lng,
      lat,
      longitude: lng,
      latitude: lat,
      avg_loads: avgLoads,
      weight: avgLoads,
      frequency,
      is_homepot: isHomepot,
      service_time: serviceTime,
      available_truck: truck,
      address,
      warehouse_name: warehouseName,
      dc_code: warehouseName,
      cluster_center_id: clusterId,
      cluster_id: clusterId,
      delivery_days_str: deliveryDaysStr,
      is_express: isExpress,
      store_is_need_dist: true,
    }

    // 保存所有原始属性用于通用透传
    rawHeaders.forEach((h, cIdx) => {
      if (h && row[cIdx] !== undefined && row[cIdx] !== null) {
        pt[h] = cleanStr(row[cIdx])
      }
    })

    points.push(pt)
  }

  // 智能自适应规范化 cluster_id (确保全系统内部统一为 0-based 编号: 0, 1, 2...)
  const validClusterPoints = points.filter(p => p.cluster_id !== undefined && p.cluster_id !== null && p.cluster_id !== '')
  if (validClusterPoints.length > 0) {
    const rawClusterVals = Array.from(new Set(validClusterPoints.map(p => p.cluster_id)))
    const numericVals = rawClusterVals.map(v => Number(v)).filter(v => !isNaN(v))

    if (numericVals.length === rawClusterVals.length) {
      const minVal = Math.min(...numericVals)
      // 如果最小值为 1 (典型 1-indexed 导出或人工输入 1, 2, 3...)，统一减 1 转为 0-indexed
      if (minVal === 1) {
        points.forEach(p => {
          if (p.cluster_id !== undefined && p.cluster_id !== null && p.cluster_id !== '') {
            const num = Number(p.cluster_id)
            if (!isNaN(num)) {
              p.cluster_id = num - 1
              p.cluster_center_id = num - 1
            }
          }
        })
      } else if (minVal > 1) {
        // 如果是从非 0 非 1 开始 (如 101, 102)，按顺序重映射为 0, 1, 2...
        const sortedVals = Array.from(new Set(numericVals)).sort((a, b) => a - b)
        const idMap = new Map(sortedVals.map((v, i) => [v, i]))
        points.forEach(p => {
          if (p.cluster_id !== undefined && p.cluster_id !== null && p.cluster_id !== '') {
            const num = Number(p.cluster_id)
            if (idMap.has(num)) {
              p.cluster_id = idMap.get(num)
              p.cluster_center_id = idMap.get(num)
            }
          }
        })
      } else if (minVal === 0) {
        // 已经是 0-indexed，确保为数字类型
        points.forEach(p => {
          if (p.cluster_id !== undefined && p.cluster_id !== null && p.cluster_id !== '') {
            const num = Number(p.cluster_id)
            if (!isNaN(num)) {
              p.cluster_id = num
              p.cluster_center_id = num
            }
          }
        })
      }
    } else {
      // 含有非纯数字字符串店群标识
      const sortedVals = rawClusterVals.sort()
      const idMap = new Map(sortedVals.map((v, i) => [v, i]))
      points.forEach(p => {
        if (p.cluster_id !== undefined && p.cluster_id !== null && p.cluster_id !== '') {
          if (idMap.has(p.cluster_id)) {
            p.cluster_id = idMap.get(p.cluster_id)
            p.cluster_center_id = idMap.get(p.cluster_id)
          }
        }
      })
    }
  }

  return { points, warnings }
}

/**
 * 解析 Excel (.xlsx, .xls) 或 CSV 文件
 */
export async function parseFileUniversal(file) {
  const isCSV = file.name.toLowerCase().endsWith('.csv')

  if (isCSV) {
    return parseCSVFile(file)
  } else {
    return parseExcelFile(file)
  }
}

export async function parseExcelFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target.result)
        const workbook = XLSX.read(data, { type: 'array' })
        const firstSheetName = workbook.SheetNames[0]
        if (!firstSheetName) {
          throw new Error('Excel 文件中未发现工作表 (Sheet)')
        }
        const worksheet = workbook.Sheets[firstSheetName]
        const rows = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: '' })
        resolve(map2DArrayToStores(rows))
      } catch (err) {
        reject(new Error('Excel 文件解析失败: ' + (err.message || err)))
      }
    }
    reader.onerror = () => reject(new Error('读取 Excel 文件失败'))
    reader.readAsArrayBuffer(file)
  })
}

export async function parseCSVFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const buffer = e.target.result
        let text = ''
        // 智能双编码解码 (优先尝试 UTF-8，若有编码错误则回退到 GBK/GB18030)
        try {
          const utf8Decoder = new TextDecoder('utf-8', { fatal: true })
          text = utf8Decoder.decode(buffer)
        } catch (decErr) {
          const gbkDecoder = new TextDecoder('gbk')
          text = gbkDecoder.decode(buffer)
        }

        const workbook = XLSX.read(text, { type: 'string' })
        const firstSheetName = workbook.SheetNames[0]
        const worksheet = workbook.Sheets[firstSheetName]
        const rows = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: '' })
        resolve(map2DArrayToStores(rows))
      } catch (err) {
        reject(new Error('CSV 文件解析失败: ' + (err.message || err)))
      }
    }
    reader.onerror = () => reject(new Error('读取 CSV 文件失败'))
    reader.readAsArrayBuffer(file)
  })
}
