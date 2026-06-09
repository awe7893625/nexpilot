const statusEl = document.getElementById('status')
const connectBtn = document.getElementById('connect')
const disconnectBtn = document.getElementById('disconnect')
const copyBtn = document.getElementById('copy')
const pasteBtn = document.getElementById('paste')
const clearBtn = document.getElementById('clear')
const tokenPanel = document.getElementById('tokenPanel')
const tokenInput = document.getElementById('token')
const saveTokenBtn = document.getElementById('saveToken')
const terminalEl = document.getElementById('terminal')
const fallbackEl = document.getElementById('fallback')

const TOKEN_KEY = 'nexpilot_token'
const SESSION_KEY = 'nexpilot_session_id'
const HEARTBEAT_MS = 10000
const STALE_MS = 30000
const INPUT_BATCH_MS = 8

let ws = null
let term = null
let fitAddon = null
let fallbackBuffer = ''
let shouldReconnect = false
let reconnectTimer = null
let reconnectAttempt = 0
let heartbeatTimer = null
let lastPongAt = 0
let inputBuffer = ''
let inputTimer = null
let messageId = 0
let outputBuffer = ''
let outputFrame = null
let resizeTimer = null

function setStatus(text, mode = '') {
  statusEl.textContent = text
  statusEl.className = `status ${mode}`.trim()
}

function getToken() {
  const url = new URL(window.location.href)
  const urlToken = url.searchParams.get('token') || ''
  const token = urlToken || sessionStorage.getItem(TOKEN_KEY) || ''
  if (token) {
    sessionStorage.setItem(TOKEN_KEY, token)
    tokenInput.value = token
    tokenPanel.hidden = true
  }
  // A01: strip ?token= from the address bar immediately after reading it so the
  // secret does not persist in browser history, bookmarks, or proxy logs.
  if (urlToken) {
    url.searchParams.delete('token')
    window.history.replaceState({}, '', url.pathname + (url.search || '') + (url.hash || ''))
  }
  return token
}

function getSessionId() {
  let sessionId = sessionStorage.getItem(SESSION_KEY)
  if (!sessionId) {
    sessionId = window.crypto && window.crypto.randomUUID
      ? window.crypto.randomUUID()
      : `s-${Math.random().toString(36).slice(2)}-${Date.now().toString(36)}`
    sessionStorage.setItem(SESSION_KEY, sessionId)
  }
  return sessionId
}

function buildWsUrl(token) {
  const url = new URL('/ws/terminal', window.location.href)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.searchParams.set('token', token)
  url.searchParams.set('session', getSessionId())
  return url.toString()
}

function updateViewportHeight() {
  const height = window.visualViewport ? window.visualViewport.height : window.innerHeight
  document.documentElement.style.setProperty('--app-height', `${height}px`)
  scheduleResize()
}

function ensureTerminal() {
  if (window.Terminal) {
    if (!term) {
      term = new window.Terminal({
        allowProposedApi: false,
        cursorBlink: true,
        convertEol: true,
        disableStdin: false,
        fastScrollModifier: 'alt',
        fontFamily: 'Menlo, Monaco, Consolas, "Liberation Mono", monospace',
        fontSize: window.matchMedia('(max-width: 520px)').matches ? 13 : 14,
        scrollback: window.matchMedia('(max-width: 520px)').matches ? 12000 : 16000,
        theme: {
          background: '#050816',
          foreground: '#e5e7eb',
          cursor: '#22c55e',
          selectionBackground: '#334155'
        }
      })
      fitAddon = window.FitAddon ? new window.FitAddon.FitAddon() : null
      if (fitAddon) term.loadAddon(fitAddon)
      term.open(terminalEl)
      if (fitAddon) fitAddon.fit()
      term.onData(queueInput)
      terminalEl.addEventListener('pointerdown', () => term.focus())
      window.addEventListener('resize', scheduleResize)
      if (window.visualViewport) {
        window.visualViewport.addEventListener('resize', updateViewportHeight)
        window.visualViewport.addEventListener('scroll', updateViewportHeight)
      }
    }
    terminalEl.hidden = false
    fallbackEl.hidden = true
    return true
  }
  terminalEl.hidden = true
  fallbackEl.hidden = false
  return false
}

function writeOutput(data) {
  if (!data) return
  outputBuffer += data
  if (outputFrame) return
  outputFrame = window.requestAnimationFrame(() => {
    const chunk = outputBuffer
    outputBuffer = ''
    outputFrame = null
    if (ensureTerminal()) {
      term.write(chunk)
    } else {
      fallbackBuffer = (fallbackBuffer + chunk).slice(-200000)
      fallbackEl.textContent = fallbackBuffer
      fallbackEl.scrollTop = fallbackEl.scrollHeight
    }
  })
}

function queueInput(data) {
  if (!data) return
  const immediate = data.length > 1024 || /[\r\n\t\u0003\u001b]/.test(data)
  if (immediate) {
    flushInput()
    sendInput(data)
    return
  }
  inputBuffer += data
  if (!inputTimer) {
    inputTimer = window.setTimeout(flushInput, INPUT_BATCH_MS)
  }
}

function flushInput() {
  if (inputTimer) {
    window.clearTimeout(inputTimer)
    inputTimer = null
  }
  if (!inputBuffer) return
  const data = inputBuffer
  inputBuffer = ''
  sendInput(data)
}

function sendInput(data) {
  if (!ws || ws.readyState !== WebSocket.OPEN || !data) return
  for (let offset = 0; offset < data.length; offset += 4096) {
    ws.send(JSON.stringify({ type: 'input', id: ++messageId, data: data.slice(offset, offset + 4096) }))
  }
}

function scheduleResize() {
  if (resizeTimer) window.clearTimeout(resizeTimer)
  resizeTimer = window.setTimeout(sendResize, 80)
}

function sendResize() {
  if (!ws || ws.readyState !== WebSocket.OPEN || !term || !fitAddon) return
  fitAddon.fit()
  ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }))
}

function startHeartbeat() {
  stopHeartbeat()
  lastPongAt = Date.now()
  heartbeatTimer = window.setInterval(() => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    if (Date.now() - lastPongAt > STALE_MS) {
      ws.close()
      return
    }
    ws.send(JSON.stringify({ type: 'ping', at: Date.now() }))
  }, HEARTBEAT_MS)
}

function stopHeartbeat() {
  if (heartbeatTimer) {
    window.clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

function scheduleReconnect() {
  if (!shouldReconnect || reconnectTimer) return
  const delay = Math.min(8000, 500 * 2 ** reconnectAttempt)
  reconnectAttempt += 1
  setStatus(`Reconnecting in ${Math.round(delay / 1000)}s...`)
  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = null
    connect({ automatic: true })
  }, delay)
}

async function connect({ automatic = false } = {}) {
  const token = getToken()
  if (!token) {
    tokenPanel.hidden = false
    tokenInput.focus()
    setStatus('Token required', 'error')
    return
  }

  shouldReconnect = true
  ensureTerminal()
  if (!automatic) setStatus('Connecting...')
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    ws.close()
  }

  ws = new WebSocket(buildWsUrl(token))
  ws.addEventListener('open', () => {
    reconnectAttempt = 0
    connectBtn.disabled = true
    disconnectBtn.disabled = false
    setStatus('Connected', 'online')
    startHeartbeat()
    sendResize()
    if (term) term.focus()
  })
  ws.addEventListener('message', (event) => {
    const message = JSON.parse(event.data)
    if (message.type === 'session' && message.session) {
      sessionStorage.setItem(SESSION_KEY, message.session)
      if (message.reconnected) setStatus('Reconnected', 'online')
    }
    if (message.type === 'output') writeOutput(message.data || '')
    if (message.type === 'pong') lastPongAt = Date.now()
    if (message.type === 'error') setStatus(message.error || 'Error', 'error')
    if (message.type === 'exit') {
      setStatus(message.reason || 'Session ended')
      shouldReconnect = false
    }
  })
  ws.addEventListener('close', () => {
    stopHeartbeat()
    connectBtn.disabled = false
    disconnectBtn.disabled = true
    flushInput()
    if (shouldReconnect) {
      scheduleReconnect()
    } else {
      setStatus('Disconnected')
    }
  })
  ws.addEventListener('error', () => {
    setStatus('Connection error', 'error')
  })
}

function disconnect() {
  shouldReconnect = false
  if (reconnectTimer) {
    window.clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  stopHeartbeat()
  if (ws) {
    ws.close()
    ws = null
  }
}

async function copySelection() {
  const selected = term ? term.getSelection() : (window.getSelection() || '').toString()
  if (!selected) return
  await navigator.clipboard.writeText(selected)
  setStatus('Copied', 'online')
}

async function pasteClipboard() {
  const text = await navigator.clipboard.readText()
  if (text) {
    queueInput(text)
    if (term) term.focus()
  }
}

saveTokenBtn.addEventListener('click', () => {
  const token = tokenInput.value.trim()
  if (token) {
    sessionStorage.setItem(TOKEN_KEY, token)
    tokenPanel.hidden = true
    connect()
  }
})

connectBtn.addEventListener('click', () => connect())
disconnectBtn.addEventListener('click', disconnect)
copyBtn.addEventListener('click', () => copySelection().catch(() => setStatus('Copy blocked', 'error')))
pasteBtn.addEventListener('click', () => pasteClipboard().catch(() => setStatus('Paste blocked', 'error')))
clearBtn.addEventListener('click', () => {
  if (term) term.clear()
  fallbackBuffer = ''
  fallbackEl.textContent = ''
})

window.addEventListener('beforeunload', flushInput)
document.addEventListener('visibilitychange', () => {
  if (!document.hidden && shouldReconnect && (!ws || ws.readyState === WebSocket.CLOSED)) {
    connect({ automatic: true })
  }
})

updateViewportHeight()
getToken()
ensureTerminal()
setStatus('Ready')
