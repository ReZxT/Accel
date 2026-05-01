import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('accel', {
  services: {
    list: () => ipcRenderer.invoke('services:list'),
    start: (id: string) => ipcRenderer.invoke('services:start', id),
    stop: (id: string) => ipcRenderer.invoke('services:stop', id),
    restart: (id: string) => ipcRenderer.invoke('services:restart', id),
    onStatus: (cb: (statuses: any[]) => void) => {
      ipcRenderer.on('services:status', (_event, data) => cb(data))
    },
  },
  window: {
    minimize: () => ipcRenderer.send('window:minimize'),
    toggleMaximize: () => ipcRenderer.send('window:toggleMaximize'),
    close: () => ipcRenderer.send('window:close'),
  },
  config: {
    get: (key: string) => ipcRenderer.invoke('config:get', key),
    set: (key: string, val: unknown) => ipcRenderer.invoke('config:set', key, val),
  },
})
