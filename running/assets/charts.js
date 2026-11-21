// Running Archive — Charts (multi-year, data from data/weeks*.json)
(function() {
  var accent, accent2, ink, muted, rule, bg2;
  var inst = {};   // chart instances by element id
  var YEAR_FILES = { 2024: 'data/weeks-2024.json', 2025: 'data/weeks-2025.json', 2026: 'data/weeks.json' };
  var CUR_YEAR = new Date().getFullYear();

  function paceStr(s) {
    var m = Math.floor(s/60), sec = s%60;
    return m+':'+(sec<10?'0':'')+sec;
  }
  function disposeAll() {
    Object.keys(inst).forEach(function(k){ if (inst[k]) { inst[k].dispose(); inst[k] = null; } });
  }

  function renderYear(year, data) {
    var weeks = data.weeks;
    var labels = weeks.map(function(w){ return w.monday.slice(5).replace('-','/'); });
    var t = data.totals;

    // KPI
    document.getElementById('kpi-km').textContent = t.km;
    document.getElementById('kpi-runs').textContent = t.runs;
    document.getElementById('kpi-hours').textContent = t.hours;
    document.getElementById('kpi-weeks-sub').textContent = weeks.length + ' 个训练周';
    document.getElementById('kpi-days-sub').textContent = t.active_days + ' 个跑步日';
    var b5 = data.highlights.best5k;
    if (b5) {
      document.getElementById('kpi-best5k').textContent = paceStr(b5.pace_s);
      document.getElementById('kpi-best5k-sub').textContent = b5.date + ' · ' + b5.km + ' km';
    }
    // 2026-only cards & insights
    var isCur = year === CUR_YEAR;
    document.querySelectorAll('.only-2026').forEach(function(el){ el.style.display = isCur ? '' : 'none'; });
    // Hero & captions
    document.getElementById('hero-year').textContent = year;
    document.getElementById('hero-period').textContent = data.period || ('2026-01-01 → ' + data.generated);
    document.getElementById('desc-kpi').textContent = year + ' 年累计数据（自动聚合自每次训练记录）';
    document.getElementById('cap-month').textContent = '月跑量（km · ' + year + '）';

    var tooltipBase = { backgroundColor: bg2, borderColor: rule, textStyle: { color: ink, fontSize: 12 } };
    function mk(id) { return echarts.init(document.getElementById(id), null, { renderer: 'svg' }); }
    function listen(c) { window.addEventListener('resize', function(){ c.resize(); }); }
    var axis = { axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted, fontSize: 11, interval: 3 } };
    var yaxis = function(extra) { return Object.assign({ type:'value', axisLine:{show:false}, axisTick:{show:false}, splitLine:{ lineStyle:{ color: rule, type:'dashed' } }, axisLabel:{ color: muted, fontSize: 11 } }, extra||{}); };

    // ===== Chart: Monthly mileage =====
    var months = data.months;
    var nMon = isCur ? 11 : 12;
    var mLabels = [], mKm = [];
    for (var i = 1; i <= nMon; i++) {
      var k = year + '-' + (i<10?'0':'') + i;
      mLabels.push(i+'月');
      mKm.push(months[k] ? months[k][0] : 0);
    }
    var c1 = mk('chart-month');
    inst['chart-month'] = c1;
    c1.setOption({
      animation:false,
      tooltip: Object.assign({ trigger:'axis', appendToBody:true, axisPointer:{type:'shadow'},
        formatter: function(p){ return '<b>'+year+'-'+(p[0].dataIndex+1<10?'0':'')+(p[0].dataIndex+1)+'</b><br>跑量：<b>'+p[0].value+'</b> km'+(p[0].value===0?'（休整）':''); } }, tooltipBase),
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
    inst['chart-week'] = c2;
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
    inst['chart-pace'] = c3;
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
    inst['chart-fastest'] = c4;
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
    inst['chart-longest'] = c5;
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
    inst['chart-freq'] = c6;
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
  }

  // ===== Chart: Cross-year comparison (always all years) =====
  function renderYearsCompare(all) {
    var years = [2024, 2025, 2026];
    var km = years.map(function(y){ return all[y] ? all[y].totals.km : 0; });
    var runs = years.map(function(y){ return all[y] ? all[y].totals.runs : 0; });
    var xLabels = years.map(function(y){ return y === CUR_YEAR ? y + '（截至' + (all[y].generated||'').slice(5).replace('-','/') + '）' : String(y); });
    var tooltipBase = { backgroundColor: bg2, borderColor: rule, textStyle: { color: ink, fontSize: 12 } };
    var c0 = echarts.init(document.getElementById('chart-years'), null, { renderer: 'svg' });
    inst['chart-years'] = c0;
    c0.setOption({
      animation:false,
      tooltip: Object.assign({ trigger:'axis', axisPointer:{type:'shadow'},
        formatter: function(p){
          var y = years[p[0].dataIndex];
          return '<b>'+xLabels[p[0].dataIndex]+'</b><br>总里程：<b>'+km[p[0].dataIndex]+' km</b><br>训练次数：<b>'+runs[p[0].dataIndex]+' 次</b>'+(all[y]?'<br>跑步日：'+all[y].totals.active_days+' 天 · '+all[y].totals.hours+' h':'');
        } }, tooltipBase),
      legend: { data:['总里程 km','训练次数'], textStyle:{ color:muted, fontSize:11 }, top:0, right:0 },
      grid: { left: 44, right: 52, top: 36, bottom: 28 },
      xAxis: { type:'category', data: xLabels, axisLine:{ lineStyle:{ color: rule } }, axisLabel:{ color:muted, fontSize:12 } },
      yAxis: [
        { type:'value', axisLine:{show:false}, axisTick:{show:false}, splitLine:{ lineStyle:{ color: rule, type:'dashed' } }, axisLabel:{ color:muted, fontSize:11 }, name:'km', nameTextStyle:{ color:muted, fontSize:11, padding:[0,0,0,30] } },
        { type:'value', axisLine:{show:false}, axisTick:{show:false}, splitLine:{show:false}, axisLabel:{ color:muted, fontSize:11 }, name:'次', nameTextStyle:{ color:muted, fontSize:11, padding:[0,30,0,0] } }
      ],
      series: [
        { name:'总里程 km', type:'bar', barMaxWidth: 44, data: km,
          itemStyle: { borderRadius:[4,4,0,0], color: { type:'linear', x:0,y:0,x2:0,y2:1, colorStops:[{offset:0,color:accent},{offset:1,color:'#24568c'}] } },
          label: { show:true, position:'top', color: muted, fontSize: 11 } },
        { name:'训练次数', type:'line', yAxisIndex:1, data: runs, symbolSize:8,
          lineStyle:{ color: accent2, width:2.5 }, itemStyle:{ color: accent2 } }
      ]
    });
    window.addEventListener('resize', function(){ c0.resize(); });
  }

  fetch('data/weeks.json')
    .then(function(r){ return r.json(); })
    .then(function(data26) {
      var st = getComputedStyle(document.documentElement);
      accent = st.getPropertyValue('--accent').trim();
      accent2 = st.getPropertyValue('--accent2').trim();
      ink = st.getPropertyValue('--ink').trim();
      muted = st.getPropertyValue('--muted').trim();
      rule = st.getPropertyValue('--rule').trim();
      bg2 = st.getPropertyValue('--bg2').trim();

      // Preload other years for cross-year chart (tolerate missing files)
      var all = { 2026: data26 };
      Promise.all([2024, 2025].map(function(y){
        return fetch(YEAR_FILES[y]).then(function(r){ return r.ok ? r.json() : null; }).catch(function(){ return null; });
      })).then(function(res){
        all[2024] = res[0]; all[2025] = res[1];
        renderYearsCompare(all);
      });

      // Initial render: current selection (default 2026)
      var current = 2026;
      renderYear(current, data26);

      // Year tabs
      document.querySelectorAll('.ytab').forEach(function(btn){
        btn.addEventListener('click', function(){
          var y = parseInt(btn.getAttribute('data-year'), 10);
          if (y === current) return;
          document.querySelectorAll('.ytab').forEach(function(b){ b.classList.toggle('active', b === btn); });
          current = y;
          if (y === 2026) { disposeAll(); renderYear(2026, data26); return; }
          fetch(YEAR_FILES[y])
            .then(function(r){ return r.json(); })
            .then(function(d){ disposeAll(); renderYear(y, d); })
            .catch(function(e){ console.error('load year failed', e); });
        });
      });
    })
    .catch(function(e){ console.error('weeks.json load failed', e); });
})();
