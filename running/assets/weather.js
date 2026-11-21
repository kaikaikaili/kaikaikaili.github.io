// 晨跑适跑指数 — Open-Meteo 实时气象（南京），纯前端计算
(function() {
  var API = 'https://api.open-meteo.com/v1/forecast?latitude=32.05&longitude=118.78'
    + '&current=temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,precipitation,weather_code'
    + '&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max'
    + '&timezone=Asia/Shanghai&forecast_days=4';

  // WMO weather code → 中文描述
  var WMO = {0:'晴',1:'大部晴朗',2:'局部多云',3:'阴',45:'雾',48:'雾凇',
    51:'毛毛雨',53:'毛毛雨',55:'浓毛毛雨',56:'冻毛毛雨',57:'强冻毛毛雨',
    61:'小雨',63:'中雨',65:'大雨',66:'冻雨',67:'强冻雨',
    71:'小雪',73:'中雪',75:'大雪',77:'雪粒',
    80:'阵雨',81:'阵雨',82:'强阵雨',85:'阵雪',86:'强阵雪',
    95:'雷阵雨',96:'雷阵雨伴冰雹',99:'强雷阵雨伴冰雹'};
  function wmoText(c) { return WMO[c] !== undefined ? WMO[c] : '—'; }

  function grade(score) {
    if (score >= 80) return { label: '极适宜', color: 'var(--accent2)' };
    if (score >= 65) return { label: '适宜',   color: 'var(--accent)' };
    if (score >= 50) return { label: '一般',   color: 'var(--warn)' };
    if (score >= 30) return { label: '欠佳',   color: 'var(--warn)' };
    return { label: '不建议', color: 'var(--danger)' };
  }

  // 适宜度评分（0-100）：温度 / 风速 / 降水 / 湿度 / 天气现象
  function score(c) {
    var T = c.temperature_2m, W = c.wind_speed_10m, RH = c.relative_humidity_2m, P = c.precipitation, code = c.weather_code;
    var s = 62, notes = [];
    // 温度：15–22°C 最优区间
    if (T >= 15 && T <= 22) { s += 20; }
    else if ((T >= 10 && T < 15) || (T > 22 && T <= 25)) { s += 14; }
    else if ((T >= 5 && T < 10) || (T > 25 && T <= 28)) { s += 6; }
    else if (T < 0 || T > 32) { s -= 15; }
    else { s -= 4; }
    if (T > 28) notes.push('气温偏高，注意补水与补盐');
    if (T < 5 && T >= 0) notes.push('低温刺激，充分热身再出发');
    if (T < 0) notes.push('冰点以下，防滑防冻伤');
    // 风速
    if (W <= 10) s += 10;
    else if (W <= 20) s += 4;
    else if (W <= 25) s -= 4;
    else { s -= 14; notes.push('风速较大，逆风段配速会明显掉'); }
    // 降水
    if (P > 0.5) { s -= 25; notes.push('正在降水，路面湿滑'); }
    else if (P > 0) { s -= 12; notes.push('有零星降水'); }
    // 湿度
    if (RH <= 60) s += 8;
    else if (RH <= 75) s += 3;
    else if (RH > 85) { s -= 6; notes.push('湿度大，散热效率低，体感更累'); }
    // 天气现象
    if (code === 0 || code === 1) s += 4;
    else if (code === 3 || code === 45 || code === 48) s -= 3;
    else if ((code >= 51 && code <= 67) || (code >= 80 && code <= 82)) s -= 8;
    else if ((code >= 71 && code <= 77) || code === 85 || code === 86) { s -= 18; notes.push('降雪天气，慎跑'); }
    else if (code >= 95) { s -= 28; notes.push('对流天气，切勿外出跑步'); }
    return { value: Math.max(0, Math.min(100, Math.round(s))), notes: notes };
  }

  function adviceFrom(sc, c) {
    var tips = sc.notes.slice();
    var T = c.temperature_2m;
    if (tips.length === 0) {
      if (T >= 15 && T <= 22) tips.push('温度、风、湿度都在舒适区间，适合节奏跑或间歇训练');
      else tips.push('整体条件平稳，按计划完成训练即可');
    }
    if (c.wind_speed_10m > 20) tips.push('建议去程逆风、回程顺风，减少风阻消耗');
    if (c.relative_humidity_2m < 45 && T < 12) tips.push('空气干冷，注意呼吸道保暖');
    return tips.join('；') + '。';
  }

  function render(data) {
    var c = data.current, d = data.daily;
    var sc = score(c), g = grade(sc.value);
    document.getElementById('wx-score').textContent = sc.value;
    var arc = document.getElementById('wx-arc');
    var CIRC = 2 * Math.PI * 52;
    arc.setAttribute('stroke-dashoffset', CIRC * (1 - sc.value / 100));
    arc.setAttribute('stroke', g.color);
    var gr = document.getElementById('wx-grade');
    gr.textContent = g.label;
    gr.style.color = g.color;
    document.getElementById('wx-advice').textContent = adviceFrom(sc, c);

    document.getElementById('wx-temp').innerHTML = c.temperature_2m + '<small>°C</small>';
    document.getElementById('wx-feels').textContent = '体感 ' + c.apparent_temperature + ' °C';
    document.getElementById('wx-wind').innerHTML = c.wind_speed_10m + '<small>km/h</small>';
    document.getElementById('wx-precip').innerHTML = c.precipitation + '<small>mm</small>';
    document.getElementById('wx-prob').textContent = '今日降水概率 ' + d.precipitation_probability_max[0] + '%';
    document.getElementById('wx-rh').innerHTML = c.relative_humidity_2m + '<small>%</small>';
    document.getElementById('wx-rh-sub').textContent = c.relative_humidity_2m <= 70 ? '干爽利于散热' : '偏湿';
    document.getElementById('wx-desc').textContent = wmoText(c.weather_code);
    document.getElementById('wx-now').textContent = c.time.replace('T', ' ') + ' 当地时';

    // 未来 3 天
    var wd = ['周日','周一','周二','周三','周四','周五','周六'];
    var fc = document.getElementById('wx-fc');
    fc.innerHTML = '';
    for (var i = 1; i <= 3; i++) {
      var dt = new Date(d.time[i] + 'T12:00:00');
      var el = document.createElement('div');
      el.className = 'wx-fc-day';
      el.innerHTML = '<div class="wx-f-date">' + wd[dt.getDay()] + ' · ' + d.time[i].slice(5).replace('-', '/')
        + '</div><div class="wx-f-desc">' + wmoText(d.weather_code[i])
        + '</div><div class="wx-f-detail">' + d.temperature_2m_min[i] + '–' + d.temperature_2m_max[i] + ' °C<br>'
        + '降水 ' + d.precipitation_sum[i] + ' mm · ' + d.precipitation_probability_max[i] + '%<br>'
        + '风 ' + d.wind_speed_10m_max[i] + ' km/h</div>';
      fc.appendChild(el);
    }
    document.getElementById('wx-src').textContent =
      '数据来源：Open-Meteo（ECMWF IFS 模式）· 南京 32.05°N 118.78°E · 更新于 '
      + new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  }

  fetch(API)
    .then(function(r){ return r.json(); })
    .then(render)
    .catch(function(e) {
      console.error('weather load failed', e);
      document.getElementById('wx-grade').textContent = '暂不可用';
      document.getElementById('wx-grade').style.color = 'var(--warn)';
      document.getElementById('wx-advice').textContent = '天气数据加载失败（Open-Meteo 接口异常），稍后刷新重试。';
    });
})();
