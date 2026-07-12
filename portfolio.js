/**
 * portfolio.js — 持倉資料檔
 * 
 * 修改持股時只需要改這個檔案，不用動 index.html
 * 欄位說明：
 *   ticker   : 股票代號（台股用數字，美股用英文）
 *   name     : 股票名稱
 *   shares   : 持股數量
 *   avgCost  : 成交均價
 *   currency : 'TWD' 或  'USD'
 *   exchange : 'TWO' = 上櫃（選填，如 00955）
 *   alertAbove : 到價提醒—漲到此價通知（選填，例：獲利了結目標價）
 *   alertBelow : 到價提醒—跌到此價通知（選填，例：停損或加碼價）
 *
 * 到價提醒範例（把數字改成你要的價位即可）：
 *   { ticker: '2618', name: '長榮航', shares: 5000, avgCost: 35.55, currency: 'TWD', alertAbove: 41 },
 * 觸價時會在 App 持倉頁標紅，且每日排程檢查到會發 Telegram 通知
 *
 * lastUpdated 請每次修改後順手更新日期
 */

window.PORTFOLIO = {

  lastUpdated: '2026/06/08',

  groups: [

    // ──────────────────────────────
    // 🤖 AI & 半導體
    // ──────────────────────────────
    {
      id: 'ai_semi',
      label: 'AI & 半導體',
      icon: '🤖',
      market: 'US',
      newsKeywords: 'NVIDIA AVGO Broadcom Google Alphabet Amazon AI chip semiconductor data center 2025',
      stocks: [
        { ticker: 'NVDA', name: '輝達',        shares: 60,  avgCost: 111.797333, currency: 'USD' },
        { ticker: 'AVGO', name: 'Broadcom',    shares: 3,   avgCost: 164.323333, currency: 'USD' },
        { ticker: 'GOOG', name: 'Alphabet',    shares: 15,  avgCost: 184.017333, currency: 'USD' },
        { ticker: 'AMZN', name: '亞馬遜',      shares: 10,  avgCost: 214.442000, currency: 'USD' },
      ]
    },

    // ──────────────────────────────
    // 🇹🇼 台積電
    // ──────────────────────────────
    {
      id: 'tsmc',
      label: '台積電',
      icon: '🇹🇼',
      market: 'TW',
      newsKeywords: '台積電 TSMC 先進製程 CoWoS 晶圓代工 輝達訂單 2025',
      stocks: [
        { ticker: '2330', name: '台積電', shares: 318, avgCost: 1468, currency: 'TWD' },
      ]
    },

    // ──────────────────────────────
    // ⚛️ 核能
    // ──────────────────────────────
    {
      id: 'nuclear',
      label: '核能',
      icon: '⚛️',
      market: 'US',
      newsKeywords: 'OKLO SMR NuScale small modular reactor nuclear power NRC approval contract 2025',
      stocks: [
        { ticker: 'OKLO', name: 'Oklo Inc.',     shares: 20, avgCost: 65.040500,  currency: 'USD' },
        { ticker: 'SMR',  name: 'NuScale Power', shares: 30, avgCost: 11.572667,  currency: 'USD' },
      ]
    },

    // ──────────────────────────────
    // 🏦 金融
    // ──────────────────────────────
    {
      id: 'finance',
      label: '金融',
      icon: '🏦',
      market: 'TW',
      newsKeywords: '台灣金融股 升降息 銀行股 台新金 兆豐金 合庫金 利差 金控獲利 2025',
      stocks: [
        { ticker: '2887', name: '台新新光金', shares: 10440, avgCost: 16.01, currency: 'TWD' },
        { ticker: '2886', name: '兆豐金',     shares: 1030,  avgCost: 34.62, currency: 'TWD' },
        { ticker: '5880', name: '合庫金',     shares: 1120,  avgCost: 21.06, currency: 'TWD' },
      ]
    },

    // ──────────────────────────────
    // ✈️ 航運
    // ──────────────────────────────
    {
      id: 'aviation',
      label: '航運',
      icon: '✈️',
      market: 'TW',
      newsKeywords: '長榮航空 2618 航空貨運 旅客量 油價 航空股 2025',
      stocks: [
        { ticker: '2618', name: '長榮航', shares: 5000, avgCost: 35.55, currency: 'TWD' },
      ]
    },

    // ──────────────────────────────
    // 👟 鞋類代工
    // ──────────────────────────────
    {
      id: 'footwear',
      label: '鞋類代工',
      icon: '👟',
      market: 'TW',
      newsKeywords: '寶成 9904 製鞋 Nike Adidas 代工訂單 越南 東南亞製造 2025',
      stocks: [
        { ticker: '9904', name: '寶成', shares: 5000, avgCost: 25.64, currency: 'TWD' },
      ]
    },

    // ──────────────────────────────
    // 🛡️ 國防科技
    // ──────────────────────────────
    {
      id: 'defense',
      label: '國防科技',
      icon: '🛡️',
      market: 'TW',
      newsKeywords: '台灣國防預算 無人機 漢翔 雷虎 軍備採購 勇鷹教練機 F-16升級 國防自主 2025',
      stocks: [
        { ticker: '2634', name: '漢翔', shares: 2000, avgCost: 46.77,  currency: 'TWD' },
        { ticker: '8033', name: '雷虎', shares: 1000, avgCost: 132.19, currency: 'TWD' },
      ]
    },

    // ──────────────────────────────
    // 🇯🇵 日本商社
    // ──────────────────────────────
    {
      id: 'japan',
      label: '日本商社',
      icon: '🇯🇵',
      market: 'TW',
      newsKeywords: '日本商社 巴菲特 伊藤忠 三菱商事 日圓匯率 00955 中信日本商社 ETF 2025',
      stocks: [
        { ticker: '00955', name: '中信日本商社', shares: 10000, avgCost: 15.6, currency: 'TWD', exchange: 'TWO' },
      ]
    },

  ] // end groups

}; // end PORTFOLIO
    // ──────────────────────────────
    // 🇹🇼 台積電
    // ──────────────────────────────
    {
      id: 'tsmc',
      label: '台積電',
      icon: '🇹🇼',
      market: 'TW',
      newsKeywords: '台積電 TSMC 先進製程 CoWoS 晶圓代工 輝達訂單 2025',
      stocks: [
        { ticker: '2330', name: '台積電', shares: 318, avgCost: 1468, currency: 'TWD' },
      ]
    },

    // ──────────────────────────────
    // ⚛️ 核能
    // ──────────────────────────────
    {
      id: 'nuclear',
      label: '核能',
      icon: '⚛️',
      market: 'US',
      newsKeywords: 'OKLO SMR NuScale small modular reactor nuclear power NRC approval contract 2025',
      stocks: [
        { ticker: 'OKLO', name: 'Oklo Inc.',     shares: 20, avgCost: 65.040500,  currency: 'USD' },
        { ticker: 'SMR',  name: 'NuScale Power', shares: 30, avgCost: 11.572667,  currency: 'USD' },
      ]
    },

    // ──────────────────────────────
    // 🏦 金融
    // ──────────────────────────────
    {
      id: 'finance',
      label: '金融',
      icon: '🏦',
      market: 'TW',
      newsKeywords: '台灣金融股 升降息 銀行股 台新金 兆豐金 合庫金 利差 金控獲利 2025',
      stocks: [
        { ticker: '2887', name: '台新新光金', shares: 10440, avgCost: 16.01, currency: 'TWD' },
        { ticker: '2886', name: '兆豐金',     shares: 1030,  avgCost: 34.62, currency: 'TWD' },
        { ticker: '5880', name: '合庫金',     shares: 1120,  avgCost: 21.06, currency: 'TWD' },
      ]
    },

    // ──────────────────────────────
    // ✈️ 航運
    // ──────────────────────────────
    {
      id: 'aviation',
      label: '航運',
      icon: '✈️',
      market: 'TW',
      newsKeywords: '長榮航空 2618 航空貨運 旅客量 油價 航空股 2025',
      stocks: [
        { ticker: '2618', name: '長榮航', shares: 5000, avgCost: 35.55, currency: 'TWD' },
      ]
    },

    // ──────────────────────────────
    // 👟 鞋類代工
    // ──────────────────────────────
    {
      id: 'footwear',
      label: '鞋類代工',
      icon: '👟',
      market: 'TW',
      newsKeywords: '寶成 9904 製鞋 Nike Adidas 代工訂單 越南 東南亞製造 2025',
      stocks: [
        { ticker: '9904', name: '寶成', shares: 5000, avgCost: 25.64, currency: 'TWD' },
      ]
    },

    // ──────────────────────────────
    // 🛡️ 國防科技
    // ──────────────────────────────
    {
      id: 'defense',
      label: '國防科技',
      icon: '🛡️',
      market: 'TW',
      newsKeywords: '台灣國防預算 無人機 漢翔 雷虎 軍備採購 勇鷹教練機 F-16升級 國防自主 2025',
      stocks: [
        { ticker: '2634', name: '漢翔', shares: 2000, avgCost: 46.77,  currency: 'TWD' },
        { ticker: '8033', name: '雷虎', shares: 1000, avgCost: 132.19, currency: 'TWD' },
      ]
    },

    // ──────────────────────────────
    // 🇯🇵 日本商社
    // ──────────────────────────────
    {
      id: 'japan',
      label: '日本商社',
      icon: '🇯🇵',
      market: 'TW',
      newsKeywords: '日本商社 巴菲特 伊藤忠 三菱商事 日圓匯率 00955 中信日本商社 ETF 2025',
      stocks: [
        { ticker: '00955', name: '中信日本商社', shares: 10000, avgCost: 15.6, currency: 'TWD', exchange: 'TWO' },
      ]
    },

  ] // end groups

}; // end PORTFOLIO
