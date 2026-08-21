# Claude Code Security Review：誤報過濾規則

## 團隊通用家規

- 僅綁定 `127.0.0.1` 或 tailnet／私有網路的服務，若沒有公開 ingress，不視為本身的網路曝險。
- secrets 若只透過 macOS Keychain、Windows Credential Manager 或環境變數注入，不因「沒有寫在程式碼裡」而報警；但程式碼內仍出現 hardcoded secret、token、私鑰或可直接使用的憑證時，一律要報。
- 已知且有明確 ask-gate／人工確認的外發行為，不因外發本身報警；仍要檢查 ask-gate 是否可被繞過，以及資料是否越權外發。
- 面向公開網路的 webhook、bot、API 若缺少 rate limit、body／資源上限或重放保護，不得排除；至少以 Medium 報告資源耗盡或濫用風險。

## 本 repo 專屬脈絡

- NexPilot Public Trial 是 local-first terminal cockpit；只綁 `127.0.0.1` 或透過 Tailscale／其他私有網路提供的服務屬預期部署脈絡，但不得排除公開 bind、Origin／token bypass 或未授權 WebSocket／API 存取。
- PTY 以目前 OS user 執行是產品能力，不是誤報；仍要檢查 token、session、命令輸入、shell environment、安裝腳本與重連流程是否可被跨使用者或未授權客戶端利用。
