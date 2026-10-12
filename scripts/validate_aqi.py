# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas"]
# ///
"""
驗證 data/aqi_monthly.csv 與 data/aqi_yearly_official.csv。
獨立於 work/etl_aqi.py（不 import、不共用邏輯），只讀輸出 CSV 與 raw 原檔。

用法：uv run scripts/validate_aqi.py
"""
import glob
import re
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
CATS = ["good", "moderate", "unhealthy_sensitive", "unhealthy_all", "very_unhealthy", "hazardous"]
BAD = ["unhealthy_sensitive", "unhealthy_all", "very_unhealthy", "hazardous"]
NUM = ["total_days"] + CATS
# 已知來源不一致：官方年度列與月資料加總不符，已確認不是 ETL 造成，數字不修改。
# 新北市 2025 年 1~4 月每月以 9 站計，5 月起變 8 站；官方年度列疑似整年以 8 站計
# （1~4 月共 120 天 × 1 站 = 120 站日，3040 - 2920 = 120）。
KNOWN_MISMATCH = {
    (2025, "新北市"): "新北市 5 月起測站由 9 站變 8 站，官方年度列疑似整年以 8 站計",
    (2025, "全國"): "同上：全國含新北市，差額來自新北市的 120 站日",
}
PCT_TOL = 0.01          # pct_over100 官方只給兩位小數，四捨五入誤差上限 0.005，留一點餘裕

m = pd.read_csv(ROOT / "data" / "aqi_monthly.csv", dtype={"date": str})
y = pd.read_csv(ROOT / "data" / "aqi_yearly_official.csv")
fails = []


def check(name, bad_df, note=""):
    ok = len(bad_df) == 0
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({note})" if note else ""))
    if not ok:
        fails.append(name)
        print(bad_df.head(15).to_string())


# 0. 和原檔列數對得起來（原檔每個資料列恰好一列：月資料 + 年度列）
raw_rows = sum(len(open(f, encoding="utf-8").read().splitlines()) - 1
               for f in glob.glob(str(ROOT / "raw" / "stat_p_115_offset*.csv")))
print(f"原檔資料列 {raw_rows}；輸出 月資料 {len(m)} + 年度 {len(y)} = {len(m) + len(y)}")
check("輸出列數 = 原檔列數", pd.DataFrame() if raw_rows == len(m) + len(y) else pd.DataFrame([{"raw": raw_rows}]))

# 1. 各等級加總 = total_days
check("月資料：good~hazardous 加總 = total_days", m[m[CATS].sum(axis=1) != m["total_days"]])
check("年度列：good~hazardous 加總 = total_days", y[y[CATS].sum(axis=1) != y["total_days"]])

# 2. pct_over100 重算
for name, d in (("月資料", m), ("年度列", y)):
    calc = d[BAD].sum(axis=1) / d["total_days"] * 100
    bad = d[(calc - d["pct_over100"]).abs() > PCT_TOL]
    check(f"{name}：pct_over100 = 不健康以上/total_days×100（容許 ±{PCT_TOL}）",
          bad.assign(recalc=calc[bad.index].round(3)) if len(bad) else bad)

# 3. 無重複、無負數、無缺值
check("月資料：(date, county) 不重複", m[m.duplicated(["date", "county"], keep=False)])
check("年度列：(year, county) 不重複", y[y.duplicated(["year", "county"], keep=False)])
check("月資料：數值欄無負數", m[(m[NUM + ["pct_over100"]] < 0).any(axis=1)])
check("月資料：無缺值", m[m.isna().any(axis=1)])
check("月資料：month 在 1~12", m[~m["month"].between(1, 12)])

# 4. 各縣市月資料加總 = 全國
cty = m[m["county"] != "全國"]
nat = m[m["county"] == "全國"].set_index("date")[NUM]
sums = cty.groupby("date")[NUM].sum()
ncty = cty.groupby("date")["county"].nunique()
diff = (sums.reindex(nat.index) - nat)
bad = diff[(diff != 0).any(axis=1)]
if len(bad):
    bad = bad.assign(n_county=ncty.reindex(bad.index))
check("各縣市月資料加總 = 全國（逐月）", bad, f"共 {len(nat)} 個月，縣市數 {sorted(ncty.unique())}")
miss_nat = sorted(set(cty["date"]) - set(nat.index))
check("每個有縣市資料的月份都有「全國」列", pd.DataFrame({"date": miss_nat}))

# 5. 縣市每年月資料加總 = 官方年度列
months = m.groupby(["year", "county"])["month"].apply(lambda s: sorted(s))
agg = m.groupby(["year", "county"])[NUM].sum()
agg["n_months"] = m.groupby(["year", "county"])["month"].nunique()
off = y.set_index(["year", "county"])[NUM]
cmp_ = agg.join(off, rsuffix="_off", how="outer")
rows = []
for (yr, c), r in cmp_.iterrows():
    same = all(r[k] == r[k + "_off"] for k in NUM)
    row = {"year": yr, "county": c, "n_months": r["n_months"], "match": same,
           "has_official": not pd.isna(r["total_days_off"])}
    if not same and row["has_official"]:
        row.update({f"{k}(月加總/官方)": f"{r[k]:g}/{r[k + '_off']:g}" for k in NUM if r[k] != r[k + "_off"]})
    rows.append(row)
res = pd.DataFrame(rows)
complete = res[res["n_months"] == 12]
is_known = complete.apply(lambda r: (int(r["year"]), r["county"]) in KNOWN_MISMATCH, axis=1)
for _, r in complete[is_known & ~complete["match"]].iterrows():
    print(f"[WARN] 已知來源不一致 {int(r['year'])} {r['county']}：{KNOWN_MISMATCH[(int(r['year']), r['county'])]}")
stale = [k for k in KNOWN_MISMATCH if complete[(complete["year"] == k[0]) & (complete["county"] == k[1]) & ~complete["match"]].empty]
check("例外清單的組合確實仍不一致（否則請移出清單）", pd.DataFrame({"stale": stale}))
strict = complete[~is_known]
check("完整 12 個月的 (年, 縣市)：月加總 = 官方年度列（不含已知例外）", strict[~strict["match"]],
      f"嚴格檢查 {len(strict)} 組，另有 {int(is_known.sum())} 組列為已知例外")
partial = res[res["n_months"] != 12]
print(f"\n月份不全的年份（不納入上面的 PASS/FAIL，僅列出比對結果）：")
if len(partial):
    p = partial.groupby("year").agg(組數=("county", "count"), 月數=("n_months", lambda s: sorted(set(map(lambda v: 0 if pd.isna(v) else int(v), s)))),
                                    與官方一致=("match", "sum"))
    print(p.to_string())
else:
    print("  無")
no_off = res[res["match"] == False]  # noqa: E712
print(f"  其中沒有官方年度列的組數: {int((~partial['has_official']).sum())} / {len(partial)}")

# 6. 缺月清單（不補值）
print("\n== 缺月清單（以資料涵蓋的 起訖月 之間的每個月為準）==")
all_dates = pd.period_range(m["date"].min(), m["date"].max(), freq="M").strftime("%Y-%m")
print(f"涵蓋 {m['date'].min()} ~ {m['date'].max()}，應有 {len(all_dates)} 個月；"
      f"資料中出現的月份 {m['date'].nunique()} 個")
gap = [d for d in all_dates if d not in set(m["date"])]
print("全體都沒有的月份:", gap if gap else "無")
for c in sorted(m["county"].unique()):
    have = set(m.loc[m["county"] == c, "date"])
    lack = [d for d in all_dates if d not in have]
    print(f"  {c}: 缺 {len(lack)} 個月" + (f" → {', '.join(lack)}" if lack else ""))

print("\n== 結果 ==")
print("全部通過" if not fails else f"未通過 {len(fails)} 項: {fails}")
sys.exit(1 if fails else 0)
