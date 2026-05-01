export type ServiceRuntime = 'process' | 'docker' | 'systemd'
export type ServiceHealth = 'healthy' | 'unhealthy' | 'stopped' | 'starting'
export type ServiceGroupId = 'inference' | 'core' | 'memory' | 'monitoring' | 'media' | 'dev'

export interface ServiceDef {
  id: string
  name: string
  runtime: ServiceRuntime
  command?: string
  compose?: string
  composeFile?: string
  unit?: string
  healthCheck: {
    url?: string
    interval: number
  }
  dependsOn: string[]
  autoStart: boolean
  group: ServiceGroupId
  accelerator?: 'gpu' | 'cpu'
  ports?: number[]
}

export interface ServiceStatus {
  id: string
  name: string
  group: ServiceGroupId
  health: ServiceHealth
  pid?: number
  uptime?: number
  accelerator?: 'gpu' | 'cpu'
  ports?: number[]
}

export interface AccelConfig {
  window: {
    width: number
    height: number
    x?: number
    y?: number
    maximized: boolean
  }
  hotkeys: {
    toggleWindow: string
  }
  autoStartGroups: ServiceGroupId[]
}

export const DEFAULT_CONFIG: AccelConfig = {
  window: {
    width: 1400,
    height: 900,
    maximized: false,
  },
  hotkeys: {
    toggleWindow: 'Super+Space',
  },
  autoStartGroups: [],
}
