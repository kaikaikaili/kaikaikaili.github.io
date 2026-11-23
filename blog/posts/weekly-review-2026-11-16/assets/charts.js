// COROS Weekly Review — Charts (2026-11-16 → 2026-11-22)
(function() {
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim();
  var accent2 = style.getPropertyValue('--accent2').trim();
  var warn = style.getPropertyValue('--warn').trim() || '#f9b24a';
  var ink = style.getPropertyValue('--ink').trim();
  var muted = style.getPropertyValue('--muted').trim();
  var rule = style.getPropertyValue('--rule').trim();
  var bg2 = style.getPropertyValue('--bg2').trim();

  var dates = ['11-16','11-17','11-18','11-19','11-20','11-21','11-22'];
  var wd = ['周一','周二','周三','周四','周五','周六','周日'];

  function axisX() {
    return {
      type: 'category', data: dates,
      axisLine: { lineStyle: { color: rule } },
      axisLabel: { color: muted, fontSize: 11, formatter: function(v, i) { return v + '\n' + wd[i]; } }
    };
  }
  function axisY(opt) {
    var o = opt || {};
    return {
      type: 'value', name: o.name || '',
      nameTextStyle: { color: muted, fontSize: 11, padding: [0, 0, 0, 30] },
      min: o.min, max: o.max,
      axisLine: { show: false }, axisTick: { show: false },
      splitLine: { lineStyle: { color: rule, type: 'dashed' } },
      axisLabel: { color: muted, fontSize: 11 }
    };
  }
  function tip() {
    return {
      trigger: 'axis', appendToBody: true,
      backgroundColor: bg2, borderColor: rule, textStyle: { color: ink, fontSize: 12 }
    };
  }

  // ===== Chart: Weekly Volume (bar) =====
  var volumeData = [7.09, 12.00, 3.19, 0, 2.56, 9.45, 20.01];
  var chartVol = echarts.init(document.getElementById('chart-volume'), null, { renderer: 'svg' });
  chartVol.setOption({
    animation: false,
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' }, appendToBody: true,
      backgroundColor: bg2, borderColor: rule, textStyle: { color: ink, fontSize: 12 },
      formatter: function(p) {
        var v = p[0].value;
        return '<b>' + p[0].axisValue + ' ' + wd[p[0].dataIndex] + '</b><br>当日跑量：<b>' +
          (v === 0 ? '0 km（休息）' : v.toFixed(2) + ' km') + '</b>';
      }
    },
    grid: { left: 40, right: 16, top: 30, bottom: 40 },
    xAxis: axisX(),
    yAxis: axisY({ name: 'km' }),
    series: [{
      type: 'bar', barMaxWidth: 30,
      data: volumeData.map(function(v) {
        return {
          value: v,
          itemStyle: { color: v === 0 ? rule : (v >= 13 ? accent : accent2), borderRadius: [4, 4, 0, 0] }
        };
      }),
      label: {
        show: true, position: 'top', color: ink, fontSize: 11, fontWeight: 600,
        formatter: function(p) { return p.value === 0 ? '休' : p.value.toFixed(2); }
      }
    }]
  });
  window.addEventListener('resize', function() { chartVol.resize(); });

  // ===== Chart: Daily Sleep Stages (stacked bar) =====
  var sleepData = [
    { d:'11-16', total:476, deep:85, light:248, rem:117, awake:26, score:89 },
    { d:'11-17', total:487, deep:61, light:279, rem:128, awake:19, score:90 },
    { d:'11-18', total:474, deep:67, light:249, rem:128, awake:30, score:82 },
    { d:'11-19', total:471, deep:56, light:253, rem:149, awake:13, score:88 },
    { d:'11-20', total:454, deep:48, light:238, rem:145, awake:23, score:81 },
    { d:'11-21', total:497, deep:34, light:297, rem:132, awake:34, score:77 },
    { d:'11-22', total:472, deep:48, light:315, rem:81,  awake:28, score:85 }
  ];
  var chartSleep = echarts.init(document.getElementById('chart-sleep'), null, { renderer: 'svg' });
  chartSleep.setOption({
    animation: false,
    tooltip: {
      trigger: 'axis', appendToBody: true,
      backgroundColor: bg2, borderColor: rule, textStyle: { color: ink, fontSize: 12 },
      axisPointer: { type: 'shadow' },
      formatter: function(p) {
        var row = sleepData.find(function(x) { return x.d === p[0].axisValue; });
        if (!row) return p[0].axisValue;
        var hrs = Math.floor(row.total / 60), mins = row.total % 60;
        return '<b>' + row.d + '</b> 睡眠<br>' +
               '总时长：' + hrs + 'h ' + mins + 'min<br>' +
               '深睡：' + row.deep + 'min | 浅睡：' + row.light + 'min<br>' +
               'REM：' + row.rem + 'min | 清醒：' + row.awake + 'min<br>' +
               '睡眠评分：<b>' + row.score + '</b>';
      }
    },
    legend: { data: ['深睡', '浅睡', 'REM', '清醒'], textStyle: { color: muted, fontSize: 11 }, top: 0, right: 0 },
    grid: { left: 36, right: 16, top: 40, bottom: 42 },
    xAxis: axisX(),
    yAxis: axisY({ name: '分钟' }),
    series: [
      { name:'深睡', type:'bar', stack:'s', data: sleepData.map(function(x){ return x.deep; }), itemStyle:{ color: accent }, barMaxWidth: 28 },
      { name:'浅睡', type:'bar', stack:'s', data: sleepData.map(function(x){ return x.light; }), itemStyle:{ color: accent2 } },
      { name:'REM', type:'bar', stack:'s', data: sleepData.map(function(x){ return x.rem; }), itemStyle:{ color: accent2+'80' } },
      { name:'清醒', type:'bar', stack:'s', data: sleepData.map(function(x){ return x.awake; }), itemStyle:{ color: rule } }
    ]
  });
  window.addEventListener('resize', function() { chartSleep.resize(); });

  // ===== Chart: Sleep Score (line) =====
  var chartScore = echarts.init(document.getElementById('chart-sleep-score'), null, { renderer: 'svg' });
  chartScore.setOption({
    animation: false,
    tooltip: { trigger: 'axis', appendToBody: true, backgroundColor: bg2, borderColor: rule, textStyle: { color: ink, fontSize: 12 } },
    grid: { left: 36, right: 16, top: 26, bottom: 36 },
    xAxis: axisX(),
    yAxis: axisY({ min: 70, max: 95 }),
    series: [{
      type: 'line', smooth: true, showSymbol: true, symbolSize: 8,
      data: sleepData.map(function(x) { return x.score; }),
      lineStyle: { color: accent, width: 3 },
      itemStyle: { color: accent, borderColor: '#fff', borderWidth: 2 },
      areaStyle: { color: { type:'linear', x:0, y:0, x2:0, y2:1, colorStops: [
        { offset: 0, color: accent+'40' }, { offset: 1, color: accent+'05' }
      ]}},
      label: { show: true, position: 'top', color: accent, fontSize: 11, fontWeight: 600 }
    }]
  });
  window.addEventListener('resize', function() { chartScore.resize(); });

  // ===== Chart: Sleep HRV (bar + baseline) =====
  var hrvData = [
    { d:'11-16', val:83,  base:98, low:90, high:106, status:'偏低' },
    { d:'11-17', val:95,  base:97, low:85, high:109, status:'正常' },
    { d:'11-18', val:103, base:97, low:85, high:109, status:'正常' },
    { d:'11-19', val:123, base:97, low:85, high:109, status:'偏高' },
    { d:'11-20', val:109, base:98, low:86, high:110, status:'偏高' },
    { d:'11-21', val:103, base:98, low:86, high:110, status:'正常' },
    { d:'11-22', val:98,  base:99, low:87, high:111, status:'正常' }
  ];
  var chartHrv = echarts.init(document.getElementById('chart-hrv'), null, { renderer: 'svg' });
  chartHrv.setOption({
    animation: false,
    tooltip: {
      trigger: 'axis', appendToBody: true,
      backgroundColor: bg2, borderColor: rule, textStyle: { color: ink, fontSize: 12 },
      formatter: function(p) {
        var row = hrvData.find(function(x) { return x.d === p[0].axisValue; });
        if (!row) return p[0].axisValue;
        return '<b>' + row.d + '</b><br>HRV：<b>' + row.val + ' ms</b>（' + row.status + '）<br>' +
               '基线：' + row.base + ' ms | 正常区间：' + row.low + '–' + row.high;
      }
    },
    grid: { left: 40, right: 16, top: 36, bottom: 42 },
    xAxis: axisX(),
    yAxis: axisY({ name: 'ms', min: 60, max: 135 }),
    series: [{
      name: 'HRV', type: 'bar', barMaxWidth: 24,
      data: hrvData.map(function(x) {
        return {
          value: x.val,
          itemStyle: { color: x.status === '偏高' ? accent : (x.status === '偏低' ? warn : accent+'cc') }
        };
      }),
      label: { show: true, position: 'top', color: ink, fontSize: 11, fontWeight: 600 },
      markLine: {
        silent: true, symbol: 'none',
        lineStyle: { color: rule, type: 'dashed', width: 1 },
        data: [{ yAxis: 98, label: { formatter: '基线 97–99ms', color: muted, fontSize: 10 } }]
      }
    }]
  });
  window.addEventListener('resize', function() { chartHrv.resize(); });

  // ===== Chart: RHR (line, 11-22 missing) =====
  var rhrData = [
    { d:'11-16', val:44 }, { d:'11-17', val:43 }, { d:'11-18', val:49 },
    { d:'11-19', val:47 }, { d:'11-20', val:44 }, { d:'11-21', val:46 },
    { d:'11-22', val:null }
  ];
  var chartRhr = echarts.init(document.getElementById('chart-rhr'), null, { renderer: 'svg' });
  chartRhr.setOption({
    animation: false,
    tooltip: {
      trigger: 'axis', appendToBody: true,
      backgroundColor: bg2, borderColor: rule, textStyle: { color: ink, fontSize: 12 },
      formatter: function(p) {
        var v = p[0].value;
        return '<b>' + p[0].axisValue + '</b><br>静息心率：' +
          (v == null ? '未返回（缺）' : '<b>' + v + ' bpm</b>');
      }
    },
    grid: { left: 36, right: 16, top: 26, bottom: 36 },
    xAxis: axisX(),
    yAxis: axisY({ min: 40, max: 52, name: 'bpm' }),
    series: [{
      type: 'line', smooth: true, symbolSize: 8, showSymbol: true, connectNulls: false,
      data: rhrData.map(function(x) { return x.val; }),
      lineStyle: { color: accent2, width: 3 },
      itemStyle: { color: accent2, borderColor: '#fff', borderWidth: 2 },
      areaStyle: { color: { type:'linear', x:0, y:0, x2:0, y2:1, colorStops: [
        { offset: 0, color: accent2+'40' }, { offset: 1, color: accent2+'05' }
      ]}},
      label: {
        show: true, position: 'top', color: accent2, fontSize: 11, fontWeight: 600,
        formatter: function(p) { return p.value == null ? '' : p.value + ' bpm'; }
      }
    }]
  });
  window.addEventListener('resize', function() { chartRhr.resize(); });

  // ===== Chart: Stress Level (bar, 11-22 partial excluded) =====
  var stressData = [
    { d:'11-16', v:27 }, { d:'11-17', v:32 }, { d:'11-18', v:32 },
    { d:'11-19', v:26 }, { d:'11-20', v:40 }, { d:'11-21', v:39 },
    { d:'11-22', v:null }
  ];
  var chartStress = echarts.init(document.getElementById('chart-stress'), null, { renderer: 'svg' });
  chartStress.setOption({
    animation: false,
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' }, appendToBody: true,
      backgroundColor: bg2, borderColor: rule, textStyle: { color: ink, fontSize: 12 },
      formatter: function(p) {
        var v = p[0].value;
        return '<b>' + p[0].axisValue + '</b><br>日均压力：' +
          (v == null ? '未结算（缺）' : '<b>' + v + '</b>');
      }
    },
    grid: { left: 36, right: 16, top: 26, bottom: 36 },
    xAxis: axisX(),
    yAxis: axisY({ min: 20, max: 45 }),
    series: [{
      type: 'bar', barMaxWidth: 28,
      data: stressData.map(function(x) {
        return { value: x.v, itemStyle: { color: x.v >= 40 ? warn : (x.v == null ? rule : accent) } };
      }),
      label: {
        show: true, position: 'top', color: muted, fontSize: 11,
        formatter: function(p) { return p.value == null ? '未结算' : p.value; }
      }
    }]
  });
  window.addEventListener('resize', function() { chartStress.resize(); });

  // ===== Chart: Training Load (STL/LTL lines) =====
  var loadData = [
    { d:'11-16', stl:37, ltl:60, ratio:0.61, comment:'Performance' },
    { d:'11-17', stl:49, ltl:61, ratio:0.80, comment:'Maintaining' },
    { d:'11-18', stl:45, ltl:61, ratio:0.73, comment:'Performance' },
    { d:'11-19', stl:39, ltl:60, ratio:0.65, comment:'Performance' },
    { d:'11-20', stl:44, ltl:60, ratio:0.73, comment:'Performance' },
    { d:'11-21', stl:55, ltl:62, ratio:0.88, comment:'Maintaining' },
    { d:'11-22', stl:47, ltl:60, ratio:0.78, comment:'Performance' }
  ];
  var chartLoad = echarts.init(document.getElementById('chart-load'), null, { renderer: 'svg' });
  chartLoad.setOption({
    animation: false,
    tooltip: {
      trigger: 'axis', appendToBody: true,
      backgroundColor: bg2, borderColor: rule, textStyle: { color: ink, fontSize: 12 },
      formatter: function(p) {
        var row = loadData.find(function(x) { return x.d === p[0].axisValue; });
        if (!row) return p[0].axisValue;
        return '<b>' + row.d + '</b><br>STL：' + row.stl + ' | LTL：' + row.ltl +
               '<br>负荷比：<b>' + row.ratio.toFixed(2) + '</b>（' + row.comment + '）';
      }
    },
    legend: { data: ['短期负荷 STL', '长期负荷 LTL'], textStyle: { color: muted, fontSize: 11 }, top: 0, right: 0 },
    grid: { left: 40, right: 16, top: 40, bottom: 42 },
    xAxis: axisX(),
    yAxis: axisY(),
    series: [
      { name:'短期负荷 STL', type:'line', smooth:true, symbolSize:7,
        data: loadData.map(function(x){ return x.stl; }),
        lineStyle:{ color: accent, width:3 }, itemStyle:{ color: accent },
        label: { show: true, position: 'top', color: accent, fontSize: 10 } },
      { name:'长期负荷 LTL', type:'line', smooth:true, symbolSize:6,
        data: loadData.map(function(x){ return x.ltl; }),
        lineStyle:{ color: accent2, width:2, type:'dashed' }, itemStyle:{ color: accent2 } }
    ]
  });
  window.addEventListener('resize', function() { chartLoad.resize(); });

  // ===== Charts: Per-run Pace & HR (horizontal bars, 11 sessions) =====
  // Sport records 2026-11-16 → 2026-11-22 (11 sessions, newest first)
  var runs = [
    { date:'11-22', wd:'周日', type:'赛道跑', dist:20.01, pace:288, hr:141, dur:'1:36:02', kcal:null },
    { date:'11-21', wd:'周六', type:'赛道跑', dist:3.19, pace:322, hr:134, dur:'17:07', kcal:214 },
    { date:'11-21', wd:'周六', type:'赛道跑', dist:3.00, pace:208, hr:175, dur:'10:26', kcal:201 },
    { date:'11-21', wd:'周六', type:'户外跑', dist:1.11, pace:358, hr:136, dur:'06:38', kcal:83 },
    { date:'11-21', wd:'周六', type:'户外跑', dist:1.14, pace:360, hr:140, dur:'06:51', kcal:87 },
    { date:'11-21', wd:'周六', type:'户外跑', dist:1.01, pace:372, hr:132, dur:'06:15', kcal:77 },
    { date:'11-20', wd:'周五', type:'赛道跑', dist:1.51, pace:190, hr:176, dur:'04:46', kcal:96 },
    { date:'11-20', wd:'周五', type:'户外跑', dist:1.05, pace:358, hr:134, dur:'06:16', kcal:77 },
    { date:'11-18', wd:'周三', type:'赛道跑', dist:3.19, pace:305, hr:139, dur:'16:14', kcal:215 },
    { date:'11-17', wd:'周二', type:'赛道跑', dist:12.00, pace:257, hr:154, dur:'51:29', kcal:788 },
    { date:'11-16', wd:'周一', type:'赛道跑', dist:7.09, pace:304, hr:139, dur:'35:52', kcal:471 }
  ];

  function paceStr(s) {
    var m = Math.floor(s / 60), sec = s % 60;
    return m + ':' + (sec < 10 ? '0' : '') + sec;
  }
  function runTip(p) {
    var row = runs[runs.length - 1 - p[0].dataIndex];
    var kcal = row.kcal == null ? '未返回' : row.kcal + ' kcal';
    return '<b>' + row.date + ' ' + row.wd + '</b> · ' + row.type + '<br>' +
           '距离：' + row.dist.toFixed(2) + ' km | 时长：' + row.dur + '<br>' +
           '配速：<b>' + paceStr(row.pace) + ' /km</b><br>' +
           '平均心率：' + row.hr + ' bpm | 消耗：' + kcal;
  }
  function runCats() {
    return runs.slice().reverse().map(function(r) { return r.date + ' · ' + r.type; });
  }

  var chartRuns = echarts.init(document.getElementById('chart-runs'), null, { renderer: 'svg' });
  chartRuns.setOption({
    animation: false,
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' }, appendToBody: true,
      backgroundColor: bg2, borderColor: rule, textStyle: { color: ink, fontSize: 12 },
      formatter: runTip
    },
    grid: { left: 84, right: 78, top: 12, bottom: 12 },
    xAxis: { show: false },
    yAxis: {
      type: 'category', data: runCats(),
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: { color: muted, fontSize: 11 }
    },
    series: [{
      type: 'bar', barMaxWidth: 14,
      data: runs.slice().reverse().map(function(r) { return r.pace; }),
      itemStyle: {
        color: function(p) {
          var v = p.value;
          return v < 210 ? accent : (v < 262 ? accent2+'cc' : accent2+'66');
        },
        borderRadius: [0, 4, 4, 0]
      },
      label: {
        show: true, position: 'right',
        formatter: function(p) { return paceStr(p.value) + ' /km'; },
        color: ink, fontSize: 11, fontWeight: 600
      }
    }]
  });
  window.addEventListener('resize', function() { chartRuns.resize(); });

  var chartHr = echarts.init(document.getElementById('chart-hr'), null, { renderer: 'svg' });
  chartHr.setOption({
    animation: false,
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' }, appendToBody: true,
      backgroundColor: bg2, borderColor: rule, textStyle: { color: ink, fontSize: 12 },
      formatter: runTip
    },
    grid: { left: 84, right: 78, top: 12, bottom: 12 },
    xAxis: { show: false },
    yAxis: {
      type: 'category', data: runCats(),
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: { color: muted, fontSize: 11 }
    },
    series: [{
      type: 'bar', barMaxWidth: 14,
      data: runs.slice().reverse().map(function(r) { return r.hr; }),
      itemStyle: {
        color: function(p) {
          var v = p.value;
          return v >= 170 ? warn : (v >= 150 ? accent : accent2);
        },
        borderRadius: [0, 4, 4, 0]
      },
      label: {
        show: true, position: 'right',
        formatter: function(p) { return p.value + ' bpm'; },
        color: ink, fontSize: 11, fontWeight: 600
      }
    }]
  });
  window.addEventListener('resize', function() { chartHr.resize(); });

})();
