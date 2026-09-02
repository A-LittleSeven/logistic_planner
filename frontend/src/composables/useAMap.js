import AMapLoader from '@amap/amap-jsapi-loader'
import { systemApi } from '../api/client.js'

export function getAMapConfig() {
  const customKey = localStorage.getItem('AMAP_USER_KEY')
  const customSecurity = localStorage.getItem('AMAP_USER_SECURITY')
  const defaultKey = import.meta.env.VITE_AMAP_KEY || ''
  const defaultSecurity = import.meta.env.VITE_AMAP_SECURITY || ''

  const isCustom = !!(customKey && customKey.trim())
  const key = isCustom ? customKey.trim() : defaultKey
  const security = isCustom ? customSecurity.trim() : defaultSecurity

  return {
    key,
    security,
    isCustom,
    customKey: isCustom ? customKey.trim() : '',
    customSecurity: isCustom ? customSecurity.trim() : '',
    defaultKey,
    defaultSecurity
  }
}

/** 从后端 SQLite 数据库获取高德配置并同步到本地 */
export async function fetchAMapConfigFromBackend() {
  try {
    const data = await systemApi.getAmapConfig()
    if (data.is_custom && data.amap_key && data.amap_secret) {
      saveAMapConfig(data.amap_key, data.amap_secret)
      return data
    } else {
      resetAMapConfig()
      return {
        amap_key: '',
        amap_secret: '',
        amap_secret_md5: '',
        is_custom: false,
        message: '使用系统内置默认高德配置'
      }
    }
  } catch (err) {
    console.warn('Failed to fetch AMap config from SQLite backend:', err)
  }
  return getAMapConfig()
}

/** 保存配置到后端 SQLite 并同步 MD5 密文摘要 */
export async function saveAMapConfigToBackend(key, security) {
  const data = await systemApi.saveAmapConfig({ amap_key: key || '', amap_secret: security || '' })
  if (data.is_custom && data.amap_key && data.amap_secret) {
    saveAMapConfig(data.amap_key, data.amap_secret)
  } else {
    resetAMapConfig()
  }
  return data
}

/** 恢复后端 SQLite 默认配置 (保留底层方法供需要时调用) */
export async function resetAMapConfigOnBackend() {
  try {
    await systemApi.resetAmapConfig()
  } catch (err) {
    console.warn('Reset on backend failed:', err)
  }
  resetAMapConfig()
  return getAMapConfig()
}

export function saveAMapConfig(key, security) {
  if (key && key.trim()) {
    localStorage.setItem('AMAP_USER_KEY', key.trim())
  } else {
    localStorage.removeItem('AMAP_USER_KEY')
  }
  if (security && security.trim()) {
    localStorage.setItem('AMAP_USER_SECURITY', security.trim())
  } else {
    localStorage.removeItem('AMAP_USER_SECURITY')
  }

  // Reset loader singleton so subsequent calls load with new key
  AMapPromise = null
  const config = getAMapConfig()
  window._AMapSecurityConfig = {
    securityJsCode: config.security,
  }
}

export function resetAMapConfig() {
  localStorage.removeItem('AMAP_USER_KEY')
  localStorage.removeItem('AMAP_USER_SECURITY')
  AMapPromise = null
  const config = getAMapConfig()
  window._AMapSecurityConfig = {
    securityJsCode: config.security,
  }
}

// 启动时静默从 SQLite 校验并加载配置
fetchAMapConfigFromBackend()

// 安全密钥必须在 loader 加载前设置 (高德 JS API 2.0 要求)
const initialConfig = getAMapConfig()
window._AMapSecurityConfig = {
  securityJsCode: initialConfig.security,
}

let AMapPromise = null

/** 加载高德 JS API, 返回 AMap 命名空间 (单例, 失败可重试)。 */
export function loadAMap() {
  if (!AMapPromise) {
    const config = getAMapConfig()
    window._AMapSecurityConfig = {
      securityJsCode: config.security,
    }
    AMapPromise = AMapLoader.load({
      key: config.key,
      version: '2.0',
      plugins: ['AMap.Scale', 'AMap.ToolBar', 'AMap.Geocoder', 'AMap.AutoComplete', 'AMap.TruckDriving', 'AMap.Driving'],
    }).catch((err) => {
      AMapPromise = null // 失败后允许下次重试
      throw err
    })
  }
  return AMapPromise
}

/** 测试指定的 AMap Key 和 Secret 连通性 (若为空则测试当前生效的密钥) */
export async function testAMapConnection(testKey, testSecurity) {
  const config = getAMapConfig()
  const effectiveKey = (testKey && testKey.trim()) ? testKey.trim() : config.key
  const effectiveSecurity = (testSecurity && testSecurity.trim()) ? testSecurity.trim() : config.security

  if (!effectiveKey) {
    throw new Error('未找到可用高德 Key，请检查环境配置或输入自定义 Key')
  }

  const startTime = Date.now()
  window._AMapSecurityConfig = {
    securityJsCode: effectiveSecurity || '',
  }
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      reject(new Error('高德 API 连接测试超时 (超过 8 秒)，请检查网络或 Key 有效性'))
    }, 8000)

    AMapLoader.load({
      key: effectiveKey,
      version: '2.0',
      plugins: ['AMap.Geocoder'],
    }).then((AMap) => {
      AMap.plugin('AMap.Geocoder', () => {
        const geocoder = new AMap.Geocoder({ city: '全国' })
        // Test with standard coordinates (Nanning depot)
        geocoder.getAddress([108.318344, 22.846367], (status, result) => {
          clearTimeout(timeout)
          const latency = Date.now() - startTime
          if (status === 'complete' && result && result.regeocode) {
            resolve({
              success: true,
              latency,
              address: result.regeocode.formattedAddress || '测试地址识别成功',
              info: 'API 验证通过，Key 与 Security Secret 匹配正常！'
            })
          } else {
            // Some keys may have geocode quota issues, but if AMap was loaded successfully:
            resolve({
              success: true,
              latency,
              address: '',
              info: '高德 JS API 核心库加载成功！'
            })
          }
        })
      })
    }).catch((err) => {
      clearTimeout(timeout)
      reject(new Error((err && err.message) || '高德 JS API 加载失败，请检查 Key 或 Secret 是否填写正确'))
    })
  })
}

/** 经纬度逆地理编码识别物理地址 */
export async function getAddressByCoords(lng, lat) {
  if (!lng || !lat) return ''
  const AMap = await loadAMap()
  return new Promise((resolve, reject) => {
    AMap.plugin('AMap.Geocoder', () => {
      const geocoder = new AMap.Geocoder({
        city: '全国'
      })
      geocoder.getAddress([Number(lng), Number(lat)], (status, result) => {
        if (status === 'complete' && result.regeocode) {
          resolve(result.regeocode.formattedAddress || '')
        } else {
          resolve('')
        }
      })
    })
  })
}

/**
 * 高德货车路径规划 (AMap.TruckDriving) 测算真实路网路线与行驶距离
 * 自动处理途经点分段、格式转换、货车规划降级与超时保护
 * @param {Array<number>} origin 起点经纬度 [lng, lat]
 * @param {Array<number>} destination 终点经纬度 [lng, lat]
 * @param {Array<Array<number>>} waypoints 途经点经纬度列表 [[lng, lat], ...]
 * @param {Object} truckOptions 车型参数 (默认4.2米厢式货车)
 */
export async function planTruckDrivingRoute(origin, destination, waypoints = [], truckOptions = {}) {
  const AMap = await loadAMap()
  return new Promise((resolve, reject) => {
    // 整体 15 秒超时保护，防止 Promise 挂起
    const overallTimer = setTimeout(() => {
      reject(new Error('高德路线规划请求超时，请检查网络或高德Key'))
    }, 15000)

    AMap.plugin(['AMap.TruckDriving', 'AMap.Driving'], () => {
      const defaultOptions = {
        policy: 1, // 0: 速度优先, 1: 距离优先, 2: 避免收费
        size: 2, // 车型大小: 1:微型车, 2:轻型车(4.2米厢式货车), 3:中型车, 4:重型车
        width: 2.1,
        height: 2.8,
        load: 4.5,
        weight: 2.0,
        axlesNum: 2,
        province: '桂',
        ...truckOptions
      }

      // 解析 routes[0] 得到规范结果
      const extractResult = (r) => {
        const coords = []
        if (r.steps && r.steps.length > 0) {
          r.steps.forEach(step => {
            if (step.path && step.path.length > 0) {
              step.path.forEach(p => {
                const lng = typeof p.getLng === 'function' ? p.getLng() : p[0] || p.lng
                const lat = typeof p.getLat === 'function' ? p.getLat() : p[1] || p.lat
                coords.push([Number(lng), Number(lat)])
              })
            }
          })
        }
        return {
          distance: r.distance || 0, // meters
          time: r.time || 0, // seconds
          tolls: r.tolls || 0, // CNY
          path: coords
        }
      }

      // 单段搜索：优先 TruckDriving，失败降级为 Driving
      const performSearch = (start, end, midPoints = []) => {
        return new Promise((res, rej) => {
          let hasSettled = false
          const segTimer = setTimeout(() => {
            if (!hasSettled) {
              hasSettled = true
              rej(new Error('高德单段路径规划响应超时'))
            }
          }, 8000)

          // 构造标准 pathList 数组格式: [{ lnglat: [lng, lat] }, ...]
          const pathList = [
            { lnglat: [Number(start[0]), Number(start[1])] },
            ...midPoints.map(pt => ({ lnglat: [Number(pt[0]), Number(pt[1])] })),
            { lnglat: [Number(end[0]), Number(end[1])] }
          ]

          try {
            const truckDriving = new AMap.TruckDriving(defaultOptions)
            truckDriving.search(pathList, (status, result) => {
              if (hasSettled) return
              clearTimeout(segTimer)

              if (status === 'complete' && result && result.routes && result.routes.length > 0) {
                hasSettled = true
                res(extractResult(result.routes[0]))
              } else {
                // 若货车规划不可用（如无权限/无货车道路），无缝降级为标准驾车规划 AMap.Driving
                console.warn('TruckDriving search fallback to Driving:', status, result)
                try {
                  const driving = new AMap.Driving({ policy: 1 })
                  const originLngLat = new AMap.LngLat(Number(start[0]), Number(start[1]))
                  const destLngLat = new AMap.LngLat(Number(end[0]), Number(end[1]))
                  const waypointsLngLat = midPoints.map(pt => new AMap.LngLat(Number(pt[0]), Number(pt[1])))

                  driving.search(originLngLat, destLngLat, { waypoints: waypointsLngLat }, (drvStatus, drvResult) => {
                    if (hasSettled) return
                    if (drvStatus === 'complete' && drvResult && drvResult.routes && drvResult.routes.length > 0) {
                      hasSettled = true
                      res(extractResult(drvResult.routes[0]))
                    } else {
                      hasSettled = true
                      rej(new Error((drvResult && drvResult.info) || (result && result.info) || '路径规划无匹配路线'))
                    }
                  })
                } catch (drvErr) {
                  hasSettled = true
                  rej(drvErr)
                }
              }
            })
          } catch (truckErr) {
            console.warn('TruckDriving init failed, fallback to Driving:', truckErr)
            try {
              const driving = new AMap.Driving({ policy: 1 })
              const originLngLat = new AMap.LngLat(Number(start[0]), Number(start[1]))
              const destLngLat = new AMap.LngLat(Number(end[0]), Number(end[1]))
              const waypointsLngLat = midPoints.map(pt => new AMap.LngLat(Number(pt[0]), Number(pt[1])))

              driving.search(originLngLat, destLngLat, { waypoints: waypointsLngLat }, (drvStatus, drvResult) => {
                if (hasSettled) return
                clearTimeout(segTimer)
                hasSettled = true
                if (drvStatus === 'complete' && drvResult && drvResult.routes && drvResult.routes.length > 0) {
                  res(extractResult(drvResult.routes[0]))
                } else {
                  rej(new Error((drvResult && drvResult.info) || '驾车路径规划失败'))
                }
              })
            } catch (fallbackErr) {
              if (!hasSettled) {
                hasSettled = true
                clearTimeout(segTimer)
                rej(fallbackErr)
              }
            }
          }
        })
      }

      const runSegmented = async () => {
        try {
          if (waypoints.length <= 16) {
            const singleRes = await performSearch(origin, destination, waypoints)
            clearTimeout(overallTimer)
            resolve(singleRes)
            return
          }

          // 途经点大于16个时分段规划并无缝拼接
          let totalDistance = 0
          let totalTime = 0
          let totalTolls = 0
          let combinedPath = []
          const chunkSize = 16

          for (let i = 0; i < waypoints.length; i += chunkSize) {
            const isFirst = i === 0
            const isLast = i + chunkSize >= waypoints.length
            const segStart = isFirst ? origin : waypoints[i - 1]
            const segEnd = isLast ? destination : waypoints[i + chunkSize - 1]
            const segWaypoints = waypoints.slice(i, isLast ? waypoints.length : i + chunkSize - 1)

            const segRes = await performSearch(segStart, segEnd, segWaypoints)
            totalDistance += segRes.distance
            totalTime += segRes.time
            totalTolls += segRes.tolls
            if (combinedPath.length > 0 && segRes.path.length > 0) {
              combinedPath = combinedPath.concat(segRes.path.slice(1))
            } else {
              combinedPath = combinedPath.concat(segRes.path)
            }
          }

          clearTimeout(overallTimer)
          resolve({
            distance: totalDistance,
            time: totalTime,
            tolls: totalTolls,
            path: combinedPath
          })
        } catch (err) {
          clearTimeout(overallTimer)
          reject(err)
        }
      }

      runSegmented()
    })
  })
}

export function useAMap() {
  return {
    loadAMap,
    getAddressByCoords,
    planTruckDrivingRoute,
    getAMapConfig,
    saveAMapConfig,
    resetAMapConfig,
    testAMapConnection,
    fetchAMapConfigFromBackend,
    saveAMapConfigToBackend,
    resetAMapConfigOnBackend
  }
}
