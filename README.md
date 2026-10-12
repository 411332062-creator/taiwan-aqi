# 台灣空氣品質 AQI 2021–2026

用環境部公開的「空氣品質指標(AQI)概況」，做一個可以篩選期間、區域、縣市的互動式 BI 網頁，看台灣各縣市空氣品質在哪裡、何時變差。

- 網站：https://411332062-creator.github.io/taiwan-aqi/
- 原始碼與資料：https://github.com/411332062-creator/taiwan-aqi

## 資料來源

| 項目 | 內容 |
|---|---|
| 資料集 | 空氣品質指標(AQI)概況（全國及縣市別、每月、各 AQI 等級站日數） |
| 提供機關 | 環境部 |
| 資料集頁面 | https://data.gov.tw/dataset/89029 |
| 下載日期 | 2026-10-12 |
| 授權 | 政府資料開放授權條款－第1版 |
| 涵蓋期間 | 2021-06 ～ 2026-06（61 個月）、22 個縣市加「全國」 |

原檔分兩頁下載（`limit=1000`，`offset` 0 與 1000），網址、檔案大小與 SHA-256 記在 [`raw/SOURCES.md`](raw/SOURCES.md)。網址中的 `api_key` 已用 `***` 遮蔽，那是 data.gov.tw 資料集頁面公開附的下載 key。

## 資料夾結構

```text
prompts/    課程提示詞
raw/        環境部原檔（兩頁 CSV，未修改）與 SOURCES.md
work/       etl_aqi.py（整理資料）、build_data.py（產生網頁資料）
data/       整理後的 CSV：aqi_monthly.csv、aqi_yearly_official.csv、county_region.csv
scripts/    validate_aqi.py（驗證）
docs/       網頁：index.html、data.js（GitHub Pages 的發佈資料夾）
```

## 流程

```text
raw/*.csv ──work/etl_aqi.py──▶ data/*.csv ──work/build_data.py──▶ docs/data.js ──▶ docs/index.html
                                   │
                          scripts/validate_aqi.py（驗證 data/）
```

- `etl_aqi.py`：合併兩頁並去重；把月資料與官方年度彙總列分開；民國年轉西元、拆出 year / month / date；「總計」改名「全國」、縣市統一用「臺」；加上 region 欄位。
- `build_data.py`：只讀 `data/aqi_monthly.csv` 與 `data/county_region.csv`，輸出 `docs/data.js`，並把 `data.js` 還原後與 CSV 逐格比對。
- `index.html`：讀取 `data.js`，用 ECharts 畫圖。

## 重跑與驗證

需要 [uv](https://docs.astral.sh/uv/)；腳本開頭已宣告相依套件（pandas），不用另外安裝。

```bash
uv run work/etl_aqi.py          # raw → data
uv run scripts/validate_aqi.py  # 驗證 data（失敗時結束碼不為 0）
uv run work/build_data.py       # data → docs/data.js，並核對
```

網頁直接雙擊 `docs/index.html` 就能開（需要網路載入 ECharts 5.5.0）。

## 欄位

`data/aqi_monthly.csv`：`date, year, month, county, region, total_days, good, moderate, unhealthy_sensitive, unhealthy_all, very_unhealthy, hazardous, pct_over100`

- `total_days` 是站日數（測站數 × 天數）。
- `region` 是本專案自訂的分區：北部、中部、南部、東部、離島；「全國」列的 region 也是「全國」。
- `pct_over100` 是官方給的 AQI>100 日數比率(%)；網頁不使用它，一律用站日數重算。

## 計算公式

- AQI>100 比率 = Σ(對敏感族群不健康 ＋ 對所有族群不健康 ＋ 非常不健康 ＋ 危害 的站日數) ÷ Σ總站日數 × 100
- 各等級占比 = Σ該等級站日數 ÷ Σ總站日數 × 100
- 一律用站日數加權，不平均各月百分比。

## AQI 等級對照

依環境部空氣品質指標分級。

| 等級 | AQI 範圍 | 代表色 |
|---|---|---|
| 良好 | 0–50 | 綠 |
| 普通 | 51–100 | 黃 |
| 對敏感族群不健康 | 101–150 | 橘 |
| 對所有族群不健康 | 151–200 | 紅 |
| 非常不健康 | 201–300 | 紫 |
| 危害 | 301–500 | 褐紅 |

## 驗證項目

`scripts/validate_aqi.py` 與 ETL 不共用邏輯，檢查：

- 輸出列數等於原檔列數（月資料 1403 列 ＋ 年度列 115 列 ＝ 1518 列）。
- 每列各等級加總等於 `total_days`；`pct_over100` 重算後與官方值一致（容許四捨五入誤差）。
- `(date, county)` 不重複、沒有負數與缺值。
- 各縣市月資料加總等於「全國」（逐月）。
- 完整 12 個月的 (年, 縣市)，月資料加總等於官方年度彙總列（已知例外見下）。
- 列出各縣市缺少的月份，不補值：目前 2021-06 到 2026-06 沒有缺月。

## 已知的來源不一致

2025 年（民國 114 年）**新北市**與**全國**的官方年度彙總列，和月資料加總差 120 站日：

| 統計區 | 月資料加總 | 官方年度列 |
|---|---|---|
| 新北市 | 3040 | 2920 |
| 全國 | 22383 | 22263 |

新北市 2025 年 1～4 月每月以 9 站計，5 月起變 8 站；官方年度列疑似整年以 8 站計（1～4 月共 120 天 × 1 站 ＝ 120 站日）。這是由數字推測的原因，未經環境部確認。

處理方式：不修改任何數字，網頁以月資料為準；驗證腳本把這 2 組列為已知例外並印出警告，其餘組合維持嚴格檢查。

## 限制說明

- 站日數會隨測站數變動，縣市間只能比比率，不能比站日數。
- 2021 年只有 6～12 月、2026 年只有 1～6 月，年度比較只用 2022～2025 完整年；官方年度列 2021 年是整年，因此和月資料加總不同是預期的。
- 區域分法為本專案自訂，非官方分區。
- 這是各縣市月統計，不含各測站每日數值；未下載環境部「日空氣品質指標(AQI)」資料。
- 資料為下載日（2026-10-12）當時的版本，環境部之後可能更新或修正。
