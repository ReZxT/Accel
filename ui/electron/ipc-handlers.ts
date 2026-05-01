import { ipcMain, BrowserWindow } from 'electron'
import { ServiceManager } from './services'
import { ConfigStore } from './config'

export function registerIpcHandlers(
  serviceManager: ServiceManager,
  configStore: ConfigStore,
  getWindow: () => BrowserWindow | null
): void {
  ipcMain.handle('services:list', () => {
    return serviceManager.list()
  })

  ipcMain.handle('services:start', async (_event, id: string) => {
    return serviceManager.start(id)
  })

  ipcMain.handle('services:stop', async (_event, id: string) => {
    return serviceManager.stop(id)
  })

  ipcMain.handle('services:restart', async (_event, id: string) => {
    return serviceManager.restart(id)
  })

  ipcMain.handle('config:get', (_event, key: string) => {
    return configStore.get(key as any)
  })

  ipcMain.handle('config:set', (_event, key: string, val: unknown) => {
    configStore.set(key as any, val as any)
  })

  ipcMain.on('window:openDevTools', () => {
    getWindow()?.webContents.openDevTools({ mode: 'detach' })
  })

  ipcMain.on('window:minimize', () => {
    getWindow()?.minimize()
  })

  ipcMain.on('window:toggleMaximize', () => {
    const win = getWindow()
    if (win) {
      win.isMaximized() ? win.unmaximize() : win.maximize()
    }
  })

  ipcMain.on('window:close', () => {
    getWindow()?.hide()
  })

  serviceManager.setOnChange((statuses) => {
    const win = getWindow()
    if (win && !win.isDestroyed()) {
      win.webContents.send('services:status', statuses)
    }
  })
}
