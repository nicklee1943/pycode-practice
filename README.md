# PyCode 練習

在本機練習 LeetCode（Python）的平台：左邊是官方題目，右邊是 Python 編輯器，可執行、提交、看提示與逐步解題引導。

程式和題庫是分開的兩個檔案：

| 檔案 | 內容 |
|---|---|
| `pycode-practice-XXXXXXXX.tar.gz` | 程式（前後端、編輯器、Python 套件），**不含題庫** |
| `question-bank-XXXXXXXX.pcbank` | 題庫（題目、測資、解題引導、官方題目內容與圖片），單一檔案 |

## 安裝（解壓縮即完成）

```bash
tar -xzf pycode-practice-XXXXXXXX.tar.gz
```

Windows 10 以上與 Ubuntu 都內建 `tar`。解壓縮後會得到 `pycode-practice/` 資料夾。

## 啟動

| 系統 | 方式 |
|---|---|
| Windows | 雙擊 `pycode-practice\run.bat` |
| Ubuntu / Linux | `cd pycode-practice && ./run.sh` |

啟動後會自動開啟瀏覽器；若沒有，請打開畫面上顯示的網址（預設 `http://127.0.0.1:5000`）。
關閉：在啟動的視窗按 `Ctrl+C`。

**第一次啟動**：畫面會顯示「尚未載入題庫」，按「📂 選擇題庫檔…」選 `question-bank-XXXXXXXX.pcbank` 即可開始練習。

### 需求

- **Python 3.10 以上**
  - Ubuntu 22.04 / 24.04 已內建；沒有的話：`sudo apt install python3`
  - Windows：到 <https://www.python.org/downloads/> 安裝，安裝時勾選「Add python.exe to PATH」
- **不需要** `pip install`，**不需要網路**：Flask、PyYAML、程式碼編輯器都已包含在內，題目內容與圖片在題庫檔裡。

### 選項

```bash
./run.sh --port 8000        # 指定連接埠（被佔用時會自動往後找）
./run.sh --no-browser       # 不自動開啟瀏覽器
./run.sh --host 0.0.0.0     # 開放給區網（注意：任何人都能在這台電腦上執行程式碼）
```

Windows 用法相同：`run.bat --port 8000`。

## 題庫

- **更換 / 更新題庫**：「📚 題庫清單」→「🔄 更換題庫」→ 選新的 `.pcbank` 檔。
  更換前會自動把目前的題庫備份到 `exports/`；你的程式碼與紀錄都不受影響（以題目 id 對應）。
- **匯出題庫**：「📚 題庫清單」→「📦 匯出題庫」，把目前的題庫封裝成 `.pcbank`（存在 `exports/`），可以拿到別台電腦載入。
- 使用中的題庫檔放在 `bank/`；直接把 `.pcbank` 檔放進這個資料夾也可以（有多個時用最新的）。
- ⚠ 題庫檔裡有判題用的程式（部分題目的 checker），只載入你信任來源的題庫檔。

## 搬移練習進度

新安裝是乾淨的（不含程式碼與紀錄）。要把舊電腦的進度搬過來：

1. 舊電腦：標題列「⬇ 匯出」→ 選 YAML 或 JSON，檔案會存在 `exports/`
2. 把檔案複製到新電腦
3. 新電腦：「⬆ 匯入」→「從電腦選擇檔案…」

## 資料夾

| 路徑 | 內容 |
|---|---|
| `bank/` | 使用中的題庫檔（`.pcbank`） |
| `solutions/` | 你的程式碼與完成紀錄（自動建立） |
| `exports/` | 匯出檔、題庫檔、各種自動備份 |
| `cache/` | 執行時從 LeetCode 補抓的題目內容（題庫檔裡沒有時才會用到） |
| `vendor/` | 附帶的 Python 套件（Flask、PyYAML…） |
| `static/` | 前端（含離線版 Monaco 編輯器） |

## 注意

- 你寫的程式碼會直接在這台電腦上執行（沒有沙盒），預設只開放本機連線。
