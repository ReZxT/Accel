import { Tray, Menu, nativeImage, BrowserWindow } from 'electron'
import { ServiceStatus } from './types'

type HealthColor = 'green' | 'yellow' | 'red' | 'gray'

function createTrayIcon(color: HealthColor): Electron.NativeImage {
  const colors: Record<HealthColor, string> = {
    green: '#22c55e',
    yellow: '#fbbf24',
    red: '#f87171',
    gray: '#6b7280',
  }
  const fill = colors[color]

  const svg = `<svg width="16" height="16" xmlns="http://www.w3.org/2000/svg">
    <circle cx="8" cy="8" r="6" fill="${fill}" />
  </svg>`

  return nativeImage.createFromBuffer(Buffer.from(svg))
}

function computeColor(statuses: ServiceStatus[]): HealthColor {
  if (statuses.length === 0) return 'gray'
  const hasUnhealthy = statuses.some((s) => s.health === 'unhealthy')
  const hasHealthy = statuses.some((s) => s.health === 'healthy')
  if (hasUnhealthy) return 'red'
  if (hasHealthy) return 'yellow'
  return 'gray'
}

export class TrayManager {
  private tray: Tray
  private window: BrowserWindow
  private statuses: ServiceStatus[] = []

  constructor(window: BrowserWindow) {
    this.window = window
    this.tray = new Tray(createTrayIcon('gray'))
    this.tray.setToolTip('Accel')
    this.updateMenu()

    this.tray.on('click', () => {
      if (this.window.isVisible()) {
        this.window.hide()
      } else {
        this.window.show()
        this.window.focus()
      }
    })
  }

  updateStatuses(statuses: ServiceStatus[]): void {
    this.statuses = statuses
    const color = computeColor(statuses)
    this.tray.setImage(createTrayIcon(color))
    this.updateMenu()
  }

  private updateMenu(): void {
    const healthy = this.statuses.filter((s) => s.health === 'healthy').length
    const total = this.statuses.length
    const summary = total > 0 ? `Services: ${healthy}/${total} healthy` : 'No services configured'

    const menu = Menu.buildFromTemplate([
      { label: 'Show Accel', click: () => { this.window.show(); this.window.focus() } },
      { label: summary, enabled: false },
      { type: 'separator' },
      { label: 'Quit', click: () => { this.window.destroy(); process.exit(0) } },
    ])
    this.tray.setContextMenu(menu)
  }

  destroy(): void {
    this.tray.destroy()
  }
}
