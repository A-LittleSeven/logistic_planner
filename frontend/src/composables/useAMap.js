import { ref } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import { systemApi } from '../api/client.js'

/** 响应式密钥版本号，当高德 Key 变更时自增，通知 MapPanel 等地图组件自动重新初始化 */
export const aMapKeyVersion = ref(0)

export function getAMapConfig() {
  const customKey = typeof localStorage !== 'undefined' ? localStorage.getItem('AMAP_USER_KEY') : null
  const defaultKey = import.meta.env.VITE_AMAP_KEY || ''

  const isCustom = !!(customKey && customKey.trim())
  const key = isCustom ? customKey.trim() : defaultKey

  return {
    key,
    isCustom,
    customKey: isCustom ? customKey.trim() : '',
    defaultKey
  }
}

let initConfigPromise = null

/** 异步初始化高德配置单例，避免顶层调用与 loadAMap 产生竞态 */
export function initAMapConfig() {
  if (!initConfigPromise) {
    initConfigPromise = fetchAMapConfigFromBackend().catch((err) => {
      console.warn('Failed to initialize AMap config from backend:', err)
      return getAMapConfig()
    })
  }
  return initConfigPromise
}

/** 从后端 SQLite 数据库获取高德配置并同步到本地 (仅同步 Key，安全密钥由后端代理托管) */
export async function fetchAMapConfigFromBackend() {
  try {
    const data = await systemApi.getAmapConfig()
    if (data.is_custom && data.amap_key) {
      saveAMapConfig(data.amap_key)
      return data
    } else {
      resetAMapConfig()
      return {
        amap_key: '',
        amap_secret: '',
        amap_secret_md5: '',
        is_custom: false,
        has_secret: !!data.has_secret,
        message: '使用系统内置默认高德配置'
      }
    }
  } catch (err) {
    console.warn('Failed to fetch AMap config from SQLite backend:', err)
  }
  return getAMapConfig()
}

/** 保存配置到后端 SQLite 并同步 Key */
export async function saveAMapConfigToBackend(key, security) {
  const data = await systemApi.saveAmapConfig({ amap_key: key || '', amap_secret: security || '' })
  if (data.is_custom && data.amap_key) {
    saveAMapConfig(data.amap_key)
  } else {
    resetAMapConfig()
  }
  return data
}

/** 重置 AMapLoader 状态并清理注入的脚本，允许切换 Key 后重新加载 */
export function resetAMapLoader() {
  if (typeof AMapLoader !== 'undefined' && typeof AMapLoader.reset === 'function') {
    try {
      AMapLoader.reset()
    } catch (e) {
      console.warn('AMapLoader reset error:', e)
    }
  }
  if (typeof document !== 'undefined') {
    const oldScripts = document.querySelectorAll('script[src*="webapi.amap.com/maps"]')
    oldScripts.forEach((s) => s.parentNode && s.parentNode.removeChild(s))
  }
  AMapPromise = null
  aMapKeyVersion.value++
}

export function saveAMapConfig(key) {
  const prevKey = getAMapConfig().key
  const newKey = (key || '').trim()

  if (newKey) {
    localStorage.setItem('AMAP_USER_KEY', newKey)
  } else {
    localStorage.removeItem('AMAP_USER_KEY')
  }
  // 安全加固：彻底清除本地存储中的明文安全密钥
  localStorage.removeItem('AMAP_USER_SECURITY')

  // 若 Key 发生变动且已加载过地图，重置 Loader 并触发地图刷新
  if (prevKey !== newKey || AMapPromise) {
    resetAMapLoader()
  }
  ensureAMapSecurityConfig()
}

export function resetAMapConfig() {
  localStorage.removeItem('AMAP_USER_KEY')
  localStorage.removeItem('AMAP_USER_SECURITY')
  resetAMapLoader()
  ensureAMapSecurityConfig()
}

/** 高德 JS API 2.0 官方安全代理规范配置：前端统一使用 serviceHost 转发，杜绝密钥泄露 */
function ensureAMapSecurityConfig() {
  if (typeof window !== 'undefined') {
    window._AMapSecurityConfig = {
      serviceHost: `${window.location.origin}/_AMapService`,
    }
  }
}

// 初始化时主动清理可能存在的历史本地明文密钥
if (typeof localStorage !== 'undefined') {
  localStorage.removeItem('AMAP_USER_SECURITY')
}
ensureAMapSecurityConfig()

// 启动时尽早发起初始化请求（受控 Promise 单例，供 loadAMap 等待）
initAMapConfig()

let AMapPromise = null

/** 加载高德 JS API, 返回 AMap 命名空间 (单例, 失败可重试)。确保等待后端配置同步完成 */
export async function loadAMap() {
  // 核心修复：必须先等待后端配置加载完成，避免竞态导致使用过期的默认 Key
  await initAMapConfig()

  if (!AMapPromise) {
    const config = getAMapConfig()
    ensureAMapSecurityConfig()
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

/** 测试指定的 AMap Key 连通性 (若为空则测试当前生效的密钥) */
export async function testAMapConnection(testKey) {
  const config = getAMapConfig()
  const effectiveKey = (testKey && testKey.trim()) ? testKey.trim() : config.key

  if (!effectiveKey) {
    throw new Error('未找到可用高德 Key，请检查环境配置或输入自定义 Key')
  }

  const startTime = Date.now()
  ensureAMapSecurityConfig()
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
              info: 'API 验证通过，Key 与后端安全代理匹配正常！'
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
      reject(new Error((err && err.message) || '高德 JS API 加载失败，请检查 Key 或网络连接'))
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
    aMapKeyVersion,
    initAMapConfig,
    resetAMapLoader
  }
}
