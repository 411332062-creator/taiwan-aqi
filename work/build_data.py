# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas"]
# ///
"""
把 data/aqi_monthly.csv 整理成網頁可直接載入的 docs/data.js。

只讀 aqi_monthly.csv 和 county_region.csv。
輸出格式（window.AQI_DATA）：
  meta   資料來源、期間、各等級名稱與 AQI 範圍、縣市與區域、計算公式、限制說明
  dims   各維度的值（dates, counties, regions, levels）
  cols   欄式資料，每個陣列長度相同，第 i 筆是 (d[i], c[i]) 加上各等級站日數：
           d / c 是 dims.dates / dims.counties 的索引
           t 總站日數；g 良好；m 普通；s 對敏感族群不健康；a 對所有族群不健康；
           v 非常不健康；h 危害
         （官方 pct_over100 不帶過去，網頁一律用站日數加權重算）

用法：uv run work/build_data.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data.js"

# ---------- 顯示順序與說明文字（呈現用，不影響數字） ----------

NATIONAL = "全國"
COUNTY_ORDER = [
    "臺北市", "新北市", "基隆市", "桃園市", "新竹市", "新竹縣", "苗栗縣", "臺中市",
    "彰化縣", "南投縣", "雲林縣", "嘉義市", "嘉義縣", "臺南市", "高雄市", "屏東縣",
    "宜蘭縣", "花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣",
]
REGION_ORDER = ["北部", "中部", "南部", "東部", "離島"]

# (欄位, 資料欄鍵, 名稱, AQI 範圍)；AQI 範圍是環境部對 AQI 指標值的分級
LEVELS = [
    ("good", "g", "良好", "0–50"),
    ("moderate", "m", "普通", "51–100"),
    ("unhealthy_sensitive", "s", "對敏感族群不健康", "101–150"),
    ("unhealthy_all", "a", "對所有族群不健康", "151–200"),
    ("very_unhealthy", "v", "非常不健康", "201–300"),
    ("hazardous", "h", "危害", "301–500"),
]
OVER100 = ["unhealthy_sensitive", "unhealthy_all", "very_unhealthy", "hazardous"]

META = {
    "title": "台灣空氣品質 AQI 月統計",
    "source": {
        "name": "環境部「空氣品質指標(AQI)概況」（全國及縣市別、每月、各 AQI 等級站日數）",
        "agency": "環境部",
        "datasetUrl": "https://data.gov.tw/dataset/89029",
        "downloadedOn": "2026-10-12",
        "license": "政府資料開放授權條款－第1版",
    },
    "period": {"from": "2021-06", "to": "2026-06"},
    "formula": {
        "pctOver100": "AQI>100 比率 = Σ(對敏感族群不健康＋對所有族群不健康＋非常不健康＋危害 的站日數) ÷ Σ總站日數 × 100",
        "levelShare": "各等級占比 = Σ該等級站日數 ÷ Σ總站日數 × 100",
    },
    "notes": [
        "站日數 = 測站數 × 天數。比率一律用站日數加權（Σ超標站日 ÷ Σ總站日），不平均各月百分比。",
        "站日數會隨測站數變動，縣市間只能比比率，不能比站日數。",
        "2021 年只有 6～12 月、2026 年只有 1～6 月，年度比較只用 2022～2025 完整年。",
        "2025 年新北市與全國的官方年度列和月加總差 120 站日，本頁以月資料為準。",
        "「全國」是官方原檔的「總計」列，等於各縣市站日數加總（已逐月驗證）。",
        "區域分法為本專案自訂：北部、中部、南部、東部、離島（非官方分區）。",
        "年份為西元年，由原始資料的民國年加 1911 轉換。",
    ],
}


def main():
    df = pd.read_csv(ROOT / "data" / "aqi_monthly.csv", encoding="utf-8-sig", dtype={"date": str})
    reg = pd.read_csv(ROOT / "data" / "county_region.csv", encoding="utf-8-sig")
    region_of = dict(zip(reg.county, reg.region))

    counties = [NATIONAL] + COUNTY_ORDER
    if set(df.county) != set(counties):
        sys.exit(f"縣市和 COUNTY_ORDER 不一致：{set(df.county) ^ set(counties)}")
    if set(region_of) != set(counties) or set(region_of.values()) - {NATIONAL} != set(REGION_ORDER):
        sys.exit("county_region.csv 和縣市 / 區域清單不一致")

    dates = sorted(df.date.unique().tolist())
    df = df.sort_values(["date", "county"]).reset_index(drop=True)
    cidx = {c: i for i, c in enumerate(counties)}
    didx = {d: i for i, d in enumerate(dates)}

    cols = {"d": df.date.map(didx).tolist(), "c": df.county.map(cidx).tolist(),
            "t": df.total_days.astype(int).tolist()}
    for field, key, _, _ in LEVELS:
        cols[key] = df[field].astype(int).tolist()

    dims = {
        "dates": dates,
        "counties": counties,
        "regions": REGION_ORDER,
        "countyRegion": [region_of[c] for c in counties],
        "levels": [{"key": k, "name": n, "aqiRange": r} for _, k, n, r in LEVELS],
    }
    payload = {"meta": {**META, "rows": len(df)}, "dims": dims, "cols": cols}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("window.AQI_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
                   encoding="utf-8")
    size = OUT.stat().st_size
    print(f"輸出 {OUT.relative_to(ROOT)}：{len(df):,} 筆，{size:,} bytes（{size / 1024:.1f} KB）")

    verify(df)


def verify(csv_df: pd.DataFrame):
    """重新讀回 data.js，還原成表格，和 aqi_monthly.csv 逐格比對。"""
    text = OUT.read_text(encoding="utf-8")
    prefix, suffix = "window.AQI_DATA = ", ";\n"
    if not (text.startswith(prefix) and text.endswith(suffix)):
        sys.exit("data.js 格式不是預期的 window.AQI_DATA = {...};")
    data = json.loads(text[len(prefix):-len(suffix)])
    d, c = data["dims"], data["cols"]
    same_len = len({len(v) for v in c.values()}) == 1

    back = pd.DataFrame({
        "date": [d["dates"][i] for i in c["d"]],
        "county": [d["counties"][i] for i in c["c"]],
        "region": [d["countyRegion"][i] for i in c["c"]],
        "total_days": c["t"],
        **{field: c[key] for field, key, _, _ in LEVELS},
    })
    cols = list(back.columns)
    a = csv_df[cols].sort_values(["date", "county"]).reset_index(drop=True)
    b = back.sort_values(["date", "county"]).reset_index(drop=True)
    cells_equal = a.equals(b)

    # 官方 pct_over100 沒帶過去；用還原的站日數重算，和 CSV 官方值比對
    calc = back[OVER100].sum(axis=1) / back.total_days * 100
    ref = csv_df.set_index(["date", "county"]).pct_over100
    got = pd.Series(calc.values, index=pd.MultiIndex.from_frame(back[["date", "county"]]))
    max_diff = (got - ref.reindex(got.index)).abs().max()

    # 全國 = 各縣市加總
    nat = back[back.county == NATIONAL].set_index("date")
    cty = back[back.county != NATIONAL].groupby("date")[["total_days"] + [f for f, *_ in LEVELS]].sum()
    nat_ok = (cty == nat[cty.columns]).all().all()

    print("\n核對：")
    checks = [
        ("cols 各陣列長度一致", same_len),
        (f"筆數 data.js {len(back)} = CSV {len(csv_df)}", len(back) == len(csv_df)),
        (f"{len(a)} 列 × {len(cols)} 欄逐格與 aqi_monthly.csv 一致（含 region）", cells_equal),
        (f"由站日數重算的 AQI>100 比率與官方 pct_over100 最大差 {max_diff:.4f}（應 ≤ 0.01）", max_diff <= 0.01),
        ("全國 = 各縣市加總（逐月）", nat_ok),
        (f"月份 {d['dates'][0]} ~ {d['dates'][-1]}，共 {len(d['dates'])} 個", len(d["dates"]) == 61),
    ]
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if not all(ok for _, ok in checks):
        sys.exit("核對未通過")


if __name__ == "__main__":
    main()
