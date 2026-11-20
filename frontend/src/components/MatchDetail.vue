<template>
  <div>
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <template v-else-if="data">
      <!-- 头部 -->
      <div class="detail-header">
        <a href="#/matches" class="back">← 返回赛程</a>
        <div class="match-big">
          <div class="team-big">{{ data.match.home_name }}</div>
          <div class="vs-big">
            <span class="league">{{ data.match.league_name }}</span>
            <span class="date">{{ fmtDate(data.match.match_date) }}</span>
            <span class="score-big" v-if="data.match.home_goals !== null">
              {{ data.match.home_goals }} - {{ data.match.away_goals }}
            </span>
            <span class="status-big" v-else>未开赛</span>
          </div>
          <div class="team-big">{{ data.match.away_name }}</div>
        </div>
      </div>

      <div class="grid-2">
        <!-- 预测面板 -->
        <div class="card">
          <h3>📊 泊松概率预测</h3>
          <div class="lambda-row">
            <div class="lambda">
              <span class="lambda-label">主队 λ</span>
              <span class="lambda-val">{{ data.prediction.lambda_home }}</span>
            </div>
            <div class="vs">vs</div>
            <div class="lambda">
              <span class="lambda-label">客队 λ</span>
              <span class="lambda-val">{{ data.prediction.lambda_away }}</span>
            </div>
          </div>
          <div class="league-avg">联赛场均进球 {{ data.prediction.league_avg_goals }}</div>

          <div class="prob-bars">
            <div class="prob-item">
              <span class="prob-label home">主胜</span>
              <div class="bar-wrap">
                <div class="bar home" :style="{width: data.prediction.home_win_prob*100+'%'}"></div>
              </div>
              <span class="prob-val">{{ (data.prediction.home_win_prob*100).toFixed(1) }}%</span>
            </div>
            <div class="prob-item">
              <span class="prob-label draw">平局</span>
              <div class="bar-wrap">
                <div class="bar draw" :style="{width: data.prediction.draw_prob*100+'%'}"></div>
              </div>
              <span class="prob-val">{{ (data.prediction.draw_prob*100).toFixed(1) }}%</span>
            </div>
            <div class="prob-item">
              <span class="prob-label away">客胜</span>
              <div class="bar-wrap">
                <div class="bar away" :style="{width: data.prediction.away_win_prob*100+'%'}"></div>
              </div>
              <span class="prob-val">{{ (data.prediction.away_win_prob*100).toFixed(1) }}%</span>
            </div>
          </div>

          <div v-if="hasPenalty" class="penalty-note">
            <span v-if="data.prediction.penalty_home?.star_absent_count">
              ⚠ {{ data.match.home_name }} 阵容惩罚 ×{{ data.prediction.penalty_home.penalty_factor }}
            </span>
            <span v-if="data.prediction.penalty_away?.star_absent_count">
              ⚠ {{ data.match.away_name }} 阵容惩罚 ×{{ data.prediction.penalty_away.penalty_factor }}
            </span>
          </div>

          <!-- 比分分布 ECharts -->
          <div ref="scoreChart" style="width:100%;height:280px;margin-top:16px"></div>
        </div>

        <!-- 近期战绩 -->
        <div class="card">
          <h3>📋 双方近期 5 场</h3>
          <div class="recent-block">
            <div class="recent-team">{{ data.match.home_name }}</div>
            <div v-for="(r, i) in data.home_recent" :key="i" class="recent-row">
              <span class="date-small">{{ fmtDate(r.match_date || r.date) }}</span>
              <span class="match-text">{{ r.home }} vs {{ r.away }}</span>
              <span class="result" :class="resultClass(r)">
                {{ r.home_goals }}-{{ r.away_goals }}
              </span>
            </div>
          </div>
          <div class="recent-block">
            <div class="recent-team">{{ data.match.away_name }}</div>
            <div v-for="(r, i) in data.away_recent" :key="i" class="recent-row">
              <span class="date-small">{{ fmtDate(r.match_date || r.date) }}</span>
              <span class="match-text">{{ r.home }} vs {{ r.away }}</span>
              <span class="result" :class="resultClass(r)">
                {{ r.home_goals }}-{{ r.away_goals }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 免责声明 -->
      <div class="mini-disclaimer">{{ data.disclaimer }}</div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
// ECharts 通过 CDN 引入（index.html 里），这里用全局变量
const echarts = window.echarts

const props = defineProps({ matchId: Number })
const data = ref(null)
const loading = ref(true)
const error = ref(null)
const scoreChart = ref(null)

const hasPenalty = computed(() => {
  const p = data.value?.prediction
  return p?.penalty_home?.star_absent_count || p?.penalty_away?.star_absent_count
})

onMounted(load)
watch(() => props.matchId, load)

// 单场详情：从 match_details.json 读取（静态文件，key 是 match_id 字符串）
const detailsCache = {}

async function load() {
  loading.value = true; error.value = null
  try {
    const key = String(props.matchId)
    if (!detailsCache[key]) {
      const r = await fetch('/data/match_details.json')
      detailsCache[key] = (await r.json())[key]
    }
    // 后端格式 → 前端期望格式（JSON 已经是扁平的了，直接赋值）
    data.value = detailsCache[key]
    if (!data.value) throw new Error('比赛不存在')
  } catch(e) { error.value = String(e) }
  finally { loading.value = false }
}

// watch data + retry（hash 路由时序差）
watch(data, async () => {
  for (let i = 0; i < 5; i++) {
    await nextTick()
    if (scoreChart.value) { renderChart(); return }
    await new Promise(r => setTimeout(r, 50))
  }
}, { flush: 'post' })

function renderChart() {
  if (!scoreChart.value || !data.value) return
  const chart = echarts.init(scoreChart.value, 'dark')
  const scores = data.value.prediction.top_scores
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, top: 10, bottom: 30 },
    xAxis: {
      type: 'category',
      data: scores.map(s => s.score),
      axisLabel: { color: '#94a3b8' },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#64748b', formatter: '{value}%' },
      splitLine: { lineStyle: { color: '#1e293b' } },
    },
    series: [{
      type: 'bar',
      data: scores.map(s => ({
        value: +(s.prob * 100).toFixed(1),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#38bdf8' }, { offset: 1, color: '#0c4a6e' }
          ]),
          borderRadius: [4, 4, 0, 0],
        },
      })),
      barWidth: '50%',
      label: { show: true, position: 'top', color: '#e2e8f0', formatter: '{c}%' },
    }],
  })
  window.addEventListener('resize', () => chart.resize())
}

function fmtDate(d) {
  if (!d) return ''
  const t = new Date(d)
  return `${t.getMonth()+1}/${t.getDate()}`
}
function resultClass(r) {
  // r.is_home=true 表示这支球队在那场里是主队
  const my_g = r.is_home ? r.home_goals : r.away_goals
  const opp_g = r.is_home ? r.away_goals : r.home_goals
  return my_g > opp_g ? 'win' : my_g < opp_g ? 'lose' : 'draw'
}
function resultText(r) {
  const my_g = r.is_home ? r.home_goals : r.away_goals
  const opp_g = r.is_home ? r.away_goals : r.home_goals
  return `${my_g}-${opp_g}`
}
</script>

<style scoped>
.loading, .error { text-align: center; padding: 60px; color: #64748b; }
.error { color: #f87171; }

.detail-header { margin-bottom: 24px; }
.back { color: #38bdf8; text-decoration: none; font-size: 13px; }
.back:hover { text-decoration: underline; }
.match-big {
  display: flex; justify-content: space-between; align-items: center;
  background: #1e293b; border: 1px solid #334155; border-radius: 16px;
  padding: 32px 48px; margin-top: 12px;
}
.team-big { font-size: 24px; font-weight: 700; flex: 1; text-align: center; }
.vs-big { text-align: center; color: #94a3b8; font-size: 14px; }
.score-big {
  display: block; font-size: 40px; font-weight: 800; color: #fbbf24; margin-top: 8px;
}
.status-big { display: block; margin-top: 8px; color: #64748b; }
.league { display: block; margin-bottom: 4px; }
.date { color: #64748b; }

.grid-2 {
  display: grid; grid-template-columns: 1fr 1fr; gap: 20px;
}
@media (max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }

.card {
  background: #1e293b; border: 1px solid #334155; border-radius: 12px;
  padding: 20px;
}
.card h3 { margin-bottom: 16px; color: #38bdf8; font-size: 16px; }

.lambda-row {
  display: flex; justify-content: space-between; align-items: center;
  background: #0f172a; border-radius: 10px; padding: 16px; margin-bottom: 4px;
}
.lambda { text-align: center; }
.lambda-label { display: block; font-size: 12px; color: #64748b; }
.lambda-val { font-size: 28px; font-weight: 700; color: #e2e8f0; }
.lambda-row .vs { color: #64748b; font-size: 13px; }
.league-avg { text-align: center; font-size: 12px; color: #64748b; margin-bottom: 16px; }

.prob-bars { display: flex; flex-direction: column; gap: 10px; }
.prob-item { display: flex; align-items: center; gap: 10px; }
.prob-label { width: 50px; font-size: 13px; font-weight: 500; text-align: right; }
.prob-label.home { color: #38bdf8; }
.prob-label.draw { color: #fbbf24; }
.prob-label.away { color: #f472b6; }
.bar-wrap { flex: 1; height: 18px; background: #0f172a; border-radius: 4px; overflow: hidden; }
.bar { height: 100%; border-radius: 4px; transition: width 0.5s; }
.bar.home { background: linear-gradient(90deg, #38bdf8, #0ea5e9); }
.bar.draw { background: linear-gradient(90deg, #fbbf24, #f59e0b); }
.bar.away { background: linear-gradient(90deg, #f472b6, #ec4899); }
.prob-val { width: 55px; font-size: 13px; font-weight: 600; }

.penalty-note {
  margin-top: 12px; font-size: 12px; color: #fbbf24; text-align: center;
}

.recent-block { margin-bottom: 16px; }
.recent-team { font-size: 14px; font-weight: 600; color: #38bdf8; margin-bottom: 8px; }
.recent-row {
  display: flex; gap: 10px; font-size: 12px; padding: 6px 0;
  border-bottom: 1px solid #334155;
}
.date-small { color: #64748b; width: 50px; }
.match-text { flex: 1; color: #cbd5e1; }
.result { font-weight: 600; width: 40px; text-align: right; }
.result.win { color: #4ade80; }
.result.lose { color: #f87171; }
.result.draw { color: #fbbf24; }

.mini-disclaimer {
  margin-top: 20px; text-align: center; color: #fbbf24;
  background: #422006; padding: 10px; border-radius: 8px; font-size: 12px;
}
</style>
