import * as fs from 'fs'
import * as path from 'path'
import { AccelConfig, DEFAULT_CONFIG } from './types'

const CONFIG_DIR = path.join(
  process.env.XDG_CONFIG_HOME || path.join(process.env.HOME || '/home/rezxt', '.config'),
  'accel'
)
const SETTINGS_PATH = path.join(CONFIG_DIR, 'settings.json')

export class ConfigStore {
  private config: AccelConfig

  constructor() {
    this.ensureDir()
    this.config = this.load()
  }

  private ensureDir(): void {
    if (!fs.existsSync(CONFIG_DIR)) {
      fs.mkdirSync(CONFIG_DIR, { recursive: true })
    }
  }

  private load(): AccelConfig {
    try {
      const raw = fs.readFileSync(SETTINGS_PATH, 'utf-8')
      return { ...DEFAULT_CONFIG, ...JSON.parse(raw) }
    } catch {
      return { ...DEFAULT_CONFIG }
    }
  }

  save(): void {
    fs.writeFileSync(SETTINGS_PATH, JSON.stringify(this.config, null, 2))
  }

  get<K extends keyof AccelConfig>(key: K): AccelConfig[K] {
    return this.config[key]
  }

  set<K extends keyof AccelConfig>(key: K, value: AccelConfig[K]): void {
    this.config[key] = value
    this.save()
  }

  getAll(): AccelConfig {
    return { ...this.config }
  }
}
