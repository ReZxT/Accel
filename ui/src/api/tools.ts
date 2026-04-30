import { apiFetch } from './client'
import type { ToolPolicy } from '../types'

interface ToolSettingsResponse {
  tool_settings: Record<string, ToolPolicy>
}

export async function getToolSettings(): Promise<Record<string, ToolPolicy>> {
  const data = await apiFetch<ToolSettingsResponse>('/settings/tools', {
    timeout: 5000,
  })
  return data.tool_settings ?? {}
}

export async function updateToolSettings(
  settings: Record<string, ToolPolicy>,
): Promise<void> {
  await apiFetch('/settings/tools', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tool_settings: settings }),
  })
}

export async function resolveApproval(
  requestId: string,
  approved: boolean,
): Promise<void> {
  await apiFetch(`/approve/${requestId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approved }),
  })
}
