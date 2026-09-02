# 前端 (Vue 3 + Vite)

## 启动

```bash
cd frontend
npm install
cp .env.example .env          # 必填 VITE_AMAP_KEY 和 VITE_AMAP_SECURITY
npm run dev
```

访问 http://localhost:5173

构建生产包：`npm run build`，预览：`npm run preview`。

## 环境变量 (.env)

| 变量 | 说明 |
| --- | --- |
| `VITE_AMAP_KEY` | 高德 JS API key（Web 端类型），必填 |
| `VITE_AMAP_SECURITY` | 高德 JS API 安全密钥 (jscode)，必填 |
| `VITE_API_BASE` | 后端基址；开发时 Vite 已代理 `/api`，留空即可 |

## 结构

```
src/
├── api/client.js           # axios 实例 + 三模块接口函数
├── composables/useAMap.js  # 高德 JS API 加载 (单例)
├── components/
│   ├── AppHeader.vue       # 顶部导航 (渐变)
│   ├── ViewLayout.vue      # 左面板 + 右地图 布局
│   ├── PointTable.vue      # 可编辑点表 (v-model)
│   ├── ExcelImportButton.vue # Excel 批量导入按钮 (反馈自包含)
│   ├── MapPanel.vue        # 地图容器 + overlay 管理
│   └── ResultCard.vue      # 结果卡片
├── views/
│   ├── LocationView.vue    # 物流选址
│   ├── RoutingView.vue     # 路线规划
│   └── ClusteringView.vue  # 店群规划
├── utils/
│   ├── mapMarkers.js       # 地图标记 HTML 构造 + 簇配色
│   └── excelImport.js      # Excel 解析 (表头匹配/容错, 纯函数可测)
├── styles/theme.css        # 主题 (对齐参考站风格)
├── router.js
└── main.js
```

## 交互

- 三个子菜单均支持：表格手动增删点、地图点击取点、「示例数据」一键演示、「清空」。
- 计算结果在左侧结果卡展示，同时在地图上可视化（标记/折线/聚类着色）。
