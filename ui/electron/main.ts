import { app, BrowserWindow, globalShortcut } from 'electron'
import * as http from 'http'
import * as fs from 'fs'
import * as path from 'path'
import { ConfigStore } from './config'
import { ServiceManager } from './services'
import { TrayManager } from './tray'
import { registerIpcHandlers } from './ipc-handlers'

const isDev = !app.isPackaged

let mainWindow: BrowserWindow | null = null
let trayManager: TrayManager | null = null
const configStore = new ConfigStore()
const serviceManager = new ServiceManager()

// ---------------------------------------------------------------------------
// Local proxy server (production only)
// Mirrors the Vite dev proxy so fetch('/chat') etc. work when loaded from file://
// ---------------------------------------------------------------------------

const MIME: Record<string, string> = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
  '.ico': 'image/x-icon',
}

interface ProxyRule {
  prefix: string
  target: string
  rewrite?: (p: string) => string
}

const PROXY_RULES: ProxyRule[] = [
  { prefix: '/chat',     target: 'http://localhost:8100' },
  { prefix: '/cancel',   target: 'http://localhost:8100' },
  { prefix: '/approve',  target: 'http://localhost:8100' },
  { prefix: '/command',  target: 'http://localhost:8100' },
  { prefix: '/models',   target: 'http://localhost:8100' },
  { prefix: '/settings', target: 'http://localhost:8100' },
  { prefix: '/voice',    target: 'http://localhost:8100' },
  { prefix: '/music',    target: 'http://localhost:8100' },
  { prefix: '/calendar', target: 'http://localhost:8100' },
  { prefix: '/career',   target: 'http://localhost:8100' },
  { prefix: '/canvas',   target: 'http://localhost:8100' },
  { prefix: '/notes',    target: 'http://localhost:8100' },
  { prefix: '/health',   target: 'http://localhost:8100' },
  { prefix: '/status',   target: 'http://localhost:8100' },
  { prefix: '/session',  target: 'http://localhost:9200' },
  { prefix: '/profile',  target: 'http://localhost:9200' },
  { prefix: '/ingest',   target: 'http://localhost:9200' },
  { prefix: '/kb',       target: 'http://localhost:9200' },
  {
    prefix: '/navidrome',
    target: 'http://localhost:4533',
    rewrite: (p) => p.replace(/^\/navidrome/, '') || '/',
  },
  {
    prefix: '/prometheus',
    target: 'http://localhost:9090',
    rewrite: (p) => p.replace(/^\/prometheus/, '') || '/',
  },
]

function startProxyServer(distPath: string): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      const url = req.url || '/'

      const rule = PROXY_RULES.find((r) => url === r.prefix || url.startsWith(r.prefix + '/') || url.startsWith(r.prefix + '?'))
      if (rule) {
        const targetPath = rule.rewrite ? rule.rewrite(url) : url
        const targetUrl = new URL(targetPath, rule.target)

        const proxyHeaders = { ...req.headers, host: targetUrl.host }
        delete proxyHeaders['content-length'] // let backend determine

        const proxyReq = http.request(
          { hostname: targetUrl.hostname, port: targetUrl.port, path: targetUrl.pathname + targetUrl.search, method: req.method, headers: proxyHeaders },
          (proxyRes) => {
            res.writeHead(proxyRes.statusCode!, proxyRes.headers)
            proxyRes.pipe(res, { end: true })
          }
        )
        proxyReq.on('error', () => {
          if (!res.headersSent) res.writeHead(502)
          res.end('Backend unavailable')
        })
        req.pipe(proxyReq, { end: true })
        return
      }

      // Static file serving with SPA fallback
      let filePath = path.join(distPath, url.split('?')[0])
      if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
        filePath = path.join(distPath, 'index.html')
      }
      const ext = path.extname(filePath)
      res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' })
      fs.createReadStream(filePath).pipe(res)
    })

    server.on('error', reject)
    server.listen(0, '127.0.0.1', () => {
      resolve((server.address() as { port: number }).port)
    })
  })
}

// ---------------------------------------------------------------------------

async function createWindow(): Promise<void> {
  const windowConfig = configStore.get('window')

  mainWindow = new BrowserWindow({
    width: windowConfig.width,
    height: windowConfig.height,
    x: windowConfig.x,
    y: windowConfig.y,
    minWidth: 800,
    minHeight: 600,
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#0a0a0a',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  if (windowConfig.maximized) {
    mainWindow.maximize()
  }

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
  } else {
    const distPath = path.join(__dirname, '..', 'dist')
    const port = await startProxyServer(distPath)
    mainWindow.loadURL(`http://127.0.0.1:${port}`)
  }

  mainWindow.on('focus', () => {
    mainWindow?.webContents.send('window:focus')
  })

  mainWindow.on('close', (e) => {
    e.preventDefault()
    mainWindow?.hide()
  })

  mainWindow.on('resize', saveWindowState)
  mainWindow.on('move', saveWindowState)

  trayManager = new TrayManager(mainWindow)

  serviceManager.setOnChange((statuses) => {
    trayManager?.updateStatuses(statuses)
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('services:status', statuses)
    }
  })

  serviceManager.probeAll()
}

function saveWindowState(): void {
  if (!mainWindow) return
  const bounds = mainWindow.getBounds()
  configStore.set('window', {
    width: bounds.width,
    height: bounds.height,
    x: bounds.x,
    y: bounds.y,
    maximized: mainWindow.isMaximized(),
  })
}

function registerHotkeys(): void {
  const hotkeys = configStore.get('hotkeys')

  globalShortcut.register(hotkeys.toggleWindow, () => {
    if (!mainWindow) return
    if (mainWindow.isVisible() && mainWindow.isFocused()) {
      mainWindow.hide()
    } else {
      mainWindow.show()
      mainWindow.focus()
    }
  })
}

app.whenReady().then(async () => {
  registerIpcHandlers(serviceManager, configStore, () => mainWindow)
  await createWindow()
  registerHotkeys()
})

app.on('window-all-closed', () => {
  // Don't quit — tray keeps the app alive
})

app.on('activate', () => {
  mainWindow?.show()
})

app.on('before-quit', () => {
  serviceManager.destroy()
  trayManager?.destroy()
  mainWindow?.destroy()
})
