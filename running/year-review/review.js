// 2026 Year in Review — charts & lists
(function() {
  var accent, accent2, ink, muted, rule, bg2;
  function paceStr(s) { var m = Math.floor(s/60), sec = s%60; return m+':'+(sec<10?'0':'')+sec; }
  function fmtDur(s) { var h = Math.floor(s/3600), m = Math.round(s%3600/60); return h>0 ? h+' h '+m+' min' : m+' min'; }

  fetch('../data/review-2026.json')
    .then(function(r){ return r.json(); })
    .then(function(d) {
      var st = getComputedStyle(document.documentElement);
      accent = st.getPropertyValue('--accent').trim();
      accent2 = st.getPropertyValue('--accent2').trim();
      ink = st.getPropertyValue('--ink').trim();
      muted = st.getPropertyValue('--muted').trim();
      rule = st.getPropertyValue('--rule').trim();
      bg2 = st.getPropertyValue('--bg2').trim();
      var tooltipBase = { backgroundColor: bg2, borderColor: rule, textStyle: { color: ink, fontSize: 12 } };
      function mk(id) { return echarts.init(document.getElementById(id), null, { renderer: 'svg' }); }
      function listen(c) { window.addEventListener('resize', function(){ c.resize(); }); }

      // KPI
      var t = d.totals;
      document.getElementById('big-km').textContent = t.km;
      document.getElementById('hero-sub').textContent = '数据周期 2026-01-01 → ' + d.generated + ' · 南京大学 · COROS PACE 3 · 数据已脱敏';
      document.getElementById('k-km').textContent = t.km;
      document.getElementById('k-vs').textContent = '+4.4%';
      document.getElementById('k-runs').textContent = t.runs;
      document.getElementById('k-runs-sub').textContent = '户外 ' + (d.types['户外跑']||[0,0])[1] + ' · 赛道 ' + (d.types['赛道跑']||[0,0])[1];
      document.getElementById('k-hours').textContent = t.hours;
      document.getElementById('k-hr').textContent = t.avg_hr_active;
      document.getElementById('k-days').textContent = t.active_days;
      document.getElementById('k-streak').textContent = d.streak_max;
      document.getElementById('k-long').textContent = d.highlights.longest.km;
      document.getElementById('k-long-sub').textContent = d.highlights.longest.date.slice(5) + ' · ' + fmtDur(d.highlights.longest.dur_s);
      document.getElementById('k-b5').textContent = paceStr(d.highlights.best5k.pace_s);
      document.getElementById('k-b5-sub').textContent = d.highlights.best5k.date.slice(5) + ' · ' + d.highlights.best5k.km + ' km';

      // ===== Calendar heatmap =====
      var calData = Object.keys(d.daily).map(function(k){ return [k, d.daily[k]]; });
      var c1 = mk('chart-cal');
      c1.setOption({
        animation: false,
        tooltip: Object.assign({ formatter: function(p){ return '<b>'+p.value[0]+'</b><br>跑量：<b>'+p.value[1]+'</b> km'; } }, tooltipBase),
        visualMap: { min: 0, max: 16, calculable: false, show: false, inRange: { color: ['#1e2536', '#24568c', '#3d9bff', '#8fc7ff'] } },
        calendar: {
          top: 30, left: 48, right: 16, cellSize: ['auto', 15],
          range: ['2026-01-01', d.generated],
          itemStyle: { color: '#171d2c', borderWidth: 2, borderColor: '#0f1420' },
          splitLine: { show: false },
          yearLabel: { show: false },
          monthLabel: { color: muted, fontSize: 11 },
          dayLabel: { color: muted, fontSize: 10, nameMap: ['日','一','二','三','四','五','六'], firstDay: 1 }
        },
        series: [{ type: 'heatmap', coordinateSystem: 'calendar', data: calData }]
      });
      listen(c1);

      // ===== Monthly =====
      var mKeys = Object.keys(d.months);
      var c2 = mk('chart-month');
      c2.setOption({
        animation: false,
        tooltip: Object.assign({ trigger: 'axis' }, tooltipBase),
        legend: { data: ['跑量 km', '次数'], textStyle: { color: muted, fontSize: 11 }, top: 0, right: 0 },
        grid: { left: 44, right: 52, top: 36, bottom: 28 },
        xAxis: { type: 'category', data: mKeys.map(function(k){ return parseInt(k.slice(5)) + '月'; }),
          axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted, fontSize: 11 } },
        yAxis: [
          { type: 'value', axisLine: { show: false }, axisTick: { show: false }, splitLine: { lineStyle: { color: rule, type: 'dashed' } }, axisLabel: { color: muted, fontSize: 11 } },
          { type: 'value', axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false }, axisLabel: { color: muted, fontSize: 11 } }
        ],
        series: [
          { name: '跑量 km', type: 'bar', barMaxWidth: 30,
            data: mKeys.map(function(k){ return d.months[k][0]; }),
            itemStyle: { borderRadius: [4,4,0,0], color: { type: 'linear', x:0, y:0, x2:0, y2:1, colorStops: [{ offset:0, color: accent }, { offset:1, color: '#24568c' }] } },
            label: { show: true, position: 'top', color: muted, fontSize: 10 } },
          { name: '次数', type: 'line', yAxisIndex: 1, smooth: true, symbolSize: 7,
            data: mKeys.map(function(k){ return d.months[k][1]; }),
            lineStyle: { color: accent2, width: 2.5 }, itemStyle: { color: accent2 } }
        ]
      });
      listen(c2);

      // ===== Type donut =====
      var c3 = mk('chart-type');
      var typeData = Object.keys(d.types).map(function(k){ return { name: k, value: d.types[k][0] }; });
      c3.setOption({
        animation: false,
        tooltip: Object.assign({ formatter: function(p){ var v=d.types[p.name]; return '<b>'+p.name+'</b><br>'+v[0]+' km · '+v[1]+' 次 · '+v[2]+' h'; } }, tooltipBase),
        legend: { bottom: 0, textStyle: { color: muted, fontSize: 11 } },
        series: [{ type: 'pie', radius: ['52%', '78%'], center: ['50%', '46%'],
          label: { color: ink, fontSize: 12, formatter: '{b}\n{d}%' },
          data: typeData,
          color: [accent, accent2] }]
      });
      listen(c3);

      // ===== Pace histogram =====
      var c4 = mk('chart-pace');
      c4.setOption({
        animation: false,
        tooltip: Object.assign({ trigger: 'axis', axisPointer: { type: 'shadow' },
          formatter: function(p){ var b=d.pace_hist[p[0].dataIndex]; return '<b>'+b.label+' /km</b><br>'+b.runs+' 次 · '+b.km+' km'; } }, tooltipBase),
        grid: { left: 40, right: 16, top: 24, bottom: 28 },
        xAxis: { type: 'category', data: d.pace_hist.map(function(b){ return b.label; }),
          axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted, fontSize: 10 } },
        yAxis: { type: 'value', axisLine: { show: false }, axisTick: { show: false }, splitLine: { lineStyle: { color: rule, type: 'dashed' } }, axisLabel: { color: muted, fontSize: 11 } },
        series: [{ type: 'bar', barMaxWidth: 28,
          data: d.pace_hist.map(function(b){ return b.runs; }),
          itemStyle: { borderRadius: [4,4,0,0], color: accent + 'cc' } }]
      });
      listen(c4);

      // ===== Moments lists =====
      function fillList(id, arr, fast) {
        var el = document.getElementById(id);
        el.innerHTML = '';
        arr.forEach(function(x, i) {
          var div = document.createElement('div');
          div.className = 'moment' + (fast ? ' fast' : '');
          div.innerHTML = '<span class="m-rank">' + (i+1 < 10 ? '0' : '') + (i+1) + '</span>'
            + '<div class="m-main"><div class="m-title">' + x.date + ' · ' + x.type + '</div>'
            + '<div class="m-sub">配速 ' + paceStr(x.pace_s) + ' /km · ' + fmtDur(x.dur_s) + (x.hr ? ' · 平均心率 ' + x.hr + ' bpm' : '') + '</div></div>'
            + '<span class="m-val">' + x.km + ' km</span>';
          el.appendChild(div);
        });
      }
      fillList('list-long', d.top_long, false);
      fillList('list-fast', d.fastest_runs, true);

      // ===== 3-year comparison =====
      fetch('../data/weeks-2025.json').then(function(r){ return r.json(); }).catch(function(){ return null; }).then(function(d25) {
        fetch('../data/weeks-2024.json').then(function(r){ return r.json(); }).catch(function(){ return null; }).then(function(d24) {
          var c5 = mk('chart-years');
          c5.setOption({
            animation: false,
            tooltip: Object.assign({ trigger: 'axis', axisPointer: { type: 'shadow' } }, tooltipBase),
            legend: { data: ['年里程 km', '训练次数'], textStyle: { color: muted, fontSize: 11 }, top: 0, right: 0 },
            grid: { left: 44, right: 52, top: 36, bottom: 28 },
            xAxis: { type: 'category', data: ['2024', '2025', '2026'],
              axisLine: { lineStyle: { color: rule } }, axisLabel: { color: ink, fontSize: 12 } },
            yAxis: [
              { type: 'value', axisLine: { show: false }, axisTick: { show: false }, splitLine: { lineStyle: { color: rule, type: 'dashed' } }, axisLabel: { color: muted, fontSize: 11 } },
              { type: 'value', axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false }, axisLabel: { color: muted, fontSize: 11 } }
            ],
            series: [
              { name: '年里程 km', type: 'bar', barMaxWidth: 44,
                data: [d24 ? d24.totals.km : 0, d25 ? d25.totals.km : 0, d.totals.km],
                itemStyle: { borderRadius: [4,4,0,0], color: { type: 'linear', x:0, y:0, x2:0, y2:1, colorStops: [{ offset:0, color: accent }, { offset:1, color: '#24568c' }] } },
                label: { show: true, position: 'top', color: muted, fontSize: 11 } },
              { name: '训练次数', type: 'line', yAxisIndex: 1, symbolSize: 8,
                data: [d24 ? d24.totals.runs : 0, d25 ? d25.totals.runs : 0, d.totals.runs],
                lineStyle: { color: accent2, width: 2.5 }, itemStyle: { color: accent2 } }
            ]
          });
          listen(c5);
        });
      });
    })
    .catch(function(e){ console.error('review load failed', e); });
})();
