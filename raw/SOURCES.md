# 原始資料來源

本資料夾的檔案皆為政府官方公開資料，下載後未做任何修改。

## 空氣品質指標(AQI)概況（全國及縣市別、每月、各 AQI 等級站日數）

| 項目 | 內容 |
|---|---|
| 提供機關 | 環境部 |
| 資料集頁面 | https://data.gov.tw/dataset/89029 |
| 下載網址（第 1 頁） | `https://data.moenv.gov.tw/api/v2/stat_p_115?api_key=***&limit=1000&offset=0&sort=ImportDate desc&format=CSV` |
| 下載網址（第 2 頁） | `https://data.moenv.gov.tw/api/v2/stat_p_115?api_key=***&limit=1000&offset=1000&sort=ImportDate desc&format=CSV` |
| 下載日期 | 2026-10-12 |
| 授權 | 政府資料開放授權條款－第1版 |
| 編碼 | UTF-8 |

`api_key` 以 `***` 遮蔽。該 key 是 data.gov.tw 資料集頁面上公開附的 CSV 下載 key，不是個人申請的 key。

| 原檔 | 大小 | SHA-256 |
|---|---|---|
| `raw/stat_p_115_offset0.csv` | 46,767 bytes（1000 列資料） | `5be553d09543e72c081b19b569ddddfae679d5e61eee15a788b02ea7c2c28580` |
| `raw/stat_p_115_offset1000.csv` | 24,332 bytes（518 列資料） | `54c2122958e2b409b25b72b071afc0749c47f71683d35f62fd7e4ee6d5d965b4` |

## 欄位（依官方說明）

| 欄位 | 意義 |
|---|---|
| item1 | 統計期（民國年；月資料如 `113年 9月`，年度彙總列如 `113年`） |
| item2 | 統計區（縣市或「總計」） |
| value1 | 總站日數 |
| value2 | 良好 |
| value3 | 普通 |
| value4 | 對敏感族群不健康 |
| value5 | 對所有族群不健康 |
| value6 | 非常不健康 |
| value7 | 危害 |
| value8 | AQI>100 日數比率(%) |

## 備註

- 未下載「日空氣品質指標(AQI)」（各測站每日）資料。
