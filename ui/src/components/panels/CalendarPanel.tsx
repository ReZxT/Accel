import { useEffect, useState, useMemo } from 'react'

interface CalEvent {
  id: number
  title: string
  date: string
  time: string | null
  description: string | null
  all_day: boolean
  recurring: string
}

interface Holiday {
  date: string
  title: string
}

function Clock() {
  const [now, setNow] = useState(new Date())

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const time = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  const date = now.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })

  return (
    <div className="text-center py-4 border-b border-border">
      <div className="text-3xl font-mono font-bold text-text-primary tracking-wider">{time}</div>
      <div className="text-sm text-text-tertiary mt-1">{date}</div>
    </div>
  )
}

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function daysInMonth(year: number, month: number) {
  return new Date(year, month + 1, 0).getDate()
}

function startDayOfWeek(year: number, month: number) {
  const d = new Date(year, month, 1).getDay()
  return d === 0 ? 6 : d - 1
}

export default function CalendarPanel() {
  const today = new Date()
  const [viewYear, setViewYear] = useState(today.getFullYear())
  const [viewMonth, setViewMonth] = useState(today.getMonth())
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [events, setEvents] = useState<CalEvent[]>([])
  const [holidays, setHolidays] = useState<Holiday[]>([])

  const totalDays = daysInMonth(viewYear, viewMonth)
  const offset = startDayOfWeek(viewYear, viewMonth)

  useEffect(() => {
    const start = `${viewYear}-${String(viewMonth + 1).padStart(2, '0')}-01`
    const end = `${viewYear}-${String(viewMonth + 1).padStart(2, '0')}-${String(totalDays).padStart(2, '0')}`
    fetch(`/calendar/events?start=${start}&end=${end}`)
      .then((r) => r.json())
      .then((data) => {
        setEvents(data.events ?? [])
        setHolidays(data.holidays ?? [])
      })
      .catch(() => {})
  }, [viewYear, viewMonth, totalDays])

  const eventsByDate = useMemo(() => {
    const map = new Map<string, CalEvent[]>()
    for (const ev of events) {
      const list = map.get(ev.date) || []
      list.push(ev)
      map.set(ev.date, list)
    }
    return map
  }, [events])

  const holidaysByDate = useMemo(() => {
    const map = new Map<string, string>()
    for (const h of holidays) map.set(h.date, h.title)
    return map
  }, [holidays])

  const prevMonth = () => {
    if (viewMonth === 0) { setViewYear(viewYear - 1); setViewMonth(11) }
    else setViewMonth(viewMonth - 1)
  }
  const nextMonth = () => {
    if (viewMonth === 11) { setViewYear(viewYear + 1); setViewMonth(0) }
    else setViewMonth(viewMonth + 1)
  }
  const goToday = () => {
    setViewYear(today.getFullYear())
    setViewMonth(today.getMonth())
    setSelectedDate(null)
  }

  const monthLabel = new Date(viewYear, viewMonth).toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`

  const cells: (number | null)[] = []
  for (let i = 0; i < offset; i++) cells.push(null)
  for (let d = 1; d <= totalDays; d++) cells.push(d)

  const selectedEvents = selectedDate ? eventsByDate.get(selectedDate) ?? [] : []
  const selectedHoliday = selectedDate ? holidaysByDate.get(selectedDate) : null

  const todayEvents = eventsByDate.get(todayStr) ?? []

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <Clock />

      {(holidays.length > 0 || todayEvents.length > 0) && (
        <div className="px-3 pt-3 space-y-1.5">
          {holidays.map((h) => (
            <div key={h.date} className={`flex items-center gap-2 px-2 py-1.5 rounded text-xs ${h.date === todayStr ? 'bg-red-500/15 text-red-300' : 'bg-red-500/8 text-red-400/70'}`}>
              <span className="flex-shrink-0">PL</span>
              <span className="flex-1">{h.title}</span>
              <span className="text-text-tertiary font-mono">{h.date.slice(5)}</span>
            </div>
          ))}
          {todayEvents.map((ev) => (
            <div key={ev.id} className="flex items-center gap-2 px-2 py-1.5 rounded bg-accent/10 text-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-accent flex-shrink-0" />
              <span className="flex-1 text-text-primary">{ev.title}</span>
              {ev.time && <span className="text-text-tertiary">{ev.time}</span>}
            </div>
          ))}
        </div>
      )}

      <div className="p-3">
        <div className="flex items-center justify-between mb-3">
          <button onClick={prevMonth} className="text-text-tertiary hover:text-text-primary px-2 py-1 text-sm cursor-pointer">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6" /></svg>
          </button>
          <button onClick={goToday} className="text-sm font-semibold text-text-primary hover:text-accent cursor-pointer">
            {monthLabel}
          </button>
          <button onClick={nextMonth} className="text-text-tertiary hover:text-text-primary px-2 py-1 text-sm cursor-pointer">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="9 18 15 12 9 6" /></svg>
          </button>
        </div>

        <div className="grid grid-cols-7 gap-px text-center text-[11px] text-text-tertiary mb-1">
          {WEEKDAYS.map((d) => <div key={d} className="py-1">{d}</div>)}
        </div>

        <div className="grid grid-cols-7 gap-px">
          {cells.map((day, i) => {
            if (day === null) return <div key={`e-${i}`} />
            const dateStr = `${viewYear}-${String(viewMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
            const isToday = dateStr === todayStr
            const isSelected = dateStr === selectedDate
            const hasEvents = eventsByDate.has(dateStr)
            const isHoliday = holidaysByDate.has(dateStr)
            const dayOfWeek = new Date(viewYear, viewMonth, day).getDay()
            const isWeekend = dayOfWeek === 0 || dayOfWeek === 6

            return (
              <button
                key={dateStr}
                onClick={() => setSelectedDate(isSelected ? null : dateStr)}
                className={`relative flex flex-col items-center justify-center h-9 rounded text-xs cursor-pointer transition-colors
                  ${isSelected ? 'bg-accent/20 text-accent' : ''}
                  ${isToday && !isSelected ? 'bg-accent/10 text-accent font-bold' : ''}
                  ${!isToday && !isSelected ? 'hover:bg-surface-hover' : ''}
                  ${isWeekend && !isToday && !isSelected ? 'text-text-tertiary' : ''}
                  ${isHoliday && !isSelected ? 'text-red-400' : ''}
                `}
              >
                {day}
                {(hasEvents || isHoliday) && (
                  <div className="flex gap-0.5 mt-0.5">
                    {hasEvents && <span className="w-1 h-1 rounded-full bg-accent" />}
                    {isHoliday && <span className="w-1 h-1 rounded-full bg-red-400" />}
                  </div>
                )}
              </button>
            )
          })}
        </div>
      </div>

      {selectedDate && (
        <div className="border-t border-border p-3 flex-1">
          <div className="text-xs text-text-tertiary mb-2">
            {new Date(selectedDate + 'T00:00:00').toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })}
          </div>
          {selectedHoliday && (
            <div className="flex items-center gap-2 mb-2 px-2 py-1.5 rounded bg-red-500/10 text-red-400 text-xs">
              <span>PL</span>
              <span>{selectedHoliday}</span>
            </div>
          )}
          {selectedEvents.length > 0 ? (
            <div className="space-y-1.5">
              {selectedEvents.map((ev) => (
                <div key={`${ev.id}-${ev.date}`} className="px-2 py-1.5 rounded bg-accent/10 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-text-primary">{ev.title}</span>
                    {ev.time && <span className="text-text-tertiary">{ev.time}</span>}
                    {ev.recurring !== 'none' && (
                      <span className="text-[10px] px-1 py-0.5 rounded bg-accent/20 text-accent">{ev.recurring}</span>
                    )}
                  </div>
                  {ev.description && <div className="text-text-tertiary mt-0.5">{ev.description}</div>}
                </div>
              ))}
            </div>
          ) : !selectedHoliday ? (
            <div className="text-xs text-text-tertiary">No events</div>
          ) : null}
        </div>
      )}
    </div>
  )
}
