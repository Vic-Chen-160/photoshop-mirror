# photoshop-mirror

[English](README.md) · **繁體中文**

在 Photoshop 裡改稿，手機上即時看到。每動一個圖層，手機一秒內就更新。

手機不用裝 App，Photoshop 不用裝外掛，也不用註冊帳號。Mac 上打一行指令，手機開瀏覽器就能看。

[![photoshop-mirror demo](docs/demo.gif)](docs/demo.mp4)

## 為什麼做這個

Adobe 的 Preview CC / Device Preview 已經停止服務，Skala Preview 也沒人維護了。剩下的第三方外掛都跑在 Photoshop 的 Generator 程序裡，外掛一當掉，Generator 就整個停擺。

photoshop-mirror 不進 Photoshop。它用 Photoshop 內建的「**影像資源**」功能，讓你每次編輯時自動重新輸出 PNG，再透過 Wi-Fi 把這些 PNG 送到手機。

- **像素精準**：手機上看的是 Photoshop 實際輸出的 PNG，顏色、字重、1px 細線都準。畫面串流做不到這點。
- **多個工作區域、多個 PSD 一起看**：在手機選單裡切換。中途新開一個 PSD，3 秒內會自己出現。
- **PSD 放 NAS 也能用**：修掉了 Generator 在網路磁碟上會默默失敗的問題（見[PSD 放在網路磁碟](#psd-放在網路磁碟)）。
- **預設私密**：網址裡帶一段隨機碼，同一個 Wi-Fi 的同事看不到你還沒發表的稿。
- **不用另外裝東西**：用 macOS 內建的 Python 就能跑。

## 需求

- macOS、Photoshop CC（近幾年的版本都可以）
- Python 3。第一次打 `python3` 時如果跳出「安裝開發者工具」，按安裝就好，或執行 `xcode-select --install`
- Mac 和手機連同一個 Wi-Fi

## 安裝

```sh
curl -fsSL https://raw.githubusercontent.com/Vic-Chen-160/photoshop-mirror/main/install.sh | zsh
```

或是 clone 下來後執行 `./install.sh`。想在終端機直接顯示 QR code 的話，再裝 `brew install qrencode`。

## Photoshop 設定（只要做一次）

1. **設定 > 增效模組**：勾選「**啟動產生器**」。
2. **檔案 > 產生 > 影像資源**：打勾。這是每個 PSD 各自的開關，想看的每個 PSD 都要各開一次。
3. 把**工作區域**命名成 `preview.png`。

> 一定要用**工作區域**，不要用圖層群組。群組會裁到實際有像素的範圍，每改一次尺寸就跳動；工作區域會輸出完整畫布，尺寸固定。

工作區域命名語法：

```text
preview.png              原尺寸 PNG
200% preview.png         放大兩倍（在高解析度手機上比較銳利）
750x1334 preview.png     指定輸出尺寸
preview.jpg8             JPG，品質 8
1. home.png              數字前綴決定手機上的排列順序
```

## 使用

```sh
psmirror ~/Design/app/home.psd          # 一個 PSD
psmirror a.psd b.psd                    # 多個 PSD
psmirror ~/Design/app                   # 這個資料夾裡所有開了「影像資源」的 PSD
psmirror                                # 跟上次一樣
```

小技巧：打 `psmirror` 加一個空格，然後直接把 PSD 從 Finder 拖進終端機。

終端機會印出一個網址（和 QR code），手機打開後放著就好。

手機上的操作：

| 按鈕 | 功能 |
|---|---|
| 檔名 | 切換工作區域／PSD |
| 符合畫面・滿版寬度・1:1 像素 | 驗收版面用「**滿版寬度**」，那才是實際 App 裡的樣子；看細節用「**1:1**」 |
| 底色 | 深／淺／透明格 |
| 綠點＋時間 | 連線中，以及最後一次收到新圖的時間 |

頁面語言會跟著手機設定（英文或繁體中文）。

## PSD 放在網路磁碟

PSD 放在 NAS／SMB 上的話，加上 `--local`：

```sh
psmirror /Volumes/NAS/project/v3.psd --local
```

**不加會發生什麼事**：Generator 會先把圖算到本機的暫存資料夾，再用 `rename()` 搬進 `<檔名>-assets/`。`rename()` 不能跨檔案系統，所以每次寫檔都失敗（`EXDEV`）。Generator 會改用複製補救，但複製會跟它自己的刪除動作撞在一起，最後內部狀態壞掉。從那之後，就算工作區域完全正常，它也會一直報 `bounds completely clipped` 這個誤導人的錯誤。

**`--local` 做了什麼**：把 NAS 上的 `<檔名>-assets/` 換成指向 `~/.psmirror/assets/…` 的 symlink。Generator 看到的路徑沒變，但檔案實際寫到本機，`rename()` 就成功了。psmirror 執行期間，你另存新檔（v3 → v4）產生的新版本也會自動處理。

**Generator 已經卡住的話**：用 `--local` 重新啟動 psmirror，然後**關掉 PSD 再重新打開**。只取消再勾「影像資源」沒有用。

本機的副本不會無限長大，因為 Generator 是覆蓋舊檔，不會一直新增。PSD 搬走或刪掉之後留下的資料夾，可以這樣清：

```sh
psmirror --clean          # 只列出
psmirror --clean --yes    # 刪除孤兒資料夾
```

不要直接 `rm -rf ~/.psmirror/assets`：還在用的資料夾被刪掉後，NAS 上的 symlink 會斷掉，Generator 又會開始失敗。

## 所有參數

```text
psmirror <a.psd> [b.psd ...]   指定一個或多個 PSD
psmirror <資料夾>               找底下所有 *-assets
psmirror                       沿用上次的設定
  --local                      PSD 在網路磁碟時，把輸出導回本機
  --depth N                    在資料夾裡往下找幾層（預設 3）
  --port N                     埠號（預設 8000，被佔用會自動 +1）
  --new-token                  換一組私密網址，舊網址失效
  --no-token                   不加隨機碼，同網路的人都能看
psmirror --clean [--yes]       列出／清除本機的孤兒資料夾
```

## 疑難排解

**手機顯示「已連上伺服器，但監看的資料夾裡沒有圖」**
- 那個 PSD 的「**檔案 > 產生 > 影像資源**」還有勾嗎？
- 工作區域名稱有沒有 `.png` 結尾？
- 指的是資料夾嗎？預設只往下找 3 層，請指到靠近 PSD 的那層，或加 `--depth 5`。

**手機打不開網址**
- 兩台裝置連的是同一個 Wi-Fi 嗎？訪客網路常常會擋裝置之間的連線。
- macOS 防火牆：允許 Python 接收連線。
- Mac 的 IP 重開機後可能會變，請用這次印出來的網址。

**手機上的字看起來糊**
750px 寬的稿在 1179px 寬的 iPhone 上會被放大。把工作區域改名成 `200% preview.png`。

**還是不行？** 看 Generator 的日誌：

```sh
tail -f ~/Library/Logs/Adobe/Adobe\ Photoshop\ */Generator/generator_latest.txt
```

出現 `Render complete` 代表 Generator 正常；出現 `EXDEV` 代表要加 `--local`；日誌突然中斷、什麼都沒寫，可能是其他 Generator 外掛把程序弄當了。

## 運作原理

```text
Photoshop ─影像資源─▶ <檔名>-assets/preview.png
                                │
                psmirror（Mac 上的 Python HTTP 伺服器）
                                │  Wi-Fi
                           手機瀏覽器
              每 0.6 秒發 HEAD → Last-Modified／檔案大小變了就換圖
```

新圖會先在背景載好才換上，畫面不會閃。資料夾掃描跑在背景執行緒，遇到慢的網路磁碟會自動放慢頻率。

## 授權

MIT

Photoshop 是 Adobe Inc. 的商標。本專案與 Adobe 無關，也未獲 Adobe 背書。
