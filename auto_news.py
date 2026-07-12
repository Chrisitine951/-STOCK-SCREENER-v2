import os
import json
import time
import re
import requests
from datetime import datetime, timezone, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ── CONFIG ──
GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
SHEETS_CLIENT_EMAIL = os.environ['SHEETS_CLIENT_EMAIL']
SHEETS_PRIVATE_KEY = os.environ['SHEETS_PRIVATE_KEY'].replace('\\n', '\n')
SPREADSHEET_ID = '1Nw-qGajPuk0UEo6bbFtkOwenzw8JmqVyqkMqcNxlgsc'
NEWS_SHEET = '新聞分析'
APP_URL = 'https://chrisitine951.github.io/-STOCK-SCREENER-v2/'

# Telegram 推播（選用：沒設定 Secrets 就自動跳過，不影響其他流程）
TG_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TG_CHAT = os.environ.get('TELEGRAM_CHAT_ID', '')

# Taiwan time (UTC+8)
TW_TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TW_TZ)
TODAY = NOW.strftime('%Y/%m/%d')

def call_gemini(prompt, use_search=True):
    """Call Gemini API with model fallback (flash-lite -> flash) and retry-backoff."""
    models = ['gemini-3.1-flash-lite', 'gemini-3.5-flash']
    body = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': 0.3, 'maxOutputTokens': 8192}
    }
    if use_search:
        body['tools'] = [{'google_search': {}}]

    last_err = None
    for model in models:
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}'
        for attempt in range(3):
            try:
                resp = requests.post(url, json=body, timeout=120)
            except requests.RequestException as e:
                last_err = str(e)
                time.sleep(15)
                continue
            if resp.status_code == 200:
                data = resp.json()
                text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                if text:
                    return text
                last_err = 'empty response'
            elif resp.status_code in (429, 503):
                wait = (attempt + 1) * 30
                print(f'{model} rate limited (attempt {attempt+1}), waiting {wait}s...')
                time.sleep(wait)
                last_err = f'{resp.status_code}'
            else:
                last_err = f'{resp.status_code}: {resp.text[:200]}'
                break  # 非過載錯誤，換下一個模型
        print(f'{model} failed ({last_err}), trying next model...')
    raise Exception(f'All Gemini models failed. Last error: {last_err}')

def parse_json(raw):
    """Extract JSON from response text. Handles both object and array roots."""
    raw = raw.replace('```json', '').replace('```', '').strip()
    obj_match = re.search(r'\{[\s\S]*\}', raw)
    arr_match = re.search(r'\[[\s\S]*\]', raw)
    # 取起始位置較前面的那個（避免陣列開頭卻誤抓內部物件）
    candidates = [m for m in (obj_match, arr_match) if m]
    if not candidates:
        raise Exception('No JSON found in response')
    best = min(candidates, key=lambda m: m.start())
    return json.loads(best.group())

def get_sheets_service():
    creds_info = {
        'type': 'service_account',
        'client_email': SHEETS_CLIENT_EMAIL,
        'private_key': SHEETS_PRIVATE_KEY,
        'token_uri': 'https://oauth2.googleapis.com/token',
    }
    creds = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    return build('sheets', 'v4', credentials=creds)

def append_to_sheet(service, sheet_name, row):
    body = {'values': [row]}
    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f'{sheet_name}!A1',
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()
    print(f'✓ Appended to {sheet_name}')

def send_telegram(text):
    """Push daily report to Telegram. Silently skips if secrets not set."""
    if not TG_TOKEN or not TG_CHAT:
        print('Telegram not configured, skipping push')
        return
    try:
        resp = requests.post(
            f'https://api.telegram.org/bot{TG_TOKEN}/sendMessage',
            json={'chat_id': TG_CHAT, 'text': text, 'parse_mode': 'HTML',
                  'disable_web_page_preview': True},
            timeout=30
        )
        if resp.status_code == 200:
            print('✓ Telegram push sent')
        else:
            print(f'✗ Telegram push failed: {resp.status_code} {resp.text[:150]}')
    except Exception as e:
        print(f'✗ Telegram push error: {e}')

# ══════════════════════════════════════════
# 持倉：解析 portfolio.js + 抓報價 + 到價提醒
# ══════════════════════════════════════════
def load_portfolio():
    """Parse portfolio.js (regex-based, tolerant to field order). Returns list of stock dicts."""
    try:
        txt = open('portfolio.js', encoding='utf-8').read()
    except FileNotFoundError:
        print('portfolio.js not found, skipping portfolio section')
        return []
    # 先剝除註解，避免把說明範例當成持股
    txt = re.sub(r'/\*[\s\S]*?\*/', '', txt)
    txt = re.sub(r'//[^\n]*', '', txt)
    stocks = []
    # group labels with their positions
    group_labels = [(m.start(), m.group(1)) for m in re.finditer(r"label:\s*'([^']+)'", txt)]
    for m in re.finditer(r'\{[^{}]*ticker:[^{}]*\}', txt):
        block, pos = m.group(), m.start()
        def grab(pattern, cast=str):
            mm = re.search(pattern, block)
            return cast(mm.group(1)) if mm else None
        s = {
            'ticker': grab(r"ticker:\s*'([^']+)'"),
            'name': grab(r"name:\s*'([^']+)'"),
            'shares': grab(r'shares:\s*([\d.]+)', float),
            'avgCost': grab(r'avgCost:\s*([\d.]+)', float),
            'currency': grab(r"currency:\s*'([^']+)'"),
            'exchange': grab(r"exchange:\s*'([^']+)'"),
            'alertAbove': grab(r'alertAbove:\s*([\d.]+)', float),
            'alertBelow': grab(r'alertBelow:\s*([\d.]+)', float),
        }
        if not s['ticker'] or s['shares'] is None or s['avgCost'] is None:
            continue
        labels = [lbl for p, lbl in group_labels if p < pos]
        s['group'] = labels[-1] if labels else ''
        stocks.append(s)
    print(f'Loaded {len(stocks)} holdings from portfolio.js')
    return stocks

def fetch_yahoo_price(symbol):
    url = f'https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d'
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
    r.raise_for_status()
    meta = r.json().get('chart', {}).get('result', [{}])[0].get('meta', {})
    price = meta.get('regularMarketPrice')
    if price is None:
        raise Exception('no price')
    prev = meta.get('chartPreviousClose') or meta.get('previousClose') or price
    return {'price': price, 'prev': prev, 'changePct': (price - prev) / prev * 100 if prev else 0}

def fetch_holding_price(s):
    if s['currency'] == 'USD':
        return fetch_yahoo_price(s['ticker'])
    if s.get('exchange') == 'TWO':
        return fetch_yahoo_price(f"{s['ticker']}.TWO")
    try:
        return fetch_yahoo_price(f"{s['ticker']}.TW")
    except Exception:
        return fetch_yahoo_price(f"{s['ticker']}.TWO")

def fetch_all_holdings():
    """Returns (stocks_with_prices, fx). Failed fetches get price=None."""
    stocks = load_portfolio()
    try:
        fx = fetch_yahoo_price('TWD=X')['price']
    except Exception:
        fx = 32.0
    for s in stocks:
        try:
            s['q'] = fetch_holding_price(s)
        except Exception as e:
            print(f"  price fail {s['ticker']}: {e}")
            s['q'] = None
        time.sleep(0.3)
    return stocks, fx

def check_alerts(stocks):
    """Return list of triggered alert strings."""
    hits = []
    for s in stocks:
        q = s.get('q')
        if not q:
            continue
        p = q['price']
        if s.get('alertAbove') is not None and p >= s['alertAbove']:
            hits.append(f"🔔 {s['name']}({s['ticker']}) {p:.2f} 已達目標價 {s['alertAbove']}（漲破提醒）")
        if s.get('alertBelow') is not None and p <= s['alertBelow']:
            hits.append(f"🔔 {s['name']}({s['ticker']}) {p:.2f} 已跌破 {s['alertBelow']}（跌破提醒）")
    return hits

def build_portfolio_section(stocks, fx):
    """Portfolio P&L summary lines for the push message."""
    priced = [s for s in stocks if s.get('q')]
    if not priced:
        return []
    def agg(subset):
        cost = sum(s['avgCost'] * s['shares'] for s in subset)
        val = sum(s['q']['price'] * s['shares'] for s in subset)
        day = sum((s['q']['price'] - s['q']['prev']) * s['shares'] for s in subset)
        return cost, val, day
    tw = [s for s in priced if s['currency'] == 'TWD']
    us = [s for s in priced if s['currency'] == 'USD']
    lines = ['💼 <b>持倉現況</b>']
    total_cost = total_val = 0.0
    for label, subset, mult in (('台股', tw, 1.0), ('美股', us, fx)):
        if not subset:
            continue
        cost, val, day = agg(subset)
        pnl_pct = (val - cost) / cost * 100 if cost else 0
        day_pct = day / (val - day) * 100 if (val - day) else 0
        lines.append(f'{label}：累計{pnl_pct:+.1f}% ｜ 今日{day_pct:+.1f}%')
        total_cost += cost * mult
        total_val += val * mult
    if total_cost:
        t_pnl = (total_val - total_cost) / total_cost * 100
        lines.append(f'合計市值 NT${total_val:,.0f}（{t_pnl:+.1f}%）')
    movers = sorted(priced, key=lambda s: s['q']['changePct'], reverse=True)
    if movers:
        top, bot = movers[0], movers[-1]
        lines.append(f"最強 {top['name']} {top['q']['changePct']:+.1f}% ｜ 最弱 {bot['name']} {bot['q']['changePct']:+.1f}%")
    return lines

def run_alert_check():
    """Afternoon mode: TW market closed — check price alerts only, push only if triggered."""
    print('Alert-only mode (afternoon TW close check)...')
    stocks, fx = fetch_all_holdings()
    hits = check_alerts(stocks)
    if not hits:
        print('No alerts triggered, staying silent')
        return
    msg = f'⚠️ <b>{TODAY} 到價提醒</b>\n' + '\n'.join(hits) + f'\n\n{APP_URL}'
    send_telegram(msg)

def build_telegram_message(summary, news_list, portfolio_lines=None, alert_lines=None):
    sentiment_map = {'bullish': '🟢 偏多', 'bearish': '🔴 偏空', 'neutral': '🟡 中性'}
    sentiment = sentiment_map.get(summary.get('overallSentiment', ''), '🟡 中性')
    impact_map = {'up': '▲', 'down': '▼', 'mixed': '◆'}

    lines = [f'📰 <b>{TODAY} 市場快報</b>',
             f'市場情緒：{sentiment}',
             f'研判：{summary.get("marketOutlook", "")}', '']

    winners = summary.get('topWinners', [])
    losers = summary.get('topLosers', [])
    if winners:
        w = '、'.join(f'{x.get("industry","")}({x.get("reason","")})' for x in winners)
        lines.append(f'📈 受惠：{w}')
    if losers:
        l = '、'.join(f'{x.get("industry","")}({x.get("reason","")})' for x in losers)
        lines.append(f'📉 承壓：{l}')
    for a in summary.get('keyActions', []):
        lines.append(f'💡 {a.get("type","")}｜{a.get("target","")}：{a.get("reason","")}')

    if portfolio_lines:
        lines.append('')
        lines.extend(portfolio_lines)
    if alert_lines:
        lines.append('')
        lines.extend(alert_lines)

    lines.append('')
    lines.append('🗞 <b>今日重點</b>')
    for n in news_list[:8]:
        mark = impact_map.get(n.get('impact', ''), '•')
        lines.append(f'{mark} {n.get("headline", "")}')

    lines.append('')
    lines.append(f'完整報告 → {APP_URL}')
    return '\n'.join(lines)

def run():
    print(f'Starting auto news analysis for {TODAY}...')

    # ── Step 1: Scan news ──
    scan_schema = '{"scanDate":"DATE","news":[{"id":1,"headline":"新聞標題（繁體中文）","category":"macro或micro或geo","impact":"up或down或mixed","summary":"一句話說明（繁體中文，20字內）","relevance":"high或medium"}]}'
    scan_prompt = (
        f'今天是{TODAY}。請使用 Google Search 搜尋今日影響台股和美股的重大事件，'
        '範圍：總經政策（Fed、通膨、GDP）、地緣政治（戰爭、貿易、制裁）、產業事件（半導體、AI、企業財報）。'
        '只列出真實存在的新聞，不要捏造。找出8到10則最重要的事件。'
        '所有headline和summary必須用繁體中文。'
        f'只輸出純JSON一行不要markdown，格式：{scan_schema.replace("DATE", TODAY)}。'
        'category值：macro=總經政策、micro=產業個股、geo=地緣政治。'
    )

    print('Scanning news...')
    scan_raw = call_gemini(scan_prompt, use_search=True)
    scan_data = parse_json(scan_raw)
    news_list = scan_data.get('news', [])
    print(f'Found {len(news_list)} news items')

    if not news_list:
        print('No news found, exiting')
        return

    # ── Step 2: Summary analysis ──
    headlines = '；'.join([f'第{i+1}則：{n["headline"]}' for i, n in enumerate(news_list)])
    summary_schema = '{"reportDate":"DATE","overallSentiment":"bullish或bearish或neutral","marketOutlook":"整體研判（30字內）","topWinners":[{"industry":"產業","stocks":["個股"],"reason":"原因（8字內）","sourcedFrom":"來自第幾則"}],"topLosers":[{"industry":"產業","stocks":["個股"],"reason":"原因（8字內）","sourcedFrom":"來自第幾則"}],"keyActions":[{"type":"持有或觀望或減碼","target":"對象","reason":"建議（15字內）","sourcedFrom":"來自第幾則"}]}'
    summary_prompt = (
        f'以下是{len(news_list)}則重要新聞：{headlines}。'
        '請只根據這些新聞的實際內容，推導出哪些產業受益、哪些受害，'
        '每個結論必須在sourcedFrom標明來自第幾則新聞作為依據。'
        '若找不到支持某產業受益或受害的新聞，就不要列出該產業。'
        f'只輸出純JSON一行不要markdown，格式：{summary_schema.replace("DATE", TODAY)}。'
        '嚴格限制：topWinners最多2個、topLosers最多2個、keyActions最多2條、stocks各1支。'
    )

    print('Generating summary...')
    summary_raw = call_gemini(summary_prompt, use_search=False)
    summary = parse_json(summary_raw)

    # ── Step 3: Write to Sheets（失敗不擋推播） ──
    winners = '、'.join([w.get('industry', '') for w in summary.get('topWinners', [])])
    losers = '、'.join([l.get('industry', '') for l in summary.get('topLosers', [])])

    full_report = {
        'reportDate': TODAY,
        'newsCount': len(news_list),
        'summary': summary,
        'events': [],
        'rawNews': news_list,
        'autoGenerated': True
    }

    row = [
        TODAY,
        NOW.strftime('%H:%M:%S'),
        len(news_list),
        summary.get('overallSentiment', ''),
        summary.get('marketOutlook', ''),
        winners,
        losers,
        json.dumps(full_report, ensure_ascii=False)[:4000]
    ]

    try:
        service = get_sheets_service()
        append_to_sheet(service, NEWS_SHEET, row)
    except Exception as e:
        print(f'✗ Sheets write failed (continuing to push): {e}')

    # ── Step 4: 持倉損益 + 到價提醒 ──
    portfolio_lines, alert_lines = [], []
    try:
        stocks, fx = fetch_all_holdings()
        portfolio_lines = build_portfolio_section(stocks, fx)
        alert_lines = check_alerts(stocks)
    except Exception as e:
        print(f'Portfolio section failed (continuing): {e}')

    # ── Step 5: Telegram 推播 ──
    send_telegram(build_telegram_message(summary, news_list, portfolio_lines, alert_lines))

    print(f'✓ Auto news report completed for {TODAY}')

if __name__ == '__main__':
    # 早上（台灣 12 點前）跑完整新聞報告；下午排程只做到價檢查
    if NOW.hour < 12:
        run()
    else:
        run_alert_check()
