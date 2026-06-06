# NexPilot Private Beta Report

版本：0.1.0 private beta  
狀態：本地 package 完成；GitHub private repo 發布腳本已備妥；實際 push 需先修復 `gh` 登入。

## 1. 這是什麼

NexPilot private beta 是一個「手機控制自己電腦 terminal」的本地優先工具。

朋友在自己的 Mac 或 Linux 電腦跑一個小 agent，agent 會印出一個帶 token 的網址。朋友用手機打開該網址，就能在手機瀏覽器裡操作那台電腦的 shell。

這版不是公網雲端 relay，也不是把 Rain 的 M4/NexDesk/Kai 系統開給別人用。它只在測試者自己的電腦上跑。

## 2. 誰適合測

適合：

- 會基本使用 terminal 的朋友。
- 有 Mac 或 Linux 電腦。
- 手機和電腦在同一個 Wi-Fi，或兩台都裝 Tailscale。
- 願意接受 private beta 的限制。

不適合：

- 完全不會 terminal 的一般消費者。
- Windows only 使用者。
- 想直接暴露到公網的人。
- 想要完整 Termius 等級連線管理、多人權限、雲端同步的人。

## 3. 給朋友的使用教學

### 3.1 取得權限

目前建議 GitHub repo 先維持 private。朋友需要先被邀請到：

```text
https://github.com/awe7893625/nexpilot-private-beta
```

注意：這個 repo 目前尚未 push，因為本機 GitHub CLI token 失效。完成 `gh auth login` 後可用 `scripts/publish-github.sh` 建立並推上 private repo。

### 3.2 安裝

朋友收到 GitHub invite 後，在電腦 terminal 執行：

```bash
git clone https://github.com/awe7893625/nexpilot-private-beta.git
cd nexpilot-private-beta
bash scripts/install.sh
```

這會建立 `.venv`，並安裝 NexPilot private beta。

### 3.3 同一台電腦先試跑

先用 localhost 模式確認可以跑：

```bash
bash scripts/run-local.sh
```

看到類似輸出：

```text
NexPilot public trial agent
  Version: 0.1.0
  Bind:    127.0.0.1:8765
  Shell:   /bin/zsh

Open: http://127.0.0.1:8765/?token=...
```

在同一台電腦的瀏覽器打開 `Open:` 後面的網址。看到 NexPilot 頁面後按 `Connect`，應該會出現 shell。

### 3.4 手機同 Wi-Fi 使用

確認 localhost 可用後，改跑 LAN 模式：

```bash
bash scripts/run-lan.sh
```

它會印出手機可用網址：

```text
Phone on same Wi-Fi: http://192.168.x.x:8765/?token=...
```

在手機瀏覽器打開該網址，按 `Connect`，就能操作電腦 shell。

### 3.5 用 Tailscale 遠端使用

如果朋友想在外面用手機連家裡或公司的電腦：

1. 電腦和手機都安裝 Tailscale。
2. 兩台裝置登入同一個 tailnet。
3. 電腦執行：

```bash
bash scripts/run-lan.sh
```

4. 手機打開：

```text
http://電腦的_Tailscale_IP:8765/?token=...
```

不要直接把 `8765` port 開到公網。

### 3.6 停止與撤銷

在電腦 terminal 按：

```text
Ctrl-C
```

agent 停止後，原本那個 token URL 立刻失效。下次不指定 `--token` 啟動時，會產生新的 token。

## 4. 安全注意事項

### 4.1 URL 就是密碼

印出來的 URL 裡有 token：

```text
http://host:8765/?token=...
```

誰拿到這個 URL，誰就能控制該 shell。不要截圖傳群組，不要貼公開地方。

### 4.2 不要用 root/admin 跑

NexPilot 會用啟動它的 OS 使用者身份開 shell。不要用 `sudo` 跑，不要用 root 跑。

### 4.3 不支援公網直連

這版只建議：

- localhost
- 同 Wi-Fi
- Tailscale/WireGuard/private network

不建議：

- router port forwarding
- 直接放到 public IP
- 用無 auth reverse proxy 暴露

### 4.4 目前不儲存 terminal transcript

NexPilot private beta 不會主動把 terminal output 寫入資料庫。shell history 仍由使用者自己的 shell 管理，例如 zsh/bash history。

## 5. 疑難排解

### 手機打不開網址

可能原因：

- 沒有用 `bash scripts/run-lan.sh`，只跑了 localhost 模式。
- 手機和電腦不在同一個 Wi-Fi。
- 電腦 firewall 擋住 port `8765`。
- 公司/學校 Wi-Fi 禁止裝置互連。

建議：

- 先在電腦瀏覽器打開 localhost URL。
- 再確認手機能 ping 或連到電腦 IP。
- 若是跨網路，改用 Tailscale。

### 顯示 token 錯誤

可能原因：

- URL 複製不完整。
- 用到舊 token。
- agent 已重啟並產生新 token。

建議：

- 重新複製 terminal 裡最新印出的完整 URL。

### terminal 沒反應

可能原因：

- WebSocket 被代理或網路環境擋住。
- shell 啟動失敗。
- 手機瀏覽器太舊。

建議：

```bash
bash scripts/doctor.sh
```

如果 agent 正在本機 `127.0.0.1:8765`，也可跑：

```bash
python3 scripts/smoke-terminal.py --url 'ws://127.0.0.1:8765/ws/terminal?token=test-token'
```

## 6. 技術架構

### 6.1 元件

```text
Phone Browser
  |
  | HTTP + WebSocket, token in URL/query
  v
FastAPI NexPilot Agent
  |
  | POSIX PTY
  v
Local Shell (/bin/zsh, /bin/sh, etc.)
```

主要檔案：

- `src/nexpilot_public/server.py`：FastAPI server、token auth、HTTP routes、WebSocket route。
- `src/nexpilot_public/terminal.py`：POSIX PTY shell session。
- `src/nexpilot_public/static/index.html`：手機瀏覽器入口。
- `src/nexpilot_public/static/app.js`：WebSocket terminal client。
- `scripts/secret-scan.py`：release tree 機密掃描。
- `scripts/doctor.sh`：本地 compile + leak scan + tests。
- `scripts/prepublish.sh`：發布前 gate。
- `scripts/publish-github.sh`：private GitHub repo 建立/推送腳本。

### 6.2 API

#### `GET /`

回傳 NexPilot web UI。

#### `GET /api/status`

需要 token。用於確認 agent 狀態。

token 可放在：

- `x-nexpilot-token`
- `Authorization: Bearer ...`
- `?token=...`

成功回傳：

```json
{
  "ok": true,
  "version": "0.1.0",
  "platform": "posix",
  "cwd": "/Users/example",
  "shell": "/bin/zsh",
  "host": "127.0.0.1",
  "port": 8765
}
```

#### `WS /ws/terminal?token=...`

手機 UI 使用的 terminal WebSocket。

Browser -> Agent：

```json
{"type":"input","data":"ls\n"}
```

```json
{"type":"resize","cols":100,"rows":32}
```

```json
{"type":"ping"}
```

Agent -> Browser：

```json
{"type":"output","data":"..."}
```

```json
{"type":"pong"}
```

```json
{"type":"error","error":"..."}
```

### 6.3 Auth model

這版是 single-token bearer access。

token 來源：

1. CLI `--token`
2. env `NEXPILOT_TOKEN`
3. 啟動時自動 `secrets.token_urlsafe(24)` 產生

優點：

- 簡單。
- 不需要帳號系統。
- 停掉 process 即撤銷。

限制：

- 沒有多使用者。
- 沒有 read-only mode。
- token URL 洩漏就等於 shell access 洩漏。

### 6.4 Terminal implementation

`terminal.py` 用 POSIX PTY：

- `pty.fork()` 建立 child shell。
- parent process 持有 PTY fd。
- WebSocket 收到 input 後寫入 fd。
- async pump loop 從 fd 讀 output，送回 browser。
- resize 透過 `termios.TIOCSWINSZ` 調整 terminal size。

目前支援：

- macOS
- Linux

目前不支援：

- Windows ConPTY

### 6.5 Frontend

前端是純靜態頁：

- HTML/CSS/JS
- xterm.js 透過 CDN 載入
- token 儲存在 `sessionStorage`
- WebSocket 自動帶 token query

這樣 packaging 很輕，但也有供應鏈限制：正式產品應把 xterm assets vendor 進 repo，避免依賴 CDN。

### 6.6 CI 與 release gate

GitHub Actions：

```text
.github/workflows/ci.yml
```

跑：

- Python 3.9
- Python 3.12
- package install
- compile
- secret scan
- pytest

本地 gate：

```bash
bash scripts/prepublish.sh
```

它會跑：

- `bash scripts/doctor.sh`
- 確認 git working tree clean

### 6.7 Secret scan policy

`scripts/secret-scan.py` 會擋：

- private key block
- GitHub token pattern
- OpenAI style token pattern
- Slack token pattern
- AWS key pattern
- Rain 本機絕對路徑
- 已知內部 Tailscale IP
- `ND_ADMIN_SECRET`
- OpenAI/Anthropic/Google/Gemini/Tailscale/Cloudflare env value
- `.db` / `.sqlite` / `.pem` / `.key` / `.log` / `.bak` 等檔案
- `.m4_data` / `.m4_runtime` / backups / secrets / private 等路徑

## 7. 目前驗證結果

已通過：

- `bash scripts/prepublish.sh`
- `python3 scripts/secret-scan.py .`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python3 -m pytest`
- HTTP token gate：無 token 401，有 token 200
- static UI fetch
- WebSocket terminal marker round-trip
- release tarball archive
- git bundle

release artifacts：

```text
dist/nexpilot-private-beta-0.1.0-b324eac.tar.gz
dist/nexpilot-private-beta-0.1.0-b324eac.tar.gz.sha256
dist/nexpilot-private-beta-b324eac.bundle
dist/nexpilot-private-beta-b324eac.bundle.sha256
```

tarball SHA256：

```text
ce12c8ba664b38ea8d0bd8b740b63b9621d9ab4313dea76ca31b0ebb72641ad2
```

## 8. GitHub 發布狀態

已準備：

```bash
bash scripts/publish-github.sh
```

預設目標：

```text
awe7893625/nexpilot-private-beta
```

行為：

- 檢查 `gh auth status`
- 跑 `scripts/prepublish.sh`
- 若 repo 不存在，建立 private repo
- 加 remote `origin`
- push `main`

目前阻塞：

```text
gh auth status 顯示 awe7893625 token invalid
```

修復：

```bash
gh auth login -h github.com
cd <local-nexpilot-public-clone>
bash scripts/publish-github.sh
```

## 9. Roadmap

短期：

- 實體手機 PWA smoke。
- 把 xterm.js assets vendored 進 repo，移除 CDN 依賴。
- 補 Windows ConPTY public path。
- 補 native installer 或一鍵 zip。

中期：

- 多 profile / saved devices。
- read-only / confirm-before-enter mode。
- session recording 可選項。
- 更好的手機鍵盤列、複製貼上、快捷鍵。

長期：

- E2E cloud relay。
- 多使用者權限。
- audit logs。
- host trust/pairing ceremony。
- 正式簽章 installer。

## 10. 對外口徑

可以說：

```text
NexPilot private beta lets you run a small local agent on your Mac/Linux computer and control that shell from your phone over same Wi-Fi or Tailscale.
```

不要說：

```text
已經跟 Termius 一樣完整。
```

不要說：

```text
可以安全直接開到公網。
```

不要說：

```text
支援 Windows。
```
