<template>
  <div class="app">
    <header class="nav">
      <div class="logo">⚽ 足球概率推演</div>
      <nav>
        <a href="#/matches" :class="{active: route==='matches' || route==='detail'}">赛程</a>
        <a href="#/backtest" :class="{active: route==='backtest'}">回测</a>
      </nav>
    </header>

    <main class="content">
      <MatchList v-if="route==='matches'" />
      <MatchDetail v-else-if="route==='detail'" :matchId="matchId" />
      <Backtest v-else-if="route==='backtest'" />
    </main>

    <footer class="disclaimer">
      ⚠ 本工具仅基于历史数据做统计概率推演，不构成任何投注建议，足球存在大量偶然性
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import MatchList from './components/MatchList.vue'
import MatchDetail from './components/MatchDetail.vue'
import Backtest from './components/Backtest.vue'

const route = ref('matches')
const matchId = ref(null)

function parseHash() {
  const h = window.location.hash.replace('#/', '')
  if (h.startsWith('match/')) {
    route.value = 'detail'
    matchId.value = parseInt(h.split('/')[1])
  } else if (h === 'backtest') {
    route.value = 'backtest'
  } else {
    route.value = 'matches'
  }
}

onMounted(() => {
  parseHash()
  window.addEventListener('hashchange', parseHash)
})
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
  background: #0f172a; color: #e2e8f0; min-height: 100vh;
}
.app { display: flex; flex-direction: column; min-height: 100vh; }
.nav {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 32px; background: #1e293b; border-bottom: 1px solid #334155;
  position: sticky; top: 0; z-index: 10;
}
.logo { font-size: 20px; font-weight: 700; color: #38bdf8; }
.nav nav { display: flex; gap: 8px; }
.nav a {
  padding: 8px 20px; border-radius: 8px; color: #94a3b8; text-decoration: none;
  transition: all 0.2s;
}
.nav a:hover { color: #e2e8f0; background: #334155; }
.nav a.active { color: #38bdf8; background: #0c4a6e; }
.content { flex: 1; padding: 24px 32px; max-width: 1400px; margin: 0 auto; width: 100%; }
.disclaimer {
  background: #422006; color: #fbbf24; text-align: center; padding: 12px;
  font-size: 13px; border-top: 1px solid #78350f;
}
</style>
