export type MessageRole = 'user' | 'bot' | 'assistant'

export interface MessageImage {
  base64: string
  name: string
  type: string
  dataUrl?: string
}

export interface MessageFile {
  content: string
  name: string
  language: string
  size?: number
}

export interface Message {
  role: MessageRole
  content: string
  timestamp: string
  images?: MessageImage[]
  files?: MessageFile[]
  thoughts?: string
}

export interface ToolCall {
  tool: string
  args: Record<string, unknown>
}

export interface ToolResult {
  tool: string
  output: string
  image?: string
  mime_type?: string
}

export interface ApprovalRequest {
  request_id: string
  tool: string
  args: Record<string, unknown>
}

export type PanelMode = 'music' | 'canvas' | 'notes' | 'file' | 'calendar' | 'career'

export interface OpenPanelPayload {
  path?: string      // for notes/file: vault-relative path to open
  content?: string   // for file: inline content if no path
}

export type SSEChunk =
  | { type: 'text'; text: string }
  | { type: 'text_delta'; text: string }
  | { type: 'text_replace'; text: string }
  | { type: 'model_info'; model_id: string; model_name: string; provider: string }
  | { type: 'thinking'; text: string }
  | { type: 'tool_call'; tool: string; args: Record<string, unknown> }
  | { type: 'tool_result'; tool: string; output: string; image?: string; mime_type?: string }
  | { type: 'approval_request'; request_id: string; tool: string; args: Record<string, unknown> }
  | { type: 'tool_denied'; tool: string }
  | { type: 'canvas_command'; command: string; data: Record<string, unknown> }
  | { type: 'open_panel'; mode: PanelMode; payload?: OpenPanelPayload }
  | { type: 'play_queue'; tracks: Track[] }
  | { type: 'route'; route: Record<string, unknown> }
  | { type: 'error'; text: string }

export interface Track {
  id: string
  title: string
  artist: string
  album: string
  duration: number
  stream_url: string
  art_url: string
}

export interface NowPlaying {
  source: 'browser' | 'feishin'
  status: 'playing' | 'paused' | 'stopped'
  title: string
  artist: string
  album: string
  length: number
  position: number
  art_url: string
}

export type SessionId = 'standard' | 'coding' | 'architecture' | 'study' | 'music' | 'news' | 'career'

export interface Session {
  id: SessionId
  label: string
  icon: string
}

export type OverlayType = 'settings' | 'memory' | null

export interface ToolSetting {
  label: string
  desc: string
  irreversible: boolean
}

export type ToolPolicy = 'require' | 'auto'

export interface StreamingToolCall {
  id: string
  tool: string
  args: Record<string, unknown>
}

export interface StreamingToolResult {
  id: string
  tool: string
  output: string
  image?: string
  mime_type?: string
}

export interface StreamingApproval {
  request_id: string
  tool: string
  args: Record<string, unknown>
  resolved?: boolean
  approved?: boolean
}

export type ServiceRuntime = 'process' | 'docker' | 'systemd'
export type ServiceHealth = 'healthy' | 'unhealthy' | 'stopped' | 'starting'
export type ServiceGroupId = 'inference' | 'core' | 'memory' | 'monitoring' | 'media' | 'dev'

export interface ServiceStatus {
  id: string
  name: string
  group: ServiceGroupId
  health: ServiceHealth
  pid?: number
  uptime?: number
  accelerator?: 'gpu' | 'cpu'
  ports?: number[]
  modelName?: string
}
