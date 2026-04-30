const BASE = ''

export async function apiFetch<T>(
  path: string,
  init?: RequestInit & { timeout?: number },
): Promise<T> {
  const { timeout = 8000, ...fetchInit } = init ?? {}
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), timeout)

  const res = await fetch(`${BASE}${path}`, {
    ...fetchInit,
    signal: controller.signal,
  })

  clearTimeout(id)

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${res.status}: ${text.slice(0, 300)}`)
  }

  return res.json()
}
