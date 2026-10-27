# logistic_planner 项目问题审查报告

> 审查范围：backend/ 全部 55 个 Python 源文件（~6,300 行）逐文件审查；frontend/ 全部核心组件/composables/utils 逐文件审查（StatCard/AppPageHeader/DepotManage/VehicleManage/theme.css 仅交叉引用验证）。
> 分级：P0 = 功能断裂/安全风险，P1 = 重要缺陷，P2 = 重构建议。

---

# 第一部分：P0 严重问题（功能不可用 / 安全）

## 后端

### P0-B1 全周全局路线规划接口端到端死路
- `backend/app/services/plan_service.py:150` 取 `routing_registry.get("global_optimization")`，但 `app/solvers/routing_solver.py:162-163` 只注册了 `"ortools"` 和 `"savings_vrp"`，全仓库无人注册 `"global_optimization"`。
- 影响：`POST /api/routing/solve_global` 必然报"未注册的求解器"。前端 `client.js:19` 的 `solveGlobal` 也无调用方——前后端双向死代码。

### P0-B2 保存排班方案接口必然 500
- `backend/app/services/plan_service.py:373/381` 访问 `req.work_days`、`req.daily_stats`，但 `SaveScheduleRequest`（`ClusteringDTO.py:101-106`）只定义了 title/depot_name/depot_lng/depot_lat/points 五个字段。
- AttributeError 发生在 try 块之外 → 500。前端 `client.js:28` 的 `saveSchedule` 同样无调用方。

### P0-B3 排班结果字段被 response_model 静默丢弃
- `backend/app/api/clustering_router.py:47` 声明 `response_model=ScheduleSolveResponse`，该模型（`ClusteringDTO.py:85-86`）只有 `points` 字段；`schedule_solver.py:181-185` 返回的 `daily_stats`/`total_stores` 被 Pydantic 过滤，前端永远收不到每日汇总。

### P0-B4 detour_thres 单位混乱，"距离保护"形同虚设
- `backend/app/core/optimizer/truck_schedule.py:33`：默认参数 40，`None` 分支给 100（死代码）；`:243` 用法 `dist_high <= dist_min * self.detour_thres` 把阈值当**乘数**——允许绕行到最近距离 40 倍的门店；`schedule_solver.py:57` 又默认传 500。与 `route_replanner` 的绝对阈值（35km）同名不同义，约束实际完全失效。

### P0-B5 高德密钥明文入库 + 无鉴权回传
- `backend/app/api/system_router.py:21-28`：GET 接口将 `amap_secret` 明文返回给任何调用方（系统无鉴权）；`:65` 的 MD5 仅为展示摘要，密钥本体明文存储于 `db/models.py:95`。"MD5 加密"是安全错觉。

## 前端

### P0-F1 CanvasListView 运行时报错
- `frontend/src/views/canvas/CanvasListView.vue:57,64`：`@input/@change="filterCanvases"` 引用了不存在的函数（script 里只有 computed `filteredCanvases`）。搜索框每次输入都抛 `filterCanvases is not defined`（搜索本身靠 computed 隐式生效，但 handler 每次报错）。

### P0-F2 密钥三路明文暴露
- `useAMap.js:5-23,70-98`：①`VITE_AMAP_SECURITY` 编译进 dist bundle（明文）；②明文存 localStorage（XSS 可读）；③后端把 secret 明文回传并填进表单（`SystemSettings.vue:299-302`）。未使用 AMap JSAPI 2.0 官方 proxy/白名单安全方案。与 P0-B5 合并为同一密钥安全问题。

### P0-F3 坐标系混用导致系统性偏移 ✅ 已修复 (2026-10-27)
- ~~`excelImport.js:324,848`：模板文案声称支持"高德 GCJ-02 或 WGS84"，但解析层无任何转换~~
- 修复：新增 `frontend/src/utils/coordSystem.js`（wgs84ToGcj02/gcj02ToWgs84 转换、haversineMeters、validateCoordinatePoints 静态校验、detectCoordinateSystemByAddress 地址编码自动检测）；`excelImport.js` 支持 `coordSystem` 选项并在解析时转换 + 静态校验（范围/中国域/经纬度互换/度分格式），同时修复了原始表头透传覆盖数值坐标的隐患；`StoreManage.vue` 导入对话框新增坐标系选择（GCJ-02 默认 / WGS-84）与"自动检测坐标系"按钮（抽样地址经高德 Geocoder 编码比对，多数投票判定，检出 WGS-84 自动切换重解析）。
- `excelImport.js:324,848`：模板文案声称支持"高德 GCJ-02 或 WGS84"，但解析层无任何转换，WGS84 数据直接进入 AMap 渲染与货车路网测算 → 全图几百米系统性偏移、路径起终点错误，无告警。

### P0-F4 模块顶层副作用竞态
- `useAMap.js:101`：import 时 fire-and-forget 执行 `fetchAMapConfigFromBackend()`，与 `loadAMap()` 竞态；key 更新后 `AMapPromise=null` 只对后续加载生效，已创建的 Map 实例（`MapPanel.vue:36`）仍用旧 key，无刷新机制。

### P0-F5 MapPanel 失败后永久挂起
- `MapPanel.vue:46-48,59-64`：onMounted catch 只设 error，不清空/拒绝 readyResolvers；`await whenReady()`（`CanvasWorkspaceView.vue:414`、`useCanvasMapLayers.js:431-433`）无限 pending，后续 renderMap 静默不执行，无用户提示。

---

# 第二部分：P1 重要问题

## 后端
| # | 位置 | 问题 |
|---|------|------|
| P1-B1 | `plan_service.py:82` | 为补一个字段全表 `db.query(DBStore).all()`，应按 shop_code IN 查询 |
| P1-B2 | `canvas_service.py:108-129` | `list_canvases` N+1（每画布 2 次额外 SQL）+ 循环 json.loads 完整快照只为算统计；快照版本表无清理 → **logistic.db 已达 1.4 GB** |
| P1-B3 | `master_data_service.py:141-155` | batch_import 中途 IntegrityError 后失败 session 继续被复用，可能整体静默失败；`:72-73` `except: continue` 吞掉所有行级错误 |
| P1-B4 | `constrained_kmeans_cluster.py:266` | `pd.merge` inner join，空簇/孤儿标签**静默丢门店行**；三个聚类器 join 方式不一致（district_cluster.py:33 无 how，district_extension_cluster.py:78 用 left）；`:260` 核心算法 print() 绕过 logger |
| P1-B5 | `constrained_kmeans_cluster.py:177-212` | 局部搜索 O(100·n²·k)，几百门店即分钟级且在同步路由线程执行，阻塞 worker |
| P1-B6 | `truck_schedule.py:114/130` | `unplanned_store` 只取 `clusters[0]`（逻辑错）且唯一调用方丢弃返回值 |
| P1-B7 | `schedule_solver.py:28-34,113-144` | frequency>2 门店被剔出车辆路线规划，选日子时完全不看装载容量，运力是否够用从未校验 |
| P1-B8 | `plan_service.py:266,291` | `execute_schedule` 的 provider 参数传入后完全没用，排班算法硬编码 haversine，依赖注入对排班失效 |
| P1-B9 | `utils/distance.py:38-43` | `.env` 宣传 amap_webservice 路网距离，实际对任何非 haversine 值静默降级直线距离；README 声称的 AMap 距离实现与 NN+2-opt 求解器均不存在 |
| P1-B10 | `canvas_service.py:76-88,190` | get_current_version 不校验版本归属（可指向孤儿版本）；`:190` 可能把 None 存进 current_version_id |
| P1-B11 | `plan_service.py:47-60` | `_record_task_history` 失败后未 rollback，失败事务污染请求级 session |
| P1-B12 | `history_router.py:43-45`、`store_router.py:66-68` | `/clear/all` 一键清库无鉴权无确认，项目已具备 Docker 部署条件 |

## 前端
| # | 位置 | 问题 |
|---|------|------|
| P1-F6 | `RoutingStage.vue:244-327` | 全周规划串行 7 次 solve 无取消/守卫，切画布后回调仍写入已卸载组件状态；中途失败留下"半成品方案"且 isRoutingOutdated 仍 true，UI 矛盾 |
| P1-F7 | `SchedulingStage.vue:229-238`、`ClusteringStage.vue:179` | 按数组下标直写 stores，假设后端点序严格同序，无 shop_code 校验；后端一旦重排即整批错位 |
| P1-F8 | `StoreManage.vue:106` vs `useCanvasMapLayers.js:173` 等 | 店群编号 0/1-based 不一致：门店维护页显示原值，画布侧全部 +1，同数据两页编号差 1 |
| P1-F9 | `StoreManage.vue:533-540` | 严格等值过滤 `===`，excelImport（:225-229 原始表头透传）产生的字符串类型永远滤不出 Number |
| P1-F10 | `useCanvasVersioning.js:359-373` | `dangerouslyUseHTMLString` 拼接未转义的 change_summary（mapMarkers.js:30 有转义、此处漏用），存储型 XSS 注入 |
| P1-F11 | `useCanvasMapLayers.js:308-309` | 渲染函数内回写 `p.frequency`，渲染产生状态变异并随快照持久化 |
| P1-F12 | `useCanvasMapLayers.js:442-466` | 任何交互全量 clearAll+重建 N 个 Marker+InfoWindow（每店一个 InfoWindow），500 店点一次下拉即重建 1000 个对象；无 MarkerClusterer |
| P1-F13 | 多处 | 批量测算串行 +350ms 间隔最坏 ~7 分钟不可取消；`RoutingStage.vue:220-235` 双向 watch 使用户关掉汇总卡即清空持久化摘要 |

---

# 第三部分：P2 重构建议

## 3.1 死代码清单（全仓库 grep 确认零引用）
**后端**：`VehicleDO.py:104` set_supported_truck_classes、`StoreDO.py:85` find_nearest_freq_store、`ClusterDO.py:22-36` 四个方法、`StoreDO.py:48-62` 四个坐标别名 property、`distance.py:75` calc_distance + manhattan/euclidean、`routing_solver.py:32-38` count_270/count_230、`route_replanner.py:8` 顶层重复导入、`core/__init__.py:34-45` 整个惰性导出兼容层、RoutingDTO 的 GlobalRoutingSolveResponse/DailyRoutingResult。

**前端**：client.js 的 solveGlobal/savePlan×2/algorithms×2/getDefault/storeApi.get/vehicleApi.get；`useRouteOptimizer.js:306` moveStoreOrder（RoutingStage.vue:452-474 手写了同样逻辑）；`SystemSettings.vue:271` resetAMapConfigOnBackend、:256 Refresh/ElMessageBox 导入未用；`StoreManage.vue:723-729` handleTemplateDownload、:422 ArrowDown；`RoutePlanList.vue:253` 未用图标导入、props.allRoutes 与 routes 同引用等价无用。

## 3.2 重复实现（缺单一事实源）
- 排班模式枚举 ×2：`useCanvasMapLayers.js:41-77` vs `SchedulingStage.vue:148-182`（同一业务规则两份硬编码）。
- Excel 导出/模板 ×4：StoreManage.vue:731-904、CanvasListView.vue:373-446、historyExport.js、useRouteExport.js；is_homepot 判断在 historyExport.js:92,169,382 重复 3 次。
- getStageLabel ×2（useCanvasVersioning.js:68-76 vs CanvasListView.vue:340-355，后者多 FINALIZED——已经分叉）。
- 颜色表 ×3：mapMarkers.js / RoutePlanList.vue:376 / ClusterResultList.vue:66。
- 时长格式化 ×2：historyExport.js:349-358 手写 vs constants.js:3 formatDuration；时间格式化 ×3。
- 路线距离累计 ×3（route_replanner / VehicleDO.calc_truck_distance / RouteOptimizer.local_route_optimize）。
- is_homepot 提取 ×3 且默认值不一致（聚类链路默认本埠=1，路线链路默认外埠=0）。
- depot 提取 validator 在 ClusteringDTO.py:33-45 与 :72-82 逐字重复；plan_service 三个 save_*_plan 相同 CRUD 样板。
- 南宁坐标硬编码散布后端 6 处 + 前端 useAMap.js:157、useCanvasState.js:25-26、useRouteMeasure.js:37-38。

## 3.3 函数入参出参问题（对应第 5 问）
- `truck_schedule.py:33` detour_thres None 分支死代码（见 P0-B4）。
- `route_replanner._plan_routes_for_group` 默认参数与唯一调用方两处维护已分叉（1.1 vs 1.0）；`plan_daily_routes_with_or:80` 装载率上限 1.1 允许物理超载 10%，命名与语义冲突。
- `execute_schedule` 的 provider 参数被丢弃（P1-B8）。
- `ConstrainedKmeansCluster.__init__` 的 max_iter/tol 无调用方传入（恒默认）；`soft_capacity` 恒 20 且无处可配。
- `ModelConverter.normalize_coordinates` 与前端 `useAMap.js:187` 均用 falsy 判断，合法 0 经度被当缺失。
- `RouteConfigDialog.vue:77,83` / `ScheduleConfigDialog.vue:93,99`：localStorage 只 setItem 无 getItem，"保存参数"刷新即失忆，用户被误导。
- 前端按 `shop_code||name` 匹配同步快递状态（useCanvasState.js:51-54 等），重名门店会串改。

## 3.4 结构与 God component（对应第 3、4 问）
**后端**：
- `models/do/VehicleDO.py`（402 行）BaseTruck 上帝类：状态机+车型注册表+别名解析+动态类工厂+主数据加载五种职责；`TRUCK_ALIAS_MAP` 模块级可变全局，每次请求追加动态类，**跨请求无限增长（内存泄漏）**。
- `canvas_service.py`（536 行）单类管 CRUD+版本+回滚+克隆+统计聚合。
- 分层总体清晰：api → services → solvers → core，无循环依赖，solver 不碰 DB（✓）；例外：`plan_service.py:283-287` 把 ORM 对象塞进 options 走私给 solver。

**前端**（≥500 行组件 9 个）：
- `StoreManage.vue`(1003)：≈6 职责（统计+筛选+表格+编辑+导入解析预览+3 套模板导出），最应拆分。
- `SystemSettings.vue`(705)：半数静态文案；"系统引擎状态卡"(134-181) 是写死"运行正常"的假数据，建议删。
- `CanvasListView.vue`(752)：模板下载(L373-446 纯数据)必抽。
- `RoutePlanList.vue`(811)：职责集中但同时服务"列表展示+编辑器"双角色，可拆。
- `CanvasWorkspaceView.vue`(742)：结构好（壳+编排），但 :324-408 的 InfoWindow 内联 onclick 走 `window.*` 全局桥是状态流旁路暗道——绕过 provide/inject、多实例即崩。
- `CreateCanvasWizardDialog.vue`(649) 职责清晰可接受。

## 3.5 仓库/配置卫生
- `main.py:27` import 时 create_all，无 Alembic 迁移，加列在旧库直接报错。
- logistic.db 1.4 GB（快照表无 TTL/上限）；backend/.venv 内 3.10 与 3.12 双 site-packages 并存。
- `task_id = uuid4().int % 1e10`（plan_service.py:185）碰撞即 500。
- CORS `*` 与 allow_credentials=True 可组成非法组合，config 未防。
- README 大面积过时：/clustering/*、/routing/* 页面已不存在，声称的 amap_webservice 距离与 NN+2-opt 均不存在。
- 前端：client.js 全局 10 分钟 timeout；main.js 全量注册 ElementPlus 图标（tree-shaking 失效）；MapPanel 默认中心北京与南宁业务不符（首帧跳变）；`province:'桂'`、'9050' 兜底等硬编码。

---

# 第四部分：整体结论（对应你的五个问题）

1. **功能正确性**：后端 3 个契约断裂端点（P0-B1/2/3）+ 前端 1 个必报错 handler（P0-F1），说明缺少任何端到端冒烟测试；排班链路的距离保护（P0-B4）、高频店运力校验（P1-B7）、坐标系（P0-F3）是语义级缺陷。
2. **代码复用**：距离累计、is_homepot、排班模式、颜色表、Excel 导出等核心业务规则均 2~4 份并存，且多处已经分叉（getStageLabel、默认值 1.1 vs 1.0）——这是最可能产生数据错乱的维护风险。
3. **结构规划**：后端 api→services→solvers→core 分层方向正确、无循环依赖；前端 canvas 的 composables/stages 拆分是亮点；主要债务是 VehicleDO 上帝类（含内存泄漏）、window.* 旁路暗道、9 个 500+ 行组件。
4. **God component**：最严重为 VehicleDO.BaseTruck（后端）与 StoreManage.vue（前端，6 职责）。
5. **入参出参**：存在参数被丢弃（provider）、默认值两处分叉、返回值无人消费（unplanned_store、daily_stats）、response_model 静默裁剪、localStorage 只写不读、按索引/按 name 的脆弱对位等多例。

**亮点**（值得保留的设计）：polylineCompressor（差值编码+公共折线池治理快照膨胀）、invalidateDownstreamStages 级联失效、TruckIdAllocator 的 contextvar 并发隔离、registry 求解器注册表模式、ModelConverter 三态转换收敛。

**建议修复顺序**：P0-B1/B2/B3（各 10 分钟）→ P0-F1 → 密钥方案（P0-B5+F2）→ 坐标系策略（P0-F3）→ MapPanel 挂起（P0-F5）→ 排班语义（P0-B4/P1-B7）→ 1.4GB db 治理（P1-B2）→ 死代码与重复实现清理 → 组件拆分。
