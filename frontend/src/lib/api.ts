const TOKEN_KEY = 'cabinet_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(path, { ...init, headers })
  if (response.status === 401) {
    setToken(null)
    if (!path.includes('/auth/login')) window.location.assign('/login')
  }
  if (!response.ok) {
    let detail = 'Не получилось выполнить запрос'
    try {
      const body = await response.json()
      detail = body.detail || detail
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return response.json() as Promise<T>
}

export type Company = {
  id: string
  legal_form: string
  inn: string
  ogrn: string
  name: string
  short_name: string
  okved: string
  okved_name: string
  registered_at: string
  status: string
  director_name: string
  account_blocked: boolean
  turnovers: number[]
  avg_turnover: number
  kassa_limit: number
  kassa_ceiling: number
  issued_kassa: number
  business_age_months: number
}

export type Me = {
  id: string
  login: string
  full_name: string
  role: 'client' | 'specialist'
  company: Company | null
}

export type EventItem = {
  id: string
  at: string
  actor: string
  action: string
  status: string
  message: string
  detail: Record<string, unknown> | null
}

export type PipelineStep = {
  code: string
  title: string
  ms: number
  status: string
  detail: string
}

export type ScheduleRow = {
  month: number
  payment: number
  principal: number
  interest: number
  remaining: number
}

export type Application = {
  id: string
  public_number: string
  purpose: string
  product: string
  requested_amount: number
  requested_term_months: number
  purpose_details: string | null
  status: string
  status_label: string
  client_message: string | null
  offer_amount: number | null
  offer_term_months: number | null
  offer_rate: number | null
  monthly_payment: number | null
  extra_fields: string[]
  extra_comment: string | null
  decided_by: string | null
  profile_changed: boolean
  extra_turnover: number
  collateral_msp: boolean
  created_at: string
  updated_at: string
  company: Company | null
  events: EventItem[]
  scoring: {
    total: number
    max_total: number
    band: string
    factors: { code: string; title: string; points: number; max_points: number; comment: string }[]
  } | null
  policy: Record<string, unknown> | null
  enrichment: Record<string, unknown> | null
  pipeline: PipelineStep[]
  available_actions: string[]
  dscr: number | null
  risk_memo: string | null
  schedule: ScheduleRow[]
}

export type Recommend = {
  purpose: string
  purpose_title: string
  purpose_subtitle: string
  why: string
  product: string
  product_name: string
  product_tagline: string
  suggested_amount: number
  suggested_term_months: number
  min_amount: number
  max_amount: number
  min_term_months: number
  max_term_months: number
  kassa_limit: number | null
  monthly_payment: number | null
  indicative_rate: number | null
}

export const api = {
  login: (login: string, password: string) =>
    request<{ access_token: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ login, password }),
    }),
  demoAccounts: () => request<{ login: string; password: string; hint: string }[]>('/api/auth/demo-accounts'),
  me: () => request<Me>('/api/me'),
  recommend: (purpose: string, amount?: number, term_months?: number) =>
    request<Recommend>('/api/recommend', {
      method: 'POST',
      body: JSON.stringify({ purpose, amount, term_months }),
    }),
  applications: () => request<Application[]>('/api/applications'),
  createApplication: (payload: object) =>
    request<Application>('/api/applications', { method: 'POST', body: JSON.stringify(payload) }),
  application: (id: string) => request<Application>(`/api/applications/${id}`),
  extra: (id: string, payload: object) =>
    request<Application>(`/api/applications/${id}/extra`, { method: 'POST', body: JSON.stringify(payload) }),
  accept: (id: string) => request<Application>(`/api/applications/${id}/accept`, { method: 'POST' }),
  decline: (id: string) => request<Application>(`/api/applications/${id}/decline`, { method: 'POST' }),
  sign: (id: string, code: string) =>
    request<Application>(`/api/applications/${id}/sign`, { method: 'POST', body: JSON.stringify({ code }) }),
  cure: (id: string) => request<Application>(`/api/applications/${id}/cure`, { method: 'POST' }),
  whatIf: (id: string, action: string) =>
    request<Application>(`/api/applications/${id}/what-if`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    }),
  chaos: () => request<{ bki_down: boolean }>('/api/demo/chaos'),
  setChaos: (bki_down: boolean) =>
    request<{ bki_down: boolean }>('/api/demo/chaos', {
      method: 'POST',
      body: JSON.stringify({ bki_down }),
    }),
  specialistQueue: (onlyPending = true) =>
    request<Application[]>(`/api/specialist/applications?only_pending=${onlyPending}`),
  specialistDossier: (id: string) => request<Application>(`/api/specialist/applications/${id}`),
  specialistDecide: (id: string, payload: object) =>
    request<Application>(`/api/specialist/applications/${id}/decision`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
}
