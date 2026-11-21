// 半马备战 — 状态计算与追踪图（数据源 ../data/weeks.json，随周报自动更新）
(function() {
  function paceStr(s) { var m = Math.floor(s/60), sec = s%60; return m+':'+(sec<10?'0':'')+sec; }

  fetch('../data/weeks.json')
    .then(function(r){ return r.json(); })
    .then(function(d) {
      var weeks = d.weeks.slice();           // chronological
      var TARGET_PACE = 233;                  // 3:53 /km
      var PEAK_WEEK_KM = 70;
      var RACE_KM = 21.1;

      var last4 = weeks.slice(-4), last8 = weeks.slice(-8), last16 = weeks.slice(-16);
      var avg4 = last4.reduce(function(s,w){ return s + w.km; }, 0) / Math.max(1,last4.length);
      var freq8 = last8.reduce(function(s,w){ return s + w.runs; }, 0) / Math.max(1,last8.length);
      var long8 = Math.max.apply(null, last8.map(function(w){ return w.longest_km; }));
      var fast8 = Math.min.apply(null, last8.map(function(w){ return w.fastest_pace_s; }));
      var avgPace4 = Math.round(last4.reduce(function(s,w){ return s + w.avg_pace_s*w.runs; },0) / Math.max(1, last4.reduce(function(s,w){ return s+w.runs; },0)));

      document.getElementById('s-avg4').textContent = Math.round(avg4*10)/10;
      document.getElementById('s-avg4-sub').textContent = '周均配速 ' + paceStr(avgPace4) + ' /km';
      document.getElementById('s-long8').textContent = long8;
      document.getElementById('s-gap').textContent = Math.max(0, Math.round((RACE_KM - long8)*10)/10);
      document.getElementById('s-freq8').textContent = Math.round(freq8*10)/10;
      document.getElementById('s-fast8').textContent = paceStr(fast8);

      function pct(v) { return Math.max(0, Math.min(100, Math.round(v))); }
      var vol = pct(avg4 / PEAK_WEEK_KM * 100);
      var endo = pct(long8 / RACE_KM * 100);
      var spd = pct((TARGET_PACE - fast8) / (TARGET_PACE - 185) * 100);
      document.getElementById('b-vol').style.width = vol + '%';
      document.getElementById('b-vol-txt').textContent = vol + '%';
      document.getElementById('b-endo').style.width = endo + '%';
      document.getElementById('b-endo-txt').textContent = endo + '%';
      document.getElementById('b-spd').style.width = spd + '%';
      document.getElementById('b-spd-txt').textContent = spd + '%';

      // tracking chart: last 16 weeks
      var st = getComputedStyle(document.documentElement);
      var accent = st.getPropertyValue('--accent').trim();
      var accent2 = st.getPropertyValue('--accent2').trim();
      var muted = st.getPropertyValue('--muted').trim();
      var rule = st.getPropertyValue('--rule').trim();
      var bg2 = st.getPropertyValue('--bg2').trim();
      var wk = last16;
      var labels = wk.map(function(w){ return w.monday.slice(5).replace('-','/'); });

      var c = echarts.init(document.getElementById('chart-track'), null, { renderer: 'svg' });
      c.setOption({
        animation: false,
        tooltip: { backgroundColor: bg2, borderColor: rule, textStyle: { color: '#e8ecf4', fontSize: 12 },
          trigger: 'axis', axisPointer: { type: 'shadow' },
          formatter: function(p) {
            var w = wk[p[0].dataIndex];
            return '<b>周 ' + w.monday + '</b><br>周跑量：<b>' + w.km + ' km</b>（' + w.runs + ' 次）<br>最长单次：<b>' + w.longest_km + ' km</b><br>周均配速：' + paceStr(w.avg_pace_s) + ' /km';
          } },
        legend: { data: ['周跑量 km', '最长单次 km'], textStyle: { color: muted, fontSize: 11 }, top: 0, right: 0 },
        grid: { left: 44, right: 20, top: 36, bottom: 28 },
        xAxis: { type: 'category', data: labels, axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted, fontSize: 11 } },
        yAxis: { type: 'value', axisLine: { show: false }, axisTick: { show: false },
          splitLine: { lineStyle: { color: rule, type: 'dashed' } }, axisLabel: { color: muted, fontSize: 11 } },
        series: [
          { name: '周跑量 km', type: 'bar', barMaxWidth: 14, data: wk.map(function(w){ return w.km; }),
            itemStyle: { color: accent + 'cc', borderRadius: [3,3,0,0] } },
          { name: '最长单次 km', type: 'line', smooth: true, symbolSize: 7, data: wk.map(function(w){ return w.longest_km; }),
            lineStyle: { color: accent2, width: 3 }, itemStyle: { color: accent2 },
            markLine: { silent: true, symbol: 'none',
              lineStyle: { color: '#ff6b6b', type: 'dashed' },
              label: { color: '#ff6b6b', fontSize: 10, formatter: '半马 21.1 km' },
              data: [{ yAxis: 21.1 }] } }
        ]
      });
      window.addEventListener('resize', function(){ c.resize(); });
    })
    .catch(function(e){ console.error('half page load failed', e); });
})();
