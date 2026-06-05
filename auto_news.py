import os
import json
import time
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

# Taiwan time (UTC+8)
TW_TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TW_TZ)
TODAY = NOW.strftime('%Y/%m/%d')

def call_gemini(prompt, use_search=True):
    """Call Gemini API with optional Google Search grounding."""
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_API_KEY}'
    body = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': 0.3, 'maxOutputTokens': 8192}
    }
    if use_search:
        body['tools'] = [{'google_search': {}}]

    for attempt in range(3):
        resp = requests.post(url, json=body, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            return text
        elif resp.status_code in (429, 503):
            wait = (attempt + 1) * 5
            print(f'Rate limited, waiting {wait}s...')
            time.sleep(wait)
        else:
            raise Exception(f'Gemini error {resp.status_code}: {resp.text[:200]}')
    raise Exception('Gemini failed after 3 attempts')

def parse_json(raw):
    """Extract JSON from response text."""
    import re
    raw = raw.replace('```json', '').replace('```', '').strip()
    # Try array first
    arr_match = re.search(r'\[[\s\S]*\]', raw)
    obj_match = re.search(r'\{[\s\S]*\}', raw)
    if obj_match:
        return json.loads(obj_match.group())
    elif arr_match:
        return json.loads(arr_match.group())
    raise Exception('No JSON found in response')

def get_sheets_service():
    """Build Google Sheets service with service account."""
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
    """Append a row to Google Sheets."""
    body = {'values': [row]}
    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f'{sheet_name}!A1',
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()
    print(f'✓ Appended to {sheet_name}')

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

    # ── Step 3: Write to Sheets ──
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

    service = get_sheets_service()
    append_to_sheet(service, NEWS_SHEET, row)
    print(f'✓ Auto news report completed for {TODAY}')

if __name__ == '__main__':
    run()
