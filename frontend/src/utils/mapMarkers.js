// 星期常量与标准统一配色
export const DAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

export const DAY_COLORS = {
  '周一': '#3b82f6', // 亮蓝
  '周二': '#10b981', // 翡翠绿
  '周三': '#ef4444', // 鲜红
  '周四': '#f59e0b', // 琥珀橙
  '周五': '#8b5cf6', // 罗兰紫
  '周六': '#ec4899', // 玫瑰粉
  '周日': '#06b6d4', // 青蓝
}

// 簇配色 (取自主题点缀色)
export const CLUSTER_COLORS = [
  '#2563eb', '#f59e0b', '#14b8a6', '#8b5cf6',
  '#f43f5e', '#0ea5e9', '#84cc16', '#ec4899',
]

// 路线配色
export const ROUTE_COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6',
  '#ef4444', '#06b6d4', '#ec4899', '#f97316',
  '#14b8a6', '#6366f1', '#84cc16', '#a855f7'
]

/**
 * 安全转义 HTML 特殊字符，防范地图气泡/弹窗模板中的 XSS 注入
 */
export function escapeHtml(str) {
  if (str === null || str === undefined) return ''
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}



/**
 * 圆形标记。color 可为纯色或 CSS 渐变字符串。
 * 返回 { content, offset } 供 AMap.Marker 使用。
 * 支持文本长度自适应计算，确保长文本在不改变圆圈尺寸的前提下完美居中不溢出。
 */
export function dotHtml({ text = '', color = '#3b82f6', size = 22, textColor = '#fff' }) {
  const half = size / 2
  const str = String(text)

  // 自适应字号与字间距智能计算 (保持圆圈原始 size 不变)
  let fontSize = Math.round(size * 0.5) // 默认 11px
  let letterSpacing = 'normal'
  let transform = ''

  if (str.length === 2) {
    fontSize = Math.round(size * 0.46) // ~10px
  } else if (str.length === 3) {
    fontSize = Math.round(size * 0.38) // ~8.5px
    letterSpacing = '-0.5px'
  } else if (str.length === 4) {
    fontSize = Math.round(size * 0.32) // ~7px
    letterSpacing = '-0.8px'
  } else if (str.length >= 5) {
    fontSize = Math.round(size * 0.28) // ~6px
    letterSpacing = '-1px'
    transform = 'transform: scale(0.92);'
  }

  return {
    content:
      `<div style="width:${size}px;height:${size}px;border-radius:50%;` +
      `background:${color};border:2px solid #ffffff;box-shadow:0 2px 6px rgba(0,0,0,0.28);` +
      `display:flex;align-items:center;justify-content:center;color:${textColor};` +
      `font-size:${fontSize}px;font-weight:700;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC',system-ui,sans-serif;` +
      `letter-spacing:${letterSpacing};${transform}white-space:nowrap;overflow:hidden;box-sizing:border-box;line-height:1;text-align:center;">${escapeHtml(str)}</div>`,
    offset: [-half, -half],
  }
}
