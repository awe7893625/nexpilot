const statusEl = document.getElementById('status')
const connectBtn = document.getElementById('connect')
const disconnectBtn = document.getElementById('disconnect')
const tokenPanel = document.getElementById('tokenPanel')
const tokenInput = document.getElementById('token')
const saveTokenBtn = document.getElementById('saveToken')
const terminalEl = document.getElementById('terminal')
const fallbackEl = document.getElementById('fallback')

let ws = null
let term = null
let fitAddon = null
let fallbackBuffer = ''

function setStatus(text, mode = '') {
  statusEl.textContent = text
  statusEl.className = `status ${mode}`.trim()
}

function getToken() {
  const url = new URL(window.location.href)
  const token = url.searchParams.get('token') || sessionStorage.getItem('nexpilot_token') || ''
  if (token) {
    sessionStorage.setItem('nexpilot_token', token)
    tokenInput.value = token
    tokenPanel.hidden = true
  }
  return token
}

function buildWsUrl(token) {
  const url = new URL('/ws/terminal', window.location.href)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.searchParams.set('token', token)
  return url.toString()
}

function ensureTerminal() {
  if (window.Terminal) {
    if (!term) {
      term = new window.Terminal({
        cursorBlink: true,
        convertEol: true,
        fontFamily: 'Menlo, Monaco, Consolas, monospace',
        fontSize: 14,
        scrollback: 8000,
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
      term.onData((data) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'input', data }))
        }
      })
      window.addEventListener('resize', sendResize)
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
  if (ensureTerminal()) {
    term.write(data)
  } else {
    fallbackBuffer += data
    fallbackEl.textContent = fallbackBuffer
    fallbackEl.scrollTop = fallbackEl.scrollHeight
  }
}

function sendResize() {
  if (!ws || ws.readyState !== WebSocket.OPEN || !term || !fitAddon) return
  fitAddon.fit()
  ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }))
}

async function connect() {
  const token = getToken()
  if (!token) {
    tokenPanel.hidden = false
    tokenInput.focus()
    setStatus('Token required', 'error')
    return
  }

  ensureTerminal()
  setStatus('Connecting...')
  ws = new WebSocket(buildWsUrl(token))
  ws.addEventListener('open', () => {
    connectBtn.disabled = true
    disconnectBtn.disabled = false
    setStatus('Connected', 'online')
    sendResize()
  })
  ws.addEventListener('message', (event) => {
    const message = JSON.parse(event.data)
    if (message.type === 'output') writeOutput(message.data || '')
    if (message.type === 'error') setStatus(message.error || 'Error', 'error')
  })
  ws.addEventListener('close', () => {
    connectBtn.disabled = false
    disconnectBtn.disabled = true
    setStatus('Disconnected')
  })
  ws.addEventListener('error', () => {
    setStatus('Connection error', 'error')
  })
}

function disconnect() {
  if (ws) {
    ws.close()
    ws = null
  }
}

saveTokenBtn.addEventListener('click', () => {
  const token = tokenInput.value.trim()
  if (token) {
    sessionStorage.setItem('nexpilot_token', token)
    tokenPanel.hidden = true
    connect()
  }
})

connectBtn.addEventListener('click', connect)
disconnectBtn.addEventListener('click', disconnect)

getToken()
ensureTerminal()
setStatus('Ready')
