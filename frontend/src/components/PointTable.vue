<template>
  <div class="point-table">
    <table class="lp-table">
      <thead>
        <tr>
          <th class="col-idx">#</th>
          <th v-for="col in columns" :key="col.key" :style="{ width: col.width }">
            {{ col.label }}
          </th>
          <th class="col-op"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, idx) in modelValue" :key="idx">
          <td class="row-idx">{{ idx + 1 }}</td>
          <td v-for="col in columns" :key="col.key">
            <slot :name="'cell-' + col.key" :row="row" :idx="idx" :col="col" :update="v => updateCell(idx, col.key, v)">
              <input
                v-if="col.type === 'checkbox'"
                type="checkbox"
                :checked="row[col.key]"
                :disabled="col.readonly"
                @change="updateCell(idx, col.key, $event.target.checked)"
              />
              <input
                v-else
                :type="col.type || 'text'"
                :value="row[col.key]"
                :placeholder="col.placeholder || ''"
                :disabled="col.readonly"
                @input="updateCell(idx, col.key, parseValue(col, $event.target.value))"
              />
            </slot>
          </td>
          <td>
            <button class="row-del" @click="remove(idx)" title="删除">×</button>
          </td>
        </tr>
        <tr v-if="!modelValue.length">
          <td :colspan="columns.length + 2" class="lp-empty">
            暂无点，点击下方"添加点"或在地图上点击取点
          </td>
        </tr>
      </tbody>
    </table>
    <button class="lp-btn lp-btn--ghost add-btn" @click="add">+ 添加点</button>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: Array, required: true },
  columns: { type: Array, required: true }, // [{key,label,type,width,placeholder}]
  defaultRow: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'add', 'remove'])

function parseValue(col, v) {
  return col.type === 'number' ? (v === '' ? '' : Number(v)) : v
}

function updateCell(idx, key, value) {
  const next = props.modelValue.map((r, i) => (i === idx ? { ...r, [key]: value } : r))
  emit('update:modelValue', next)
}

function add() {
  emit('add')
}

function remove(idx) {
  emit('remove', idx)
}
</script>

<style scoped>
.point-table {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.col-idx {
  width: 36px;
}
.col-op {
  width: 44px;
}
.row-idx {
  color: var(--text-light);
  font-size: 12px;
}
.row-del {
  border: none;
  background: transparent;
  color: var(--text-light);
  font-size: 18px;
  line-height: 1;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  transition: var(--transition);
}
.row-del:hover {
  background: #fff1f2;
  color: var(--accent-rose);
}
.add-btn {
  align-self: flex-start;
}
</style>
