# NexPilot Public Trial 安全審查指示

每個 finding 必須包含：`attacker`、`precondition`、`action`、`result`、`impact`、`file:line`、`evidence`、`fix`。

請優先審查：

1. HTTP／WebSocket server 的 bind、Origin／Host 檢查、token 產生與驗證、session 綁定、重連與 replay。
2. terminal PTY 的輸入輸出、命令執行、環境變數、目前 OS user 權限、Windows ConPTY／POSIX 差異與 shell injection。
3. `--lan`、Tailscale／私有網路與公開網路邊界；公開可達 API／WebSocket 的 rate limit、連線數／輸出量上限與資源耗盡必須保留為 Medium 以上候選。
4. 安裝／執行腳本、token／credential log、CORS／安全 headers、錯誤回應與測試工具是否把私人控制能力暴露給遠端客戶端。

請把「本機或 tailnet 可用」與「無需認證即可公開控制 shell」分開判定，並對每一項給出實際資料流與行號。
