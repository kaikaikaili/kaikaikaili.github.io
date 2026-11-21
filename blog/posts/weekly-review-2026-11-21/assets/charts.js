// COROS Weekly Review — Charts
(function() {
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim();
  var accent2 = style.getPropertyValue('--accent2').trim();
  var ink = style.getPropertyValue('--ink').trim();
  var muted = style.getPropertyValue('--muted').trim();
  var rule = style.getPropertyValue('--rule').trim();
  var bg2 = style.getPropertyValue('--bg2').trim();

  // Helper: weekday labels
  var weekdays = ['日', '一', '二', '三', '四', '五', '六'];
  var dates = ['11-15','11-16','11-17','11-18','11-19','11-20','11-21'];

  // ===== Chart: Daily Sleep Duration (bar with phases stacked) =====
  // data: [total_min, deep_min, light_min, rem_min, awake_min] per day
  var sleepData = [
    { d:'11-15', total:453, deep:24, light:344, rem:48, awake:37, score:76 },
    { d:'11-16', total:476, deep:85, light:248, rem:117, awake:26, score:89 },
    { d:'11-17', total:487, deep:61, light:279, rem:128, awake:19, score:90 },
    { d:'11-18', total:474, deep:67, light:249, rem:128, awake:30, score:82 },
    { d:'11-19', total:471, deep:56, light:253, rem:149, awake:13, score:88 },
    { d:'11-20', total:454, deep:48, light:238, rem:145, awake:23, score:86 },
    { d:'11-21', total:497, deep:34, light:297, rem:132, awake:34, score:85 }
  ];

  var chartSleep = echarts.init(document.getElementById('chart-sleep'), null, { renderer: 'svg' });
  chartSleep.setOption({
    animation: false,
    tooltip: {
      trigger: 'axis',
      appendToBody: true,
      backgroundColor: bg2,
      borderColor: rule,
      textStyle: { color: ink, fontSize: 12 },
      axisPointer: { type: 'shadow' },
      formatter: function(p) {
        var d = p[0].axisValue;
        var row = sleepData.find(function(x){ return x.d === d; });
        if (!row) return d;
        var hrs = Math.floor(row.total/60), mins = row.total%60;
        return '<b>'+ d +'</b> 睡眠<br>'+
               '总时长：'+ hrs+'h '+mins+'min<br>'+
               '深睡：'+ row.deep+'min | 浅睡：'+ row.light+'min<br>'+
               'REM：'+ row.rem+'min | 清醒：'+ row.awake+'min<br>'+
               '睡眠评分：<b>'+ row.score+'</b>';
      }
    },
    legend: {
      data: ['深睡', '浅睡', 'REM', '清醒'],
      textStyle: { color: muted, fontSize: 11 },
      top: 0, right: 0
    },
    grid: { left: 36, right: 16, top: 40, bottom: 36 },
    xAxis: {
      type: 'category',
      data: sleepData.map(function(x){ return x.d; }),
      axisLine: { lineStyle: { color: rule } },
      axisLabel: { color: muted, fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      name: '分钟',
      nameTextStyle: { color: muted, fontSize: 11, padding: [0,0,0,30] },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: rule, type: 'dashed' } },
      axisLabel: { color: muted, fontSize: 11 }
    },
    series: [
      { name:'深睡', type:'bar', stack:'s', data: sleepData.map(function(x){ return x.deep; }), itemStyle:{ color: accent }, barMaxWidth: 28 },
      { name:'浅睡', type:'bar', stack:'s', data: sleepData.map(function(x){ return x.light; }), itemStyle:{ color: accent2 } },
      { name:'REM', type:'bar', stack:'s', data: sleepData.map(function(x){ return x.rem; }), itemStyle:{ color: accent2+'80' } },
      { name:'清醒', type:'bar', stack:'s', data: sleepData.map(function(x){ return x.awake; }), itemStyle:{ color: rule } }
    ]
  });
  window.addEventListener('resize', function(){ chartSleep.resize(); });

  // ===== Chart: Sleep Score (line) =====
  var chartScore = echarts.init(document.getElementById('chart-sleep-score'), null, { renderer: 'svg' });
  chartScore.setOption({
    animation: false,
    tooltip: {
      trigger: 'axis', appendToBody: true,
      backgroundColor: bg2, borderColor: rule, textStyle: { color: ink, fontSize: 12 }
    },
    grid: { left: 36, right: 16, top: 24, bottom: 28 },
    xAxis: {
      type: 'category',
      data: sleepData.map(function(x){ return x.d; }),
      axisLine: { lineStyle: { color: rule } },
      axisLabel: { color: muted, fontSize: 11 }
    },
    yAxis: {
      type: 'value', min: 70, max: 95,
      axisLine: { show: false }, axisTick: { show: false },
      splitLine: { lineStyle: { color: rule, type: 'dashed' } },
      axisLabel: { color: muted, fontSize: 11 }
    },
    series: [{
      type: 'line', smooth: true, showSymbol: true, symbolSize: 8,
      data: sleepData.map(function(x){ return x.score; }),
      lineStyle: { color: accent, width: 3 },
      itemStyle: { color: accent, borderColor: '#fff', borderWidth: 2 },
      areaStyle: { color: { type:'linear', x:0,y:0,x2:0,y2:1, colorStops:[
        {offset:0, color: accent+'40'}, {offset:1, color: accent+'05'}
      ]}},
      label: { show: true, position: 'top', color: accent, fontSize: 11, fontWeight: 600 }
    }]
  });
  window.addEventListener('resize', function(){ chartScore.resize(); });

  // ===== Chart: HRV Daily Average (bar + baseline) =====
  var hrvData = [
    { d:'11-15', val:101, base:97, low:89,  high:105, status:'正常' },
    { d:'11-16', val:83,  base:98, low:90,  high:106, status:'偏低' },
    { d:'11-17', val:95,  base:97, low:88,  high:106, status:'正常' },
    { d:'11-18', val:103, base:97, low:88,  high:106, status:'正常' },
    { d:'11-19', val:123, base:97, low:88,  high:106, status:'偏高' },
    { d:'11-20', val:109, base:98, low:88,  high:108, status:'偏高' },
    { d:'11-21', val:103, base:98, low:88,  high:108, status:'正常' }
  ];

  var chartHrv = echarts.init(document.getElementById('chart-hrv'), null, { renderer: 'svg' });
  chartHrv.setOption({
    animation: false,
    tooltip: {
      trigger: 'axis', appendToBody: true,
      backgroundColor: bg2, borderColor: rule, textStyle: { color: ink, fontSize: 12 },
      formatter: function(p) {
        var row = hrvData.find(function(x){ return x.d === p[0].axisValue; });
        if (!row) return p[0].axisValue;
        return '<b>'+ row.d +'</b><br>HRV：<b>'+ row.val+' ms</b> ('+row.status+')<br>'+
               '基线：'+ row.base+' ms | 正常区间：'+ row.low+'–'+ row.high;
      }
    },
    grid: { left: 40, right: 16, top: 36, bottom: 36 },
    xAxis: {
      type: 'category',
      data: hrvData.map(function(x){ return x.d; }),
      axisLine: { lineStyle: { color: rule } },
      axisLabel: { color: muted, fontSize: 11 }
    },
    yAxis: {
      type: 'value', name: 'ms',
      nameTextStyle: { color: muted, fontSize: 11, padding: [0,0,0,30] },
      axisLine: { show: false }, axisTick: { show: false },
      splitLine: { lineStyle: { color: rule, type: 'dashed' } },
      axisLabel: { color: muted, fontSize: 11 }
    },
    series: [
      {
        name:'HRV', type:'bar', barMaxWidth: 24,
        data: hrvData.map(function(x){ return {
          value: x.val,
          itemStyle: {
            color: x.status === '偏高' ? accent : (x.status === '偏低' ? accent2 : accent+'cc')
          }
        }; }),
        markLine: {
          silent: true, symbol: 'none',
          lineStyle: { color: rule, type: 'dashed', width: 1 },
          data: [{ yAxis: 97, label: { formatter: '基线 97ms', color: muted, fontSize: 10 } }]
        }
      }
    ]
  });
  window.addEventListener('resize', function(){ chartHrv.resize(); });

  // ===== Chart: RHR (line) =====
  var rhrData = [
    { d:'11-15', val:48 }, { d:'11-16', val:44 }, { d:'11-17', val:43 },
    { d:'11-18', val:49 }, { d:'11-19', val:47 }, { d:'11-20', val:44 },
    { d:'11-21', val:46 }
  ];
  var chartRhr = echarts.init(document.getElementById('chart-rhr'), null, { renderer: 'svg' });
  chartRhr.setOption({
    animation: false,
    tooltip: { trigger: 'axis', appendToBody: true, backgroundColor: bg2, borderColor: rule, textStyle: { color: ink, fontSize: 12 } },
    grid: { left: 36, right: 16, top: 24, bottom: 28 },
    xAxis: { type:'category', data: rhrData.map(function(x){ return x.d; }), axisLine:{ lineStyle:{ color: rule } }, axisLabel:{ color: muted, fontSize: 11 } },
    yAxis: { type:'value', min:40, max:52, axisLine:{ show:false }, axisTick:{ show:false }, splitLine:{ lineStyle:{ color: rule, type:'dashed' } }, axisLabel:{ color: muted, fontSize: 11 } },
    series: [{
      type:'line', smooth:true, symbolSize:8, showSymbol:true,
      data: rhrData.map(function(x){ return x.val; }),
      lineStyle:{ color: accent2, width:3 }, itemStyle:{ color: accent2, borderColor:'#fff', borderWidth:2 },
      areaStyle:{ color:{ type:'linear', x:0,y:0,x2:0,y2:1, colorStops:[{offset:0, color: accent2+'40'},{offset:1, color: accent2+'05'}] } },
      label:{ show:true, position:'top', color: accent2, fontSize:11, fontWeight:600, formatter:'{c} bpm' }
    }]
  });
  window.addEventListener('resize', function(){ chartRhr.resize(); });

  // ===== Chart: Training Load Ratio =====
  var loadData = [
    { d:'11-15', stl:35, ltl:60, ratio:0.58, comment:'Performance' },
    { d:'11-16', stl:37, ltl:60, ratio:0.61, comment:'Performance' },
    { d:'11-17', stl:49, ltl:61, ratio:0.80, comment:'Maintaining' },
    { d:'11-18', stl:45, ltl:61, ratio:0.73, comment:'Performance' },
    { d:'11-19', stl:39, ltl:60, ratio:0.65, comment:'Performance' },
    { d:'11-20', stl:44, ltl:60, ratio:0.73, comment:'Performance' },
    { d:'11-21', stl:52, ltl:61, ratio:0.85, comment:'Maintaining' }
  ];

  var chartLoad = echarts.init(document.getElementById('chart-load'), null, { renderer: 'svg' });
  chartLoad.setOption({
    animation: false,
    tooltip: {
      trigger: 'axis', appendToBody: true,
      backgroundColor: bg2, borderColor: rule, textStyle: { color: ink, fontSize: 12 },
      formatter: function(p) {
        var row = loadData.find(function(x){ return x.d === p[0].axisValue; });
        if (!row) return p[0].axisValue;
        return '<b>'+ row.d +'</b><br>STL：'+ row.stl+' | LTL：'+ row.ltl+'<br>负荷比：<b>'+ row.ratio.toFixed(2)+'</b> ('+row.comment+')';
      }
    },
    legend: { data:['短期负荷 STL','长期负荷 LTL'], textStyle:{ color:muted, fontSize:11 }, top:0, right:0 },
    grid: { left: 40, right: 16, top: 40, bottom: 36 },
    xAxis: { type:'category', data: loadData.map(function(x){ return x.d; }), axisLine:{ lineStyle:{ color: rule } }, axisLabel:{ color: muted, fontSize: 11 } },
    yAxis: { type:'value', axisLine:{ show:false }, axisTick:{ show:false }, splitLine:{ lineStyle:{ color: rule, type:'dashed' } }, axisLabel:{ color: muted, fontSize: 11 } },
    series: [
      { name:'短期负荷 STL', type:'line', smooth:true, data: loadData.map(function(x){ return x.stl; }), lineStyle:{ color: accent, width:3 }, itemStyle:{ color: accent } },
      { name:'长期负荷 LTL', type:'line', smooth:true, data: loadData.map(function(x){ return x.ltl; }), lineStyle:{ color: accent2, width:2, type:'dashed' }, itemStyle:{ color: accent2 } }
    ]
  });
  window.addEventListener('resize', function(){ chartLoad.resize(); });

  // ===== Chart: Stress Level =====
  var stressData = [
    { d:'11-15', v:31 }, { d:'11-16', v:27 }, { d:'11-17', v:32 },
    { d:'11-18', v:32 }, { d:'11-19', v:26 }, { d:'11-20', v:40 },
    { d:'11-21', v:40 }
  ];
  var chartStress = echarts.init(document.getElementById('chart-stress'), null, { renderer: 'svg' });
  chartStress.setOption({
    animation: false,
    tooltip: { trigger: 'axis', appendToBody: true, backgroundColor: bg2, borderColor: rule, textStyle: { color: ink, fontSize: 12 } },
    grid: { left: 36, right: 16, top: 24, bottom: 28 },
    xAxis: { type:'category', data: stressData.map(function(x){ return x.d; }), axisLine:{ lineStyle:{ color: rule } }, axisLabel:{ color: muted, fontSize: 11 } },
    yAxis: { type:'value', min:20, max:45, axisLine:{ show:false }, axisTick:{ show:false }, splitLine:{ lineStyle:{ color: rule, type:'dashed' } }, axisLabel:{ color: muted, fontSize: 11 } },
    visualMap: { show:false, min:20, max:45, inRange:{ color:[accent2, accent+'99', accent] } },
    series: [{
      type:'bar', barMaxWidth: 28,
      data: stressData.map(function(x){ return { value: x.v }; }),
      label:{ show:true, position:'top', color: muted, fontSize: 11, formatter:'{c}' }
    }]
  });
  window.addEventListener('resize', function(){ chartStress.resize(); });

  // ===== Chart: Run Pace per session (horizontal bar) =====
  // Sport records 11-15 to 11-21 (9 records)
  // Reconstructed from querySportRecords output
  var runs = [
    { date:'11-21', time:'今晨 07:14', type:'赛道跑', dist:3.00, pace:208, hr:175, dur:'10:26' },
    { date:'11-21', time:'今晨 06:31', type:'户外跑', dist:1.11, pace:358, hr:136, dur:'06:38' },
    { date:'11-21', time:'今晨 06:21', type:'户外跑', dist:1.14, pace:360, hr:140, dur:'06:51' },
    { date:'11-21', time:'今晨 06:13', type:'户外跑', dist:1.01, pace:372, hr:132, dur:'06:15' },
    { date:'11-20', time:'昨晨', type:'赛道跑', dist:1.51, pace:190, hr:176, dur:'04:46' },
    { date:'11-20', time:'昨晨', type:'户外跑', dist:1.05, pace:358, hr:134, dur:'06:16' },
    { date:'11-18', time:'周二', type:'赛道跑', dist:3.05, pace:202, hr:174, dur:'10:17' },
    { date:'11-18', time:'周二', type:'户外跑', dist:1.02, pace:360, hr:133, dur:'06:07' },
    { date:'11-16', time:'周日', type:'户外跑', dist:3.20, pace:215, hr:152, dur:'11:28' }
  ];
  // sort by date desc (already)

  function paceStr(s) {
    var m = Math.floor(s/60), sec = s%60;
    return m+':'+(sec<10?'0':'')+sec;
  }

  var chartRuns = echarts.init(document.getElementById('chart-runs'), null, { renderer: 'svg' });
  chartRuns.setOption({
    animation: false,
    tooltip: {
      trigger: 'axis', axisPointer:{ type:'shadow' }, appendToBody: true,
      backgroundColor: bg2, borderColor: rule, textStyle: { color: ink, fontSize: 12 },
      formatter: function(p) {
        var row = runs[runs.length-1-p[0].dataIndex];
        return '<b>'+ row.date+'</b> '+ row.type+'<br>'+
               '距离：'+ row.dist+' km<br>'+
               '配速：<b>'+ paceStr(row.pace)+' /km</b><br>'+
               '平均心率：'+ row.hr+' bpm';
      }
    },
    grid: { left: 40, right: 48, top: 12, bottom: 12 },
    xAxis: { show:false },
    yAxis: {
      type:'category',
      data: runs.slice().reverse().map(function(r,i){
        return r.date+' · '+ r.type;
      }),
      axisLine:{ show:false }, axisTick:{ show:false },
      axisLabel:{ color: muted, fontSize: 11 }
    },
    series: [{
      type:'bar', barMaxWidth: 16,
      data: runs.slice().reverse().map(function(r){ return r.pace; }),
      itemStyle: {
        color: function(p) {
          var v = p.value;
          // faster pace (lower number) = accent
          return v < 210 ? accent : (v < 260 ? accent2+'cc' : accent2+'66');
        },
        borderRadius: [0, 4, 4, 0]
      },
      label: {
        show: true, position: 'right',
        formatter: function(p){ return paceStr(p.value)+' /km'; },
        color: ink, fontSize: 11, fontWeight: 600
      }
    }]
  });
  window.addEventListener('resize', function(){ chartRuns.resize(); });

})();
