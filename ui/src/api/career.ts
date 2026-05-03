import { apiFetch } from './client'

export interface CareerOffer {
  id: number
  title: string
  company: string
  url: string
  description: string
  requirements: string
  salary: string
  location: string
  remote: string
  rating: number
  tier: string
  notes: string
  status: string
  date_added: string
  date_updated: string
}

export interface CareerProfile {
  skills?: string
  experience?: string
  education?: string
  target_roles?: string
  preferred_stack?: string
  location_preference?: string
  salary_expectation?: string
  languages?: string
  strengths?: string
  notes?: string
  updated_at?: string
}

export async function getCareerProfile(): Promise<CareerProfile> {
  return apiFetch('/career/profile')
}

export async function getCareerOffers(): Promise<CareerOffer[]> {
  const data = await apiFetch<{ offers: CareerOffer[] }>('/career/offers')
  return data.offers
}

export async function getCareerTierlist(): Promise<Record<string, CareerOffer[]>> {
  const data = await apiFetch<{ tiers: Record<string, CareerOffer[]> }>('/career/tierlist')
  return data.tiers
}

export interface FetchJobsParams {
  keywords?: string
  seniority?: string
  category?: string
  location?: string
  salary_min?: number
  limit?: number
}

export async function fetchCareerJobs(params: FetchJobsParams): Promise<{ message: string; offers: CareerOffer[] }> {
  const query = new URLSearchParams()
  if (params.keywords) query.set('keywords', params.keywords)
  if (params.seniority) query.set('seniority', params.seniority)
  if (params.category) query.set('category', params.category)
  if (params.location) query.set('location', params.location)
  if (params.salary_min) query.set('salary_min', String(params.salary_min))
  if (params.limit) query.set('limit', String(params.limit))
  return apiFetch<{ message: string; offers: CareerOffer[] }>(`/career/fetch?${query.toString()}`, { method: 'POST', timeout: 90000 })
}
