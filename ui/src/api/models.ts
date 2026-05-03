import { apiFetch } from './client'

export interface ModelInfo {
  id: string
  name: string
  provider: string
  context_window: number
  capabilities: string[]
  supports_thinking: boolean
  supports_vision: boolean
}

export interface ActiveModels {
  chat: string
  curator: string
  embeddings: string
  chat_details: {
    name: string
    provider: string
    supports_thinking: boolean
    supports_vision: boolean
    context_window: number
  }
}

export interface ModelsState {
  chat_model_id: string
  curator_model_id: string
  embeddings_model_id: string
  chat: {
    id: string
    name: string
    provider: string
    context_window: number
    supports_thinking: boolean
    supports_vision: boolean
  }
  curator: {
    id: string
    name: string
    provider: string
  }
  embeddings: {
    id: string
    name: string
    provider: string
  }
  available: ModelInfo[]
}

export async function getModels(): Promise<ModelsState> {
  return apiFetch<ModelsState>('/models')
}

export async function getActiveModels(): Promise<ActiveModels> {
  return apiFetch<ActiveModels>('/models/active')
}

export async function setActiveModel(role: 'chat' | 'curator' | 'embeddings', modelId: string): Promise<void> {
  await apiFetch('/models/active', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role, model_id: modelId }),
  })
}

export async function runCommand(command: string): Promise<unknown> {
  return apiFetch('/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command }),
  })
}
