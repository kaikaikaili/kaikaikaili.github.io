#!/usr/bin/env python3
"""2026 年度跑步海报生成器。

用法: python3 gen_poster.py <coros_records.txt> [输出路径]
输入: COROS MCP querySportRecords 的持久化输出文件（含 Outdoor/Track/Indoor/Trail Run 记录的纯文本）
输出: 印刷级 SVG 海报（1200x1697, 暗底玻璃风, 与站点设计系统一致）
"""
import json, re, sys, os, datetime, collections

W, H = 1200, 1697
M = 80
INK, DIM, MUTED, RULE = '#e8ecf4', '#b8c0d0', '#7a8398', '#2a3247'
ACCENT, ACCENT2 = '#3d9bff', '#22c39a'
TIERS = ['#1e2536', '#1b3a5c', '#24568c', '#3d9bff', '#8fc7ff']

def parse(src_path):
    raw = open(src_path).read()
    m = re.search(r'\[\{"type":"text","text":(".*")\}\]', raw, re.S)
    src = json.loads(m.group(1)) if m else raw
    if isinstance(src, str) and src.startswith('"'):
        src = json.loads(src)
    records = []
    for r in re.split(r'\n\d+\.\s+', src)[1:]:
        typ = re.match(r'(Outdoor Run|Track Run|Indoor Run|Trail Run) — (\d{4}-\d{2}-\d{2})', r)
        dur = re.search(r'Duration:\s*([\d:]+)', r)
        dist = re.search(r'Distance:\s*([\d.]+)\s*(km|m)\b', r)
        pace = re.search(r'Average Pace:\s*(\d+):(\d+)\s*/km', r)
        hr = re.search(r'Avg HR:\s*(\d+)\s*bpm', r)
        if not (typ and dur and dist and pace):
            continue
        parts = [int(v) for v in dur.group(1).split(':')]
        while len(parts) < 3:
            parts.insert(0, 0)
        km = float(dist.group(1)) if dist.group(2) == 'km' else float(dist.group(1)) / 1000
        records.append({
            'date': typ.group(2),
            'type': {'Outdoor Run': '户外跑', 'Track Run': '赛道跑', 'Indoor Run': '跑步机', 'Trail Run': '越野跑'}[typ.group(1)],
            'km': round(km, 2),
            'dur_s': parts[0]*3600 + parts[1]*60 + parts[2],
            'pace_s': int(pace.group(1))*60 + int(pace.group(2)),
            'hr': int(hr.group(1)) if hr else None,
        })
    return records

def tier(km):
    if km <= 0: return TIERS[0]
    if km < 3: return TIERS[1]
    if km < 7: return TIERS[2]
    if km < 13: return TIERS[3]
    return TIERS[4]

def pace_str(s):
    return f'{s//60}:{s%60:02d}'

def main():
    src_path = sys.argv[1]
    year = sys.argv[2] if len(sys.argv) > 2 else str(datetime.date.today().year)
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(__file__), '..', f'{year}-poster.svg')
    records = [r for r in parse(src_path) if r['date'].startswith(year)]
    assert records, 'no records parsed'
    today = records[-1]['date']

    weeks = collections.OrderedDict()
    for x in records:
        d = datetime.date.fromisoformat(x['date'])
        mon = (d - datetime.timedelta(days=d.weekday())).isoformat()
        w = weeks.setdefault(mon, {'km': 0, 'n': 0})
        w['km'] += x['km']; w['n'] += 1
    max_week_km = max(w['km'] for w in weeks.values())
    heatmap = collections.defaultdict(float)
    for x in records:
        heatmap[x['date']] += x['km']
    total_km = round(sum(x['km'] for x in records), 1)
    active_days = len(heatmap)
    longest = max(records, key=lambda x: x['km'])
    best5k = sorted([x for x in records if x['km'] >= 5], key=lambda x: x['pace_s'])[0]
    days = sorted(set(x['date'] for x in records))
    streak = cur = 1
    for i in range(1, len(days)):
        gap = (datetime.date.fromisoformat(days[i]) - datetime.date.fromisoformat(days[i-1])).days
        cur = cur + 1 if gap == 1 else 1
        streak = max(streak, cur)
    tt = collections.defaultdict(lambda: [0, 0])
    for x in records:
        tt[x['type']][0] += x['km']; tt[x['type']][1] += 1

    S = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         '''<defs>
<linearGradient id="heroG" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="#3d9bff" stop-opacity="0.16"/>
  <stop offset="1" stop-color="#22c39a" stop-opacity="0.10"/>
</linearGradient>
<linearGradient id="barG" x1="0" y1="1" x2="0" y2="0">
  <stop offset="0" stop-color="#24568c"/><stop offset="1" stop-color="#3d9bff"/>
</linearGradient>
</defs>''',
         f'<rect width="{W}" height="{H}" fill="#0f1420"/>',
         f'<rect width="{W}" height="{H}" fill="url(#heroG)" opacity="0.5"/>']

    def txt(x, y, s, size, fill, weight='400', ls='0', anchor='start'):
        S.append(f'<text x="{x}" y="{y}" font-family="Work Sans,PingFang SC,sans-serif" font-size="{size}" fill="{fill}" font-weight="{weight}" letter-spacing="{ls}" text-anchor="{anchor}">{s}</text>')

    def istxt(x, y, s, size, fill, weight='400', ls='0', anchor='start'):
        S.append(f'<text x="{x}" y="{y}" font-family="Instrument Sans,Work Sans,sans-serif" font-size="{size}" fill="{fill}" font-weight="{weight}" letter-spacing="{ls}" text-anchor="{anchor}">{s}</text>')

    y = 108
    istxt(M, y, 'RUNNING · YEAR IN REVIEW', 15, ACCENT, '700', '4')
    istxt(W-M, y, year, 15, ACCENT2, '700', '4', 'end')
    y += 64
    txt(M, y, '我的一年跑步', 52, INK, '700')
    y += 40
    txt(M, y, f'南京大学 · COROS PACE 3 · {year}-01-01 → {today}', 15, MUTED)
    y += 96
    istxt(M, y, f'{total_km:g}', 120, ACCENT, '700', '-2')
    istxt(M+300, y-14, 'km', 30, DIM)
    istxt(M+300, y+14, '总里程', 16, MUTED)
    y += 58
    x = M
    for v, l in [(len(records), '训练次数'), (round(sum(r['dur_s'] for r in records)/3600, 1), '运动时长 · h'),
                 (active_days, '跑步日'), (len(weeks), '训练周'), (f'{max_week_km:.1f}', '最大周跑量 · km')]:
        istxt(x, y, str(v), 26, INK, '700')
        txt(x, y+22, l, 12, MUTED)
        x += 208

    y += 92
    istxt(M, y, '月度跑量', 17, INK, '700', '1')
    months = collections.defaultdict(float)
    for x2 in records:
        months[x2['date'][:7]] += x2['km']
    last_month = int(today[5:7])
    mKm = [months.get(f'{year}-{i:02d}', 0) for i in range(1, last_month+1)]
    mx = max(mKm)
    chart_h, bw, gap = 150, 62, (W-2*M-last_month*62)//max(last_month-1, 1)
    by0 = y + 8 + chart_h + 26
    for i, v in enumerate(mKm):
        bx = M + i*(bw+gap)
        if v:
            bh = v/mx*chart_h
            S.append(f'<rect x="{bx}" y="{by0-bh:.0f}" width="{bw}" height="{bh:.0f}" rx="4" fill="url(#barG)"/>')
            istxt(bx+bw/2, by0-bh-10, f'{v:.0f}', 13, DIM, '600', '0', 'middle')
        else:
            S.append(f'<rect x="{bx}" y="{by0-3}" width="{bw}" height="3" rx="1.5" fill="{RULE}"/>')
            txt(bx+bw/2, by0-12, '休', 12, MUTED, '400', '0', 'middle')
        istxt(bx+bw/2, by0+20, f'{i+1}月', 12, MUTED, '400', '0', 'middle')
    S.append(f'<line x1="{M}" y1="{by0}" x2="{W-M}" y2="{by0}" stroke="{RULE}"/>')

    y = by0 + 64
    istxt(M, y, '跑步日历', 17, INK, '700', '1')
    txt(W-M, y, '颜色越亮 · 跑得越多', 12, MUTED, '400', '0', 'end')
    cell, cgap = 15, 4
    step = cell + cgap
    first = datetime.date(int(year), 1, 1)
    start = first - datetime.timedelta(days=first.weekday())
    end = datetime.date.fromisoformat(today)
    hx0, hy0 = M, y + 18
    for r, lab in [(0, '一'), (2, '三'), (4, '五')]:
        txt(hx0-18, hy0 + (r+1)*step + cell*0.75, lab, 10, MUTED, '400', '0', 'end')
    cur_d, col = start, 0
    last_m = 0
    while cur_d <= end:
        if cur_d.month != last_m and cur_d.day <= 7:
            istxt(hx0+col*step, hy0-8, f'{cur_d.month}月', 11, MUTED)
        last_m = cur_d.month
        for rr in range(7):
            day = cur_d + datetime.timedelta(days=rr)
            if day > end:
                break
            km = heatmap.get(day.isoformat(), 0)
            hl = ' stroke="#3d9bff" stroke-opacity="0.5"' if day == end else ''
            S.append(f'<rect x="{hx0+col*step}" y="{hy0+rr*step}" width="{cell}" height="{cell}" rx="3" fill="{tier(km)}"{hl}/>')
        cur_d += datetime.timedelta(days=7); col += 1
    leg_x = W-M-5*step
    ly = hy0 + 7*step + 22
    txt(leg_x-26, ly+cell-2, '少', 10, MUTED, '400', '0', 'end')
    for i, c in enumerate(TIERS):
        S.append(f'<rect x="{leg_x+i*step}" y="{ly}" width="{cell}" height="{cell}" rx="3" fill="{c}"/>')
    txt(leg_x+5*step+14, ly+cell-2, '多', 10, MUTED, '400', '0', 'end')

    y = ly + 66
    istxt(M, y, '年度亮点', 17, INK, '700', '1')
    y += 40
    hl = [(f'{longest["km"]:g} km', '最长单次', f'{longest["date"][5:].replace("-", " 月 ").replace(" 月 ", "-")} · 年度最长距离'),
          (f'{pace_str(best5k["pace_s"])} /km', '最佳 5km 配速', f'{best5k["date"][5:].replace("-", " 月 ")} · {best5k["km"]:g} km'),
          (f'{max_week_km:.1f} km', '最大周跑量', f'{min(weeks, key=lambda k: abs(float(max_week_km) - weeks[k]["km"]))[5:]} 当周'),
          (f'{streak} 天', '最长连续跑步', f'全年 {active_days} 个跑步日')]
    cw = (W-2*M-3*24)/4
    x = M
    for v, l, s in hl:
        S.append(f'<rect x="{x:.0f}" y="{y-32:.0f}" width="{cw:.0f}" height="112" rx="10" fill="#171d2c" stroke="{RULE}"/>')
        istxt(x+20, y+4, v, 24, ACCENT, '700')
        txt(x+20, y+34, l, 13, INK, '600')
        txt(x+20, y+58, s, 11, MUTED)
        x += cw + 24

    y += 130
    istxt(M, y, '场地分布', 17, INK, '700', '1')
    y += 26
    barw = W-2*M
    order = sorted(tt.items(), key=lambda kv: -kv[1][0])
    xoff = M
    colors = [ACCENT, ACCENT2, '#f9b24a', '#ff6b6b']
    for i, (k, (km, n)) in enumerate(order):
        seg = barw*km/total_km
        S.append(f'<rect x="{xoff:.0f}" y="{y}" width="{seg:.0f}" height="18" rx="4" fill="{colors[i % 4]}"/>')
        txt(xoff, y+40, f'{k} {km:.1f} km · {n} 次', 12, colors[i % 4], '600')
        xoff += seg + 6
    y += 92
    istxt(M, y, '竞技水平', 17, INK, '700', '1')
    txt(W-M, y-4, '见 lkk31.xyz/running', 11, MUTED)
    fy = H-64
    S.append(f'<line x1="{M}" y1="{fy-34}" x2="{W-M}" y2="{fy-34}" stroke="{RULE}"/>')
    istxt(M, fy, f'COROS · Year in Sport {year} · generated {datetime.date.today()}', 12, MUTED, '400', '1')
    istxt(M, fy+22, '数据已脱敏 · lkk31.xyz/running', 12, MUTED, '400', '1')
    istxt(W-M, fy+22, 'LKK', 14, DIM, '700', '4', 'end')
    S.append('</svg>')
    open(out, 'w').write('\n'.join(S))
    print(f'poster written: {os.path.abspath(out)} | {total_km} km / {len(records)} runs / {active_days} days')

if __name__ == '__main__':
    main()
