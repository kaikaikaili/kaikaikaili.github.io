<template>
  <div>
    <div v-if="loading" class="loading">加载回测数据（约 10 秒）...</div>
    <template v-else-if="data">
      <h2>📊 穿越式回测仪表盘</h2>
      <p class="subtitle">
        HOME_ADV = {{ data.home_advantage }} ·
        样本 {{ data.total_matches }} 场 ·
        全部零未来信息（每场只使用当时已结束的数据）
      </p>

      <!-- 总览卡片 -->
      <div class="summary">
        <div class="sum-card">
          <div class="sum-label">五大联赛平均命中率</div>
          <div class="sum-val big">{{ top5AvgHit }}%</div>
        </div>
        <div class="sum-card">
          <div class="sum-label">五大联赛平均 Brier</div>
          <div class="sum-val big">{{ top5AvgBrier }}</div>
          <div class="sum-ref">参考 0.55-0.65</div>
        </div>
        <div class="sum-card">
          <div class="sum-label">覆盖联赛</div>
          <div class="sum-val big">{{ data.leagues.length }}</div>
        </div>
        <div class="sum-card">
          <div class="sum-label">总回测场次</div>
          <div class="sum-val big">{{ data.total_matches }}</div>
        </div>
      </div>

      <!-- 图表区 -->
      <div class="grid-2" v-if="data">
        <div class="card">
          <h3>🏆 各联赛命中率</h3>
          <div ref="hitChart" style="width:100%;height:340px"></div>
        </div>
        <div class="card">
          <h3>📈 各联赛 Brier Score</h3>
          <div ref="brierChart" style="width:100%;height:340px"></div>
        </div>
      </div>

      <!-- 明细表 -->
      <div class="card full">
        <h3>📋 详细数据</h3>
        <table class="league-table">
          <thead>
            <tr>
              <th>联赛</th>
              <th>场次</th>
              <th>命中率</th>
              <th>Brier</th>
              <th>平局命中</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="l in sortedLeagues" :key="l.league">
              <td><strong>{{ l.league_name }}</strong></td>
              <td>{{ l.matches }}</td>
              <td>{{ l.hit_rate }}%</td>
              <td>
                <span :class="brierClass(l.brier)">{{ l.brier }}</span>
              </td>
              <td>{{ l.draw_hit_rate }}% ({{ l.draw_hit }}/{{ l.draw_total }})</td>
            </tr>
          </tbody>
        </table>
        <p class="ref-note">{{ data.disclaimer }}</p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
// ECharts 通过 CDN 引入（index.html 里），这里用全局变量
const echarts = window.echarts

const data = ref(null)
const loading = ref(true)
const hitChart = ref(null)
const brierChart = ref(null)

const TOP5 = ['英超', '西甲', '意甲', '德甲', '法甲']

const sortedLeagues = computed(() =>
  [...(data.value?.leagues || [])].sort((a, b) => b.hit_rate - a.hit_rate)
)

const top5AvgHit = computed(() => {
  const ls = (data.value?.leagues || []).filter(l => TOP5.includes(l.league_name))
  if (!ls.length) return '-'
  return (ls.reduce((a, b) => a + b.hit_rate, 0) / ls.length).toFixed(1)
})
const top5AvgBrier = computed(() => {
  const ls = (data.value?.leagues || []).filter(l => TOP5.includes(l.league_name))
  if (!ls.length) return '-'
  return (ls.reduce((a, b) => a + b.brier, 0) / ls.length).toFixed(4)
})

onMounted(async () => {
  try {
    const r = await fetch('/data/backtest.json')
    data.value = await r.json()
  } finally { loading.value = false }
})

// 等 data 有值 + DOM 更新后渲染图表（hash 路由时序差问题）
watch(data, async () => {
  for (let i = 0; i < 5; i++) {
    await nextTick()
    if (hitChart.value && brierChart.value) {
      renderCharts()
      return
    }
    await new Promise(r => setTimeout(r, 50))
  }
}, { flush: 'post' })

function renderCharts() {
  if (!hitChart.value || !brierChart.value) return
  const leagues = sortedLeagues.value

  const hit = echarts.init(hitChart.value, 'dark')
  hit.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: leagues.map(l => l.league_name), axisLabel: { color: '#94a3b8', rotate: 20 } },
    yAxis: { type: 'value', min: 35, max: 60, axisLabel: { color: '#64748b', formatter: '{value}%' }, splitLine: { lineStyle: { color: '#1e293b' } } },
    series: [{
      type: 'bar', barWidth: '50%',
      data: leagues.map(l => ({
        value: l.hit_rate,
        itemStyle: { color: l.hit_rate >= 47 ? '#4ade80' : l.hit_rate >= 43 ? '#38bdf8' : '#fbbf24', borderRadius: [4,4,0,0] },
      })),
      label: { show: true, position: 'top', color: '#e2e8f0', formatter: '{c}%' },
    }],
  })

  const bri = echarts.init(brierChart.value, 'dark')
  bri.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: leagues.map(l => l.league_name), axisLabel: { color: '#94a3b8', rotate: 20 } },
    yAxis: { type: 'value', min: 0.55, max: 0.72, axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: '#1e293b' } } },
    series: [{
      type: 'bar', barWidth: '50%',
      data: leagues.map(l => ({
        value: l.brier,
        itemStyle: { color: l.brier <= 0.65 ? '#4ade80' : l.brier <= 0.68 ? '#38bdf8' : '#f87171', borderRadius: [4,4,0,0] },
      })),
      label: { show: true, position: 'top', color: '#e2e8f0', formatter: '{c}' },
    }],
  })

  window.addEventListener('resize', () => { hit.resize(); bri.resize() })
}

function brierClass(b) {
  if (b <= 0.65) return 'good'
  if (b <= 0.68) return 'ok'
  return 'bad'
}
</script>

<style scoped>
.loading { text-align: center; padding: 60px; color: #64748b; font-size: 16px; }
h2 { margin-bottom: 8px; color: #38bdf8; }
.subtitle { color: #64748b; font-size: 13px; margin-bottom: 24px; }

.summary {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;
}
@media (max-width: 800px) { .summary { grid-template-columns: repeat(2, 1fr); } }
.sum-card {
  background: #1e293b; border: 1px solid #334155; border-radius: 12px;
  padding: 20px; text-align: center;
}
.sum-label { font-size: 12px; color: #64748b; margin-bottom: 8px; }
.sum-val { font-size: 22px; font-weight: 700; color: #e2e8f0; }
.sum-val.big { font-size: 32px; color: #38bdf8; }
.sum-ref { font-size: 11px; color: #64748b; margin-top: 4px; }

.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
@media (max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }
.card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; }
.card.full { margin-bottom: 20px; }
.card h3 { margin-bottom: 12px; color: #38bdf8; font-size: 15px; }

.league-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.league-table th, .league-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #334155; }
.league-table th { color: #64748b; font-weight: 500; font-size: 12px; text-transform: uppercase; }
.brier.good { color: #4ade80; font-weight: 600; }
.brier.ok { color: #fbbf24; }
.brier.bad { color: #f87171; }
.ref-note { margin-top: 16px; color: #64748b; font-size: 12px; }
</style>
