import { createRouter, createWebHistory } from 'vue-router'
import Layout from './layout/Layout.vue'

const routes = [
  { path: '/', redirect: '/canvas' },
  {
    path: '/',
    component: Layout,
    children: [
      { path: 'canvas', name: 'canvas_list', component: () => import('./views/canvas/CanvasListView.vue'), meta: { title: '规划画布' } },
      { path: 'canvas/workspace/:id', name: 'canvas_workspace', component: () => import('./views/canvas/CanvasWorkspaceView.vue'), meta: { title: '画布工作台' } },
      { path: 'history', name: 'history', component: () => import('./views/history/HistoryView.vue'), meta: { title: '历史记录' } },

      { path: 'config/store', name: 'store', component: () => import('./views/config/StoreManage.vue'), meta: { title: '门店维护' } },
      { path: 'config/vehicle', name: 'vehicle', component: () => import('./views/config/VehicleManage.vue'), meta: { title: '车型维护' } },
      { path: 'config/depot', name: 'depot', component: () => import('./views/config/DepotManage.vue'), meta: { title: '起点管理' } },

      { path: 'settings', name: 'settings', component: () => import('./views/settings/SystemSettings.vue'), meta: { title: '系统设置' } },
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  document.title = `${to.meta?.title ?? '物流规划'} | 智能物流调度系统`
})

export default router
