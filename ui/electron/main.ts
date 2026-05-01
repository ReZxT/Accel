import { app, BrowserWindow, globalShortcut } from 'electron'
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

function createWindow(): void {
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
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  }

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

app.whenReady().then(() => {
  registerIpcHandlers(serviceManager, configStore, () => mainWindow)
  createWindow()
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
