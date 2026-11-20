<template>
  <div>
    <div class="toolbar">
      <select v-model="leagueFilter" @change="loadMatches" class="select">
        <option value="">全部联赛</option>
        <option v-for="l in leagues" :key="l.code" :value="l.code">{{ l.name }}</option>
      </select>
      <select v-model="statusFilter" @change="loadMatches" class="select">
        <option value="upcoming">未开赛</option>
        <option value="finished">已结束</option>
        <option value="all">全部</option>
      </select>
      <span class="total">共 {{ total }} 场</span>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div class="match-grid">
      <div
        v-for="m in matches" :key="m.match_id"
        class="match-card"
        :class="{finished: isFinished(m)}"
        @click="goDetail(m.match_id)"
      >
        <div class="match-head">
          <span class="league-tag">{{ m.league_name }}</span>
          <span class="date">{{ fmtDate(m.match_date) }}</span>
        </div>
        <div class="teams">
          <span class="team home">{{ m.home_name }}</span>
          <span class="score" v-if="m.home_goals !== null">{{ m.home_goals }} - {{ m.away_goals }}</span>
          <span class="vs" v-else>VS</span>
          <span class="team away">{{ m.away_name }}</span>
        </div>
        <div class="status">{{ statusText(m) }}</div>
      </div>
    </div>

    <div class="pagination">
      <button :disabled="page<=1" @click="page--; loadMatches()">上一页</button>
      <span>第 {{ page }} 页</span>
      <button :disabled="page*limit>=total" @click="page++; loadMatches()">下一页</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'

const leagues = ref([])
const matches = ref([])
const total = ref(0)
const loading = ref(false)
const leagueFilter = ref('PL')
const statusFilter = ref('upcoming')
const page = ref(1)
const limit = ref(24)

onMounted(async () => {
  try {
    const r = await fetch('/data/leagues.json')
    leagues.value = await r.json()
  } catch(e) {}
  loadMatches()
})

async function loadMatches() {
  loading.value = true
  try {
    // 用 matches_by_league.json 做前端过滤 + 分页
    const full = await _getFullMatches()
    let items = full
    if (leagueFilter.value) {
      items = items.filter(m => m.league === leagueFilter.value)
    }
    if (statusFilter.value === 'upcoming') {
      items = items.filter(m => m.status === 'TIMED' || m.status === 'SCHEDULED')
    } else if (statusFilter.value === 'finished') {
      items = items.filter(m => m.home_goals !== null)
    }
    total.value = items.length
    items = items.slice((page.value - 1) * limit.value, page.value * limit.value)
    matches.value = items
  } finally {
    loading.value = false
  }
}

// 缓存一次全部数据，避免重复 fetch
let _allMatchesCache = null
async function _getFullMatches() {
  if (_allMatchesCache) return _allMatchesCache
  const r = await fetch('/data/matches_all.json')
  _allMatchesCache = await r.json()
  return _allMatchesCache
}

function fmtDate(d) {
  if (!d) return ''
  const t = new Date(d)
  return `${t.getMonth()+1}/${t.getDate()} ${String(t.getHours()).padStart(2,'0')}:${String(t.getMinutes()).padStart(2,'0')}`
}
function isFinished(m) { return m.home_goals !== null }
function statusText(m) {
  if (m.home_goals !== null) return `已结束 ${m.home_goals}-${m.away_goals}`
  return m.status === 'TIMED' ? '即将开赛' : '待定'
}
function goDetail(id) { window.location.hash = `#/match/${id}` }
</script>

<style scoped>
.toolbar {
  display: flex; gap: 12px; margin-bottom: 20px; align-items: center;
}
.select {
  padding: 10px 16px; background: #1e293b; color: #e2e8f0; border: 1px solid #334155;
  border-radius: 8px; font-size: 14px; cursor: pointer;
}
.total { color: #64748b; font-size: 13px; margin-left: auto; }
.loading { text-align: center; padding: 40px; color: #64748b; }

.match-grid {
  display: grid; gap: 12px;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
}
.match-card {
  background: #1e293b; border: 1px solid #334155; border-radius: 12px;
  padding: 16px; cursor: pointer; transition: all 0.2s;
}
.match-card:hover { border-color: #38bdf8; transform: translateY(-2px); }
.match-card.finished { opacity: 0.7; }
.match-head {
  display: flex; justify-content: space-between; margin-bottom: 12px;
  font-size: 12px;
}
.league-tag {
  background: #0c4a6e; color: #38bdf8; padding: 2px 8px; border-radius: 4px;
}
.date { color: #64748b; }
.teams {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 16px; font-weight: 500; gap: 8px;
}
.team { flex: 1; }
.team.home { text-align: right; }
.team.away { text-align: left; }
.score {
  font-size: 20px; font-weight: 700; color: #fbbf24; padding: 0 12px;
}
.vs {
  color: #64748b; padding: 0 12px;
}
.status {
  margin-top: 10px; font-size: 12px; text-align: center; color: #64748b;
}
.pagination {
  display: flex; justify-content: center; gap: 12px; margin-top: 24px; align-items: center;
}
.pagination button {
  padding: 8px 20px; background: #1e293b; color: #e2e8f0; border: 1px solid #334155;
  border-radius: 8px; cursor: pointer;
}
.pagination button:hover:not(:disabled) { border-color: #38bdf8; }
.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
