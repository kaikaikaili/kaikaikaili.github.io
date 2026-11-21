// Running Archive 2026 — Charts (data from data/weeks.json)
(function() {
  var accent, accent2, ink, muted, rule, bg2;
  function paceStr(s) {
    var m = Math.floor(s/60), sec = s%60;
    return m+':'+(sec<10?'0':'')+sec;
  }

  fetch('data/weeks.json')
    .then(function(r){ return r.json(); })
    .then(function(data) {
      var st = getComputedStyle(document.documentElement);
      accent = st.getPropertyValue('--accent').trim();
      accent2 = st.getPropertyValue('--accent2').trim();
      ink = st.getPropertyValue('--ink').trim();
      muted = st.getPropertyValue('--muted').trim();
      rule = st.getPropertyValue('--rule').trim();
      bg2 = st.getPropertyValue('--bg2').trim();

      var weeks = data.weeks;
      var labels = weeks.map(function(w){ return w.monday.slice(5).replace('-','/'); });

      // KPI fill
      var t = data.totals;
      document.getElementById('kpi-km').textContent = t.km;
      document.getElementById('kpi-runs').textContent = t.runs;
      document.getElementById('kpi-hours').textContent = t.hours;
      var b5 = data.highlights.best5k;
      if (b5) {
        document.getElementById('kpi-best5k').textContent = paceStr(b5.pace_s);
        document.getElementById('kpi-best5k-sub').textContent = b5.date + ' · ' + b5.km + ' km';
      }

      var tooltipBase = { backgroundColor: bg2, borderColor: rule, textStyle: { color: ink, fontSize: 12 } };
      function mk(id) { return echarts.init(document.getElementById(id), null, { renderer: 'svg' }); }
      function listen(c) { window.addEventListener('resize', function(){ c.resize(); }); }
      var axis = { axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted, fontSize: 11, interval: 3 } };
      var yaxis = function(extra) { return Object.assign({ type:'value', axisLine:{show:false}, axisTick:{show:false}, splitLine:{ lineStyle:{ color: rule, type:'dashed' } }, axisLabel:{ color: muted, fontSize: 11 } }, extra||{}); };

      // ===== Chart: Monthly mileage =====
      var months = data.months;
      var mLabels = [], mKm = [];
      for (var i = 1; i <= 11; i++) {
        var k = '2026-' + (i<10?'0':'') + i;
        mLabels.push(i+'月');
        mKm.push(months[k] ? months[k][0] : 0);
      }
      var c1 = mk('chart-month');
      c1.setOption({
        animation:false,
        tooltip: Object.assign({ trigger:'axis', appendToBody:true, axisPointer:{type:'shadow'},
          formatter: function(p){ return '<b>2026-'+(p[0].dataIndex+1<10?'0':'')+(p[0].dataIndex+1)+'</b><br>跑量：<b>'+p[0].value+'</b> km'+(p[0].value===0?'（休整）':''); } }, tooltipBase),
        grid: { left: 40, right: 16, top: 24, bottom: 28 },
        xAxis: Object.assign({}, axis, { type:'category', data: mLabels, axisLabel:{ color:muted, fontSize:11 } }),
        yAxis: yaxis({ name:'km', nameTextStyle:{ color:muted, fontSize:11, padding:[0,0,0,30] } }),
        series: [{
          type:'bar', barMaxWidth: 32,
          data: mKm.map(function(v){ return { value: v, itemStyle: { color: v===0 ? rule : accent, borderRadius:[4,4,0,0] } }; }),
          label: { show:true, position:'top', color: muted, fontSize: 10, formatter: function(p){ return p.value>0 ? p.value : ''; } }
        }]
      });
      listen(c1);

      // ===== Chart: Weekly mileage + cumulative =====
      var cum = [], s = 0;
      weeks.forEach(function(w){ s += w.km; cum.push(Math.round(s*10)/10); });
      var c2 = mk('chart-week');
      c2.setOption({
        animation:false,
        tooltip: Object.assign({ trigger:'axis', appendToBody:true,
          formatter: function(p){
            var w = weeks[p[0].dataIndex];
            return '<b>周 '+w.monday+'</b><br>周跑量：<b>'+w.km+' km</b>（'+w.runs+' 次）<br>累计：<b>'+cum[p[0].dataIndex]+' km</b><br>周均配速：'+paceStr(w.avg_pace_s)+' /km';
          } }, tooltipBase),
        legend: { data:['周跑量','累计里程'], textStyle:{ color:muted, fontSize:11 }, top:0, right:0 },
        grid: { left: 44, right: 52, top: 36, bottom: 28 },
        xAxis: Object.assign({}, axis, { type:'category', data: labels }),
        yAxis: [
          yaxis({ name:'周 km', nameTextStyle:{ color:muted, fontSize:11, padding:[0,0,0,34] } }),
          yaxis({ name:'累计', nameTextStyle:{ color:muted, fontSize:11, padding:[0,30,0,0] }, splitLine:{show:false}, axisLabel:{ color: muted, fontSize: 11 } })
        ],
        series: [
          { name:'周跑量', type:'bar', barMaxWidth: 12, data: weeks.map(function(w){ return w.km; }),
            itemStyle: { color: accent+'cc', borderRadius:[3,3,0,0] } },
          { name:'累计里程', type:'line', yAxisIndex:1, smooth:true, showSymbol:false,
            data: cum, lineStyle:{ color: accent2, width:2.5 }, itemStyle:{ color: accent2 } }
        ]
      });
      listen(c2);

      // ===== Chart: Weekly avg pace (inverted) =====
      var c3 = mk('chart-pace');
      c3.setOption({
        animation:false,
        tooltip: Object.assign({ trigger:'axis', appendToBody:true,
          formatter: function(p){ var w=weeks[p[0].dataIndex]; return '<b>周 '+w.monday+'</b><br>周均配速：<b>'+paceStr(w.avg_pace_s)+' /km</b>'; } }, tooltipBase),
        grid: { left: 44, right: 16, top: 24, bottom: 28 },
        xAxis: Object.assign({}, axis, { type:'category', data: labels }),
        yAxis: yaxis({ inverse:true, name:'min/km', nameTextStyle:{ color:muted, fontSize:11, padding:[0,0,0,34] },
          axisLabel:{ color:muted, fontSize:11, formatter: function(v){ return paceStr(v); } } }),
        series: [{
          type:'line', smooth:true, showSymbol:false, data: weeks.map(function(w){ return w.avg_pace_s; }),
          lineStyle:{ color: accent, width:3 }, itemStyle:{ color: accent },
          areaStyle: { color: { type:'linear', x:0,y:0,x2:0,y2:1, colorStops:[{offset:0,color:accent+'30'},{offset:1,color:accent+'05'}] } }
        }]
      });
      listen(c3);

      // ===== Chart: Weekly fastest pace =====
      var c4 = mk('chart-fastest');
      c4.setOption({
        animation:false,
        tooltip: Object.assign({ trigger:'axis', appendToBody:true,
          formatter: function(p){ var w=weeks[p[0].dataIndex]; return '<b>周 '+w.monday+'</b><br>单次最快：<b>'+paceStr(w.fastest_pace_s)+' /km</b>'; } }, tooltipBase),
        grid: { left: 44, right: 16, top: 24, bottom: 28 },
        xAxis: Object.assign({}, axis, { type:'category', data: labels }),
        yAxis: yaxis({ inverse:true, axisLabel:{ color:muted, fontSize:11, formatter: function(v){ return paceStr(v); } } }),
        series: [{
          type:'line', smooth:true, showSymbol:false, data: weeks.map(function(w){ return w.fastest_pace_s; }),
          lineStyle:{ color: accent2, width:3 }, itemStyle:{ color: accent2 },
          areaStyle: { color: { type:'linear', x:0,y:0,x2:0,y2:1, colorStops:[{offset:0,color:accent2+'30'},{offset:1,color:accent2+'05'}] } }
        }]
      });
      listen(c4);

      // ===== Chart: Weekly longest single run =====
      var c5 = mk('chart-longest');
      c5.setOption({
        animation:false,
        tooltip: Object.assign({ trigger:'axis', appendToBody:true, axisPointer:{type:'shadow'},
          formatter: function(p){ var w=weeks[p[0].dataIndex]; return '<b>周 '+w.monday+'</b><br>最长单次：<b>'+w.longest_km+' km</b>'; } }, tooltipBase),
        grid: { left: 40, right: 16, top: 24, bottom: 28 },
        xAxis: Object.assign({}, axis, { type:'category', data: labels }),
        yAxis: yaxis({ name:'km', nameTextStyle:{ color:muted, fontSize:11, padding:[0,0,0,30] } }),
        series: [{ type:'bar', barMaxWidth: 12, data: weeks.map(function(w){ return w.longest_km; }),
          itemStyle: { color: accent2+'cc', borderRadius:[3,3,0,0] } }]
      });
      listen(c5);

      // ===== Chart: Weekly run count =====
      var c6 = mk('chart-freq');
      c6.setOption({
        animation:false,
        tooltip: Object.assign({ trigger:'axis', appendToBody:true, axisPointer:{type:'shadow'},
          formatter: function(p){ var w=weeks[p[0].dataIndex]; return '<b>周 '+w.monday+'</b><br>训练次数：<b>'+w.runs+'</b> 次'; } }, tooltipBase),
        grid: { left: 40, right: 16, top: 24, bottom: 28 },
        xAxis: Object.assign({}, axis, { type:'category', data: labels }),
        yAxis: yaxis(),
        series: [{ type:'bar', barMaxWidth: 12, data: weeks.map(function(w){ return w.runs; }),
          itemStyle: { color: accent+'99', borderRadius:[3,3,0,0] } }]
      });
      listen(c6);
    })
    .catch(function(e){ console.error('weeks.json load failed', e); });
})();
