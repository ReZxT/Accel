import { useEffect, useState, useRef } from 'react'
import { getCareerProfile, getCareerOffers, fetchCareerJobs } from '../../api/career'
import type { CareerProfile, CareerOffer, FetchJobsParams } from '../../api/career'

const TIER_COLORS: Record<string, string> = {
  S: 'text-yellow-400 bg-yellow-400/15',
  A: 'text-green-400 bg-green-400/15',
  B: 'text-blue-400 bg-blue-400/15',
  C: 'text-orange-400 bg-orange-400/15',
  D: 'text-red-400 bg-red-400/15',
  '?': 'text-text-tertiary bg-white/5',
}

const STATUS_COLORS: Record<string, string> = {
  new: 'text-text-tertiary',
  applied: 'text-blue-400',
  interview: 'text-yellow-400',
  rejected: 'text-red-400',
  accepted: 'text-green-400',
}

type View = 'overview' | 'tierlist' | 'offers' | 'fetch'

export default function CareerPanel() {
  const [view, setView] = useState<View>('overview')
  const [profile, setProfile] = useState<CareerProfile | null>(null)
  const [offers, setOffers] = useState<CareerOffer[]>([])
  const [loading, setLoading] = useState(true)
  const [fetching, setFetching] = useState(false)
  const [fetchMsg, setFetchMsg] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const [p, o] = await Promise.all([getCareerProfile(), getCareerOffers()])
      setProfile(p)
      setOffers(o)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const rated = offers.filter((o) => o.rating >= 0)
  const tiers: Record<string, CareerOffer[]> = { S: [], A: [], B: [], C: [], D: [] }
  for (const o of rated) {
    if (tiers[o.tier]) tiers[o.tier].push(o)
  }

  if (loading) return <div className="text-center text-xs text-text-tertiary py-8">Loading...</div>

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center border-b border-border px-2 py-1.5 gap-1 flex-shrink-0">
        <NavBtn active={view === 'overview'} onClick={() => setView('overview')} label="Overview" />
        <NavBtn active={view === 'tierlist'} onClick={() => setView('tierlist')} label="Tier List" />
        <NavBtn active={view === 'offers'} onClick={() => setView('offers')} label="All Offers" />
        <NavBtn active={view === 'fetch'} onClick={() => setView('fetch')} label="Fetch" />
        <div className="flex-1" />
        <button onClick={load} className="text-xs text-text-tertiary hover:text-text-primary transition-colors cursor-pointer px-1">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M23 4v6h-6" /><path d="M1 20v-6h6" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></svg>
        </button>
      </div>

      {view === 'overview' && (
        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          {/* Profile summary */}
          <Section title="Profile">
            {profile && Object.keys(profile).length > 0 ? (
              <div className="space-y-1.5">
                {profile.target_roles && <Field label="Target" value={profile.target_roles} />}
                {profile.skills && <Field label="Skills" value={profile.skills} />}
                {profile.preferred_stack && <Field label="Stack" value={profile.preferred_stack} />}
                {profile.experience && <Field label="Experience" value={profile.experience} />}
                {profile.location_preference && <Field label="Location" value={profile.location_preference} />}
                {profile.salary_expectation && <Field label="Salary" value={profile.salary_expectation} />}
                {profile.languages && <Field label="Languages" value={profile.languages} />}
              </div>
            ) : (
              <div className="text-xs text-text-tertiary">No profile yet. Ask the model to set one up.</div>
            )}
          </Section>

          {/* Stats */}
          <Section title="Stats">
            <div className="grid grid-cols-3 gap-2">
              <Stat label="Total" value={offers.length} />
              <Stat label="Rated" value={rated.length} />
              <Stat label="Applied" value={offers.filter((o) => o.status === 'applied').length} />
            </div>
            {rated.length > 0 && (
              <div className="flex gap-1.5 mt-2">
                {(['S', 'A', 'B', 'C', 'D'] as const).map((t) => (
                  <span key={t} className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${TIER_COLORS[t]}`}>
                    {t}: {tiers[t].length}
                  </span>
                ))}
              </div>
            )}
          </Section>

          {/* Recent offers */}
          {offers.length > 0 && (
            <Section title="Recent">
              {offers.slice(0, 5).map((o) => (
                <OfferRow key={o.id} offer={o} />
              ))}
            </Section>
          )}
        </div>
      )}

      {view === 'tierlist' && (
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {rated.length === 0 ? (
            <div className="text-xs text-text-tertiary text-center py-4">No rated offers yet.</div>
          ) : (
            (['S', 'A', 'B', 'C', 'D'] as const).map((t) =>
              tiers[t].length > 0 ? (
                <div key={t}>
                  <div className={`text-xs font-bold px-2 py-1 rounded-t ${TIER_COLORS[t]}`}>
                    Tier {t} ({t === 'S' ? '90-100' : t === 'A' ? '75-89' : t === 'B' ? '60-74' : t === 'C' ? '40-59' : '0-39'})
                  </div>
                  <div className="border border-border border-t-0 rounded-b divide-y divide-border">
                    {tiers[t].map((o) => (
                      <OfferRow key={o.id} offer={o} />
                    ))}
                  </div>
                </div>
              ) : null,
            )
          )}
          {offers.filter((o) => o.rating < 0).length > 0 && (
            <div>
              <div className="text-xs font-bold px-2 py-1 rounded-t text-text-tertiary bg-white/5">
                Unrated ({offers.filter((o) => o.rating < 0).length})
              </div>
              <div className="border border-border border-t-0 rounded-b divide-y divide-border">
                {offers.filter((o) => o.rating < 0).map((o) => (
                  <OfferRow key={o.id} offer={o} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {view === 'offers' && (
        <div className="flex-1 overflow-y-auto divide-y divide-border">
          {offers.length === 0 ? (
            <div className="text-xs text-text-tertiary text-center py-4">No offers saved yet.</div>
          ) : (
            offers.map((o) => <OfferRow key={o.id} offer={o} expanded />)
          )}
        </div>
      )}

      {view === 'fetch' && (
        <FetchView
          fetching={fetching}
          fetchMsg={fetchMsg}
          onFetch={async (params) => {
            setFetching(true)
            setFetchMsg('')
            try {
              const result = await fetchCareerJobs(params)
              setFetchMsg(result.message)
              setOffers(result.offers)
            } catch (e) {
              setFetchMsg(`Error: ${e}`)
            }
            setFetching(false)
          }}
        />
      )}
    </div>
  )
}

function NavBtn({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`text-xs px-2 py-1 rounded transition-colors cursor-pointer ${active ? 'bg-accent/15 text-accent' : 'text-text-tertiary hover:text-text-primary'}`}
    >
      {label}
    </button>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[10px] text-text-tertiary font-medium uppercase tracking-wider mb-1.5">{title}</div>
      {children}
    </div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-xs">
      <span className="text-text-tertiary">{label}: </span>
      <span className="text-text-secondary">{value}</span>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-surface-hover rounded px-2 py-1.5 text-center">
      <div className="text-sm font-medium text-text-primary">{value}</div>
      <div className="text-[10px] text-text-tertiary">{label}</div>
    </div>
  )
}

function FetchView({
  fetching,
  fetchMsg,
  onFetch,
}: {
  fetching: boolean
  fetchMsg: string
  onFetch: (params: FetchJobsParams) => void
}) {
  const kwRef = useRef<HTMLInputElement>(null)
  const senRef = useRef<HTMLSelectElement>(null)
  const catRef = useRef<HTMLSelectElement>(null)
  const locRef = useRef<HTMLInputElement>(null)

  const handleSubmit = () => {
    onFetch({
      keywords: kwRef.current?.value || '',
      seniority: senRef.current?.value || '',
      category: catRef.current?.value || '',
      location: locRef.current?.value || '',
      limit: 30,
    })
  }

  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-3">
      <Section title="Fetch from nofluffjobs.com">
        <div className="space-y-2">
          <input
            ref={kwRef}
            placeholder="Keywords (e.g. python, react, AI)"
            className="w-full bg-surface-hover border border-border rounded px-2 py-1.5 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent"
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          />
          <div className="grid grid-cols-2 gap-2">
            <select
              ref={senRef}
              className="bg-surface-hover border border-border rounded px-2 py-1.5 text-xs text-text-primary focus:outline-none focus:border-accent"
            >
              <option value="">Any seniority</option>
              <option value="junior">Junior</option>
              <option value="mid">Mid</option>
              <option value="senior">Senior</option>
            </select>
            <select
              ref={catRef}
              className="bg-surface-hover border border-border rounded px-2 py-1.5 text-xs text-text-primary focus:outline-none focus:border-accent"
            >
              <option value="">Any category</option>
              <option value="backend">Backend</option>
              <option value="frontend">Frontend</option>
              <option value="fullstack">Fullstack</option>
              <option value="data">Data</option>
              <option value="devops">DevOps</option>
              <option value="testing">Testing</option>
              <option value="mobile">Mobile</option>
              <option value="pm">PM</option>
            </select>
          </div>
          <input
            ref={locRef}
            placeholder="City (e.g. Warszawa)"
            className="w-full bg-surface-hover border border-border rounded px-2 py-1.5 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent"
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          />
          <button
            onClick={handleSubmit}
            disabled={fetching}
            className="w-full bg-accent/15 text-accent text-xs font-medium py-2 rounded hover:bg-accent/25 transition-colors cursor-pointer disabled:opacity-50"
          >
            {fetching ? 'Fetching...' : 'Fetch & Save New Offers'}
          </button>
        </div>
      </Section>

      {fetchMsg && (
        <Section title="Results">
          <pre className="text-[10px] text-text-secondary whitespace-pre-wrap leading-relaxed max-h-[400px] overflow-y-auto">
            {fetchMsg}
          </pre>
        </Section>
      )}
    </div>
  )
}

function OfferRow({ offer, expanded }: { offer: CareerOffer; expanded?: boolean }) {
  const tc = TIER_COLORS[offer.tier] || TIER_COLORS['?']
  const sc = STATUS_COLORS[offer.status] || STATUS_COLORS.new
  return (
    <div className="px-3 py-2">
      <div className="flex items-center gap-2">
        <span className={`text-[10px] font-bold w-5 h-5 rounded flex items-center justify-center flex-shrink-0 ${tc}`}>
          {offer.tier}
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-xs font-medium text-text-primary truncate">{offer.title}</div>
          <div className="text-[10px] text-text-tertiary truncate">{offer.company}</div>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {offer.rating >= 0 && <span className="text-[10px] text-text-secondary">{offer.rating}</span>}
          <span className={`text-[10px] ${sc}`}>{offer.status}</span>
        </div>
      </div>
      {expanded && (
        <div className="mt-1 ml-7 space-y-0.5">
          {offer.salary && <div className="text-[10px] text-text-tertiary">Salary: {offer.salary}</div>}
          {offer.location && (
            <div className="text-[10px] text-text-tertiary">
              {offer.location}{offer.remote ? ` (${offer.remote})` : ''}
            </div>
          )}
          {offer.notes && <div className="text-[10px] text-text-secondary italic">{offer.notes}</div>}
          {offer.url && (
            <a href={offer.url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-accent hover:underline truncate block">
              {offer.url}
            </a>
          )}
        </div>
      )}
    </div>
  )
}
