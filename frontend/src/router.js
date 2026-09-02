import { createRouter, createWebHistory, createWebHashHistory } from 'vue-router'
import Layout from './layout/Layout.vue'

// Assuming existing views will be moved/adapted. For now, referencing them or creating placeholders.
import StoreManage from './views/config/StoreManage.vue'
import VehicleManage from './views/config/VehicleManage.vue'
import DepotManage from './views/config/DepotManage.vue'
import HistoryView from './views/history/HistoryView.vue'

import RoutingView from './views/RoutingView.vue'
import ClusteringView from './views/ClusteringView.vue'
import ClusterSchedulingView from './views/ClusterSchedulingView.vue'
import SystemSettings from './views/settings/SystemSettings.vue'
import CanvasListView from './views/canvas/CanvasListView.vue'
import CanvasWorkspaceView from './views/canvas/CanvasWorkspaceView.vue'

const routes = [
  { path: '/', redirect: '/canvas' },
  {
    path: '/',
    component: Layout,
    children: [
      { path: 'canvas', name: 'canvas_list', component: CanvasListView, meta: { title: '规划画布' } },
      { path: 'canvas/workspace/:id', name: 'canvas_workspace', component: CanvasWorkspaceView, meta: { title: '画布工作台' } },
      { path: 'history', name: 'history', component: HistoryView, meta: { title: '历史记录' } },

      { path: 'config/store', name: 'store', component: StoreManage, meta: { title: '门店维护' } },
      { path: 'config/vehicle', name: 'vehicle', component: VehicleManage, meta: { title: '车型维护' } },
      { path: 'config/depot', name: 'depot', component: DepotManage, meta: { title: '起点管理' } },
      
      { path: 'clustering/plan', name: 'clustering', component: ClusteringView, meta: { title: '门店分组' } },
      { path: 'clustering/schedule', name: 'schedule', component: ClusterSchedulingView, meta: { title: '门店排班' } },

      { path: 'routing/plan', name: 'routing', component: RoutingView, meta: { title: '路线规划' } },

      { path: 'settings', name: 'settings', component: SystemSettings, meta: { title: '系统设置' } },
    ]
  }
]

const router = createRouter({
  // Electron 使用 Hash 模式，开发模式使用 History 模式
  history: window.electronAPI ? createWebHashHistory() : createWebHistory(),
  routes,
})

router.afterEach((to) => {
  document.title = `${to.meta?.title ?? '物流规划'} | 智能物流调度系统`
})

export default router
