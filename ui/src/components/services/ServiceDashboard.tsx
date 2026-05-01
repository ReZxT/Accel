import { useEffect } from 'react'
import { useServiceStore } from '../../stores/serviceStore'
import { isElectron } from '../../api/electron'
import ServiceGroupCard from './ServiceGroupCard'
import type { ServiceGroupId } from '../../types'

const GROUP_ORDER: ServiceGroupId[] = ['inference', 'core', 'memory', 'monitoring', 'media', 'dev']

export default function ServiceDashboard() {
  const init = useServiceStore((s) => s.init)
  const statuses = useServiceStore((s) => s.statuses)

  useEffect(() => { init() }, [init])

  if (!isElectron()) {
    return (
      <div className="flex-1 flex items-center justify-center text-text-tertiary">
        <p className="text-sm">Service management is only available in the desktop app.</p>
      </div>
    )
  }

  const grouped = new Map<ServiceGroupId, typeof statuses>()
  for (const s of statuses) {
    const list = grouped.get(s.group) || []
    list.push(s)
    grouped.set(s.group, list)
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <h1 className="text-lg font-semibold mb-4">Services</h1>
      <div className="space-y-3 max-w-2xl">
        {GROUP_ORDER.map((group) => {
          const services = grouped.get(group)
          if (!services || services.length === 0) return null
          return <ServiceGroupCard key={group} group={group} services={services} />
        })}
      </div>
    </div>
  )
}
