<template>
  <!-- 悬浮于地图左上角的门店搜索框: 按名称/编号过滤, 选中后 emit('select', { ...store, index }) -->
  <div class="map-store-search">
    <el-autocomplete
      v-model="keyword"
      :fetch-suggestions="querySearch"
      placeholder="搜索门店名称或编号"
      @select="(item) => emit('select', item)"
      value-key="name"
      style="width: 100%"
      clearable
      :trigger-on-focus="false"
    >
      <template #default="{ item }">
        <div style="font-weight: 600; font-size: 13px;">{{ item.name }}</div>
        <div style="font-size: 11px; color: #64748b; margin-top: 2px;">
          编号: {{ item.shop_code || '无' }} | 序号: {{ item.index + 1 }}
        </div>
      </template>
    </el-autocomplete>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  // 门店数组, 元素需含 name / shop_code (弹窗联动还需 lng / lat)
  stores: { type: Array, default: () => [] },
})

const emit = defineEmits(['select'])

const keyword = ref('')

const querySearch = (queryString, cb) => {
  const all = props.stores.map((p, idx) => ({ ...p, index: idx }))
  const results = queryString
    ? all.filter((s) => {
        const q = queryString.toLowerCase()
        return (s.name && s.name.toLowerCase().includes(q)) ||
          (s.shop_code && s.shop_code.toLowerCase().includes(q))
      })
    : all
  cb(results)
}
</script>

<style scoped>
.map-store-search {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 100;
  width: 320px;
  background: white;
  padding: 8px;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}
</style>
