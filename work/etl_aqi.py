# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas"]
# ///
"""
台灣空氣品質 AQI ETL

讀 raw/stat_p_115_offset*.csv（環境部「空氣品質指標(AQI)概況」，兩頁），輸出：
  data/aqi_monthly.csv          月資料
  data/aqi_yearly_official.csv  官方年度彙總列（只拿來驗證）
  data/county_region.csv        縣市 → 區域對照

用法：uv run work/etl_aqi.py
"""
import re
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
OUT = ROOT / "data"

# ---------- 規則 ----------

COLUMN_MAP = {
    "item1": "period",
    "item2": "county",
    "value1": "total_days",
    "value2": "good",
    "value3": "moderate",
    "value4": "unhealthy_sensitive",
    "value5": "unhealthy_all",
    "value6": "very_unhealthy",
    "value7": "hazardous",
    "value8": "pct_over100",
}
OUT_COLS = ["date", "year", "month", "county", "region", "total_days", "good", "moderate",
            "unhealthy_sensitive", "unhealthy_all", "very_unhealthy", "hazardous", "pct_over100"]
YEARLY_COLS = ["year", "county", "region", "total_days", "good", "moderate",
               "unhealthy_sensitive", "unhealthy_all", "very_unhealthy", "hazardous", "pct_over100"]

NATIONAL_SRC, NATIONAL = "總計", "全國"
REGION = {
    "北部": ["臺北市", "新北市", "基隆市", "桃園市", "新竹市", "新竹縣"],
    "中部": ["苗栗縣", "臺中市", "彰化縣", "南投縣", "雲林縣"],
    "南部": ["嘉義市", "嘉義縣", "臺南市", "高雄市", "屏東縣"],
    "東部": ["宜蘭縣", "花蓮縣", "臺東縣"],
    "離島": ["澎湖縣", "金門縣", "連江縣"],
}
COUNTY_REGION = {c: r for r, cs in REGION.items() for c in cs}
COUNTY_REGION[NATIONAL] = NATIONAL      # 全國不屬於任何區域

PERIOD_RE = re.compile(r"^(\d+)年(?:(\d+)月)?$")


def parse_period(s):
    """'113年 9月' → (2024, 9)；'113年' → (2024, None)。民國年 + 1911 = 西元年。"""
    m = PERIOD_RE.match(re.sub(r"[\s\"']", "", s))
    if not m:
        raise ValueError(f"無法解析統計期: {s!r}")
    return int(m.group(1)) + 1911, (int(m.group(2)) if m.group(2) else None)


def main():
    files = sorted(RAW.glob("stat_p_115_offset*.csv"), key=lambda p: int(re.search(r"offset(\d+)", p.name).group(1)))
    frames = [pd.read_csv(f, encoding="utf-8", dtype=str) for f in files]
    df = pd.concat(frames, ignore_index=True)
    print(f"讀入 {len(files)} 檔，共 {len(df)} 列")

    df = df.rename(columns=COLUMN_MAP)
    df["period"] = df["period"].str.strip()
    df["county"] = df["county"].str.strip().str.replace("台", "臺", regex=False)
    df["county"] = df["county"].replace({NATIONAL_SRC: NATIONAL})

    n0 = len(df)
    df = df.drop_duplicates()
    print(f"去除完全重複列: {n0 - len(df)} 列")
    key_dups = df.duplicated(["period", "county"], keep=False)
    if key_dups.any():
        print("警告：同一 (統計期, 統計區) 出現數值不同的列：")
        print(df[key_dups].sort_values(["period", "county"]).to_string())

    ym = df["period"].map(parse_period)
    df["year"] = [y for y, _ in ym]
    df["month"] = [m for _, m in ym]

    num = ["total_days", "good", "moderate", "unhealthy_sensitive", "unhealthy_all",
           "very_unhealthy", "hazardous"]
    df[num] = df[num].astype(int)
    df["pct_over100"] = df["pct_over100"].astype(float)

    unknown = set(df["county"]) - set(COUNTY_REGION)
    if unknown:
        raise SystemExit(f"未對照的統計區: {unknown}")
    df["region"] = df["county"].map(COUNTY_REGION)

    monthly = df[df["month"].notna()].copy()
    monthly["month"] = monthly["month"].astype(int)
    monthly["date"] = monthly["year"].astype(str) + "-" + monthly["month"].astype(str).str.zfill(2)
    monthly = monthly[OUT_COLS].sort_values(["date", "county"]).reset_index(drop=True)

    yearly = df[df["month"].isna()][YEARLY_COLS].sort_values(["year", "county"]).reset_index(drop=True)

    OUT.mkdir(exist_ok=True)
    monthly.to_csv(OUT / "aqi_monthly.csv", index=False, encoding="utf-8")
    yearly.to_csv(OUT / "aqi_yearly_official.csv", index=False, encoding="utf-8")
    pd.DataFrame(
        [(c, r) for c, r in COUNTY_REGION.items()], columns=["county", "region"]
    ).to_csv(OUT / "county_region.csv", index=False, encoding="utf-8")

    print(f"月資料 {len(monthly)} 列（{monthly['date'].min()} ~ {monthly['date'].max()}）→ data/aqi_monthly.csv")
    print(f"年度彙總 {len(yearly)} 列 → data/aqi_yearly_official.csv")


if __name__ == "__main__":
    main()
