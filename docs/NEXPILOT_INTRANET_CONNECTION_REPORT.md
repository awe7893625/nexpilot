# NexPilot 內網 / Tailscale 連線報告

版本：0.1.0 private beta  
用途：讓朋友用手機控制自己的電腦 terminal  
建議連線方式：同 Wi-Fi 內網或 Tailscale 私有網路  
不建議：直接開到公網

## 1. 結論

NexPilot private beta 目前採 **local-first / private-network-first** 架構。

朋友不是連到 Rain 的 M4、NexDesk、Kai，也不是加入 Rain 的內部 tailnet。正確方式是：

- 朋友在自己的電腦上跑 NexPilot agent。
- 朋友用自己的手機連那台電腦。
- 連線走同 Wi-Fi 內網，或朋友自己的 Tailscale tailnet。
- token URL 只給該朋友本人使用。

一句話口徑：

```text
NexPilot private beta runs locally on your computer. Your phone connects over same Wi-Fi or your own Tailscale network. Do not expose it directly to the public internet.
```

## 2. 連線方式 A：同 Wi-Fi / 同 LAN

適合情境：

- 手機和電腦在同一個家用 Wi-Fi。
- 辦公室網路允許裝置互相連線。
- 想最快測試。

朋友在電腦執行：

```bash
bash scripts/run-lan.sh
```

電腦會印出類似：

```text
Phone on same Wi-Fi: http://192.168.1.23:8765/?token=...
```

朋友用手機瀏覽器打開這個網址，按 `Connect`，就能進 terminal。

### 常見問題

如果手機打不開：

- 手機和電腦可能不在同一個 Wi-Fi。
- 公司/學校 Wi-Fi 可能隔離裝置。
- 電腦 firewall 可能擋住 `8765`。
- 電腦 IP 變了，需要重新看 terminal 印出的網址。

## 3. 連線方式 B：Tailscale，推薦遠端使用

適合情境：

- 朋友在外面想用手機連家裡電腦。
- 同 Wi-Fi 不穩。
- 想避免 router port forwarding。

正確做法：

1. 朋友自己的電腦安裝 Tailscale。
2. 朋友自己的手機安裝 Tailscale。
3. 兩台登入朋友自己的同一個 Tailscale 帳號/tailnet。
4. 電腦執行：

```bash
bash scripts/run-lan.sh
```

5. 手機打開：

```text
http://電腦的_Tailscale_IP:8765/?token=...
```

重點：

- 不需要 Rain 的 Tailscale。
- 不需要 Rain 的 M4/NexDesk。
- 不要把朋友加入 Rain 的內部 tailnet。
- Tailscale 只是幫朋友自己的手機找到朋友自己的電腦。

## 4. 不要使用的方式

不要：

- router port forwarding `8765` 到 public internet
- 把 NexPilot 放在 public IP
- 把 token URL 貼到群組
- 用無驗證的 reverse proxy 暴露
- 用 root/admin 跑 agent

原因：

- token URL 等於 shell access。
- 公網掃描和暴力嘗試風險高。
- 這版還沒有完整 public relay、multi-user auth、audit log、rate limit。

## 5. 技術架構

```text
Phone Browser
  |
  | HTTP + WebSocket
  | token in URL/query
  v
NexPilot Local Agent
  |
  | POSIX PTY
  v
Computer Shell
```

連線路徑：

- Same Wi-Fi：手機直接連 `192.168.x.x:8765`
- Tailscale：手機直接連 `100.x.x.x:8765`
- Public internet：不支援

## 6. 安全模型

### Token

agent 啟動時會產生 token。

URL 長這樣：

```text
http://host:8765/?token=...
```

誰拿到 URL，誰就能控制該 shell。停止 agent 後 token 失效。

### 權限

shell 權限等於啟動 agent 的 OS 使用者。

所以：

- 用一般使用者跑。
- 不要 sudo。
- 不要 root。

### 資料

private beta 不會把 terminal transcript 寫進資料庫，也不連 Rain 的中控台。

## 7. 給朋友的最短教學

```bash
git clone https://github.com/awe7893625/nexpilot-private-beta.git
cd nexpilot-private-beta
bash scripts/install.sh
bash scripts/run-lan.sh
```

然後用手機打開 terminal 印出的 `Phone on same Wi-Fi` URL。

如果要遠端用，先讓手機和電腦都登入朋友自己的 Tailscale，再用電腦的 Tailscale IP 打開。

## 8. 目前限制

- Windows 已有 private beta ConPTY path，但尚未完成 Windows 實機長時間驗證。
- 尚未做實體手機長時間 soak。
- 尚未提供 native installer。
- 尚未提供公網 cloud relay。
- Terminal 已補 reconnect、output replay、heartbeat、batching、paste/copy/clear，
  但尚未達到 Termius 完整功能等級。
- Source beta 不能技術上阻止收件人複製；目前用 private invite、非轉讓條款、
  per-tester package 與 checksum 降低亂轉傳風險。

## 9. GitHub 狀態

local repo 已完成，private publish script 已備妥：

```bash
bash scripts/publish-github.sh
```

但目前實際 push blocked，因為本機 GitHub CLI token 失效：

```text
gh auth status -> token invalid
```

修復後執行：

```bash
gh auth login -h github.com
cd <local-nexpilot-public-clone>
bash scripts/publish-github.sh
```

預設會建立 private repo：

```text
awe7893625/nexpilot-private-beta
```
