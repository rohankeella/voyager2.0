/**
 * Thin typed client over the FastAPI backend. Keeps the JWT in localStorage
 * (browser only) and attaches it automatically. Throws `ApiError` on any
 * non-2xx response so callers can `try/catch` uniformly.
 */

function resolveApiBase(): string {
  const explicit = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (explicit) return explicit.replace(/\/+$/, "");
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return "http://localhost:8000";
}

export const API_BASE = resolveApiBase();

const TOKEN_KEY = "voyager_auth_token";
const USER_KEY = "voyager_auth_user";

export class ApiError extends Error {
  status: number;
  data: unknown;
  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

export type ApiUser = {
  id: string;
  email: string;
  full_name: string;
  country: string | null;
  phone: string | null;
  role: "traveler" | "provider" | "admin";
  preferences: Record<string, unknown> | null;
  created_at: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  user: ApiUser;
};

// ---- token/user storage (browser-only, safe in SSR) ------------------------

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setSession(res: LoginResponse) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, res.access_token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(res.user));
}

export function clearSession() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

export function getStoredUser(): ApiUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as ApiUser;
  } catch {
    return null;
  }
}

// ---- fetch wrapper ---------------------------------------------------------

type RequestOpts = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  auth?: boolean;   // attach Bearer token — defaults true when a token exists
  signal?: AbortSignal;
};

async function request<T>(path: string, opts: RequestOpts = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token && opts.auth !== false) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
    signal: opts.signal,
  });

  if (res.status === 204) return undefined as T;

  let data: unknown = null;
  const text = await res.text();
  if (text) {
    try { data = JSON.parse(text); } catch { data = text; }
  }

  if (!res.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : res.statusText;
    throw new ApiError(res.status, detail || `HTTP ${res.status}`, data);
  }
  return data as T;
}

// ---- auth ------------------------------------------------------------------

export const authApi = {
  register: (payload: {
    email: string;
    password: string;
    full_name: string;
    country?: string;
    phone?: string;
  }) => request<LoginResponse>("/api/auth/register", { method: "POST", body: payload, auth: false }),

  login: (payload: { email: string; password: string }) =>
    request<LoginResponse>("/api/auth/login", { method: "POST", body: payload, auth: false }),

  me: () => request<ApiUser>("/api/auth/me"),

  updatePreferences: (preferences: Record<string, unknown>) =>
    request<ApiUser>("/api/auth/me/preferences", { method: "PUT", body: { preferences } }),
};

// ---- experiences / recommendations ----------------------------------------

export type ApiOperatingHour = { id: string; day_of_week: number; open_time: string; close_time: string };

export type ApiExperience = {
  id: string;
  slug: string;
  provider_id: string | null;
  title: string;
  description: string | null;
  category: "FOOD" | "WORKSHOP" | "FESTIVAL" | "OUTDOOR" | "NIGHTLIFE" | "CULTURE";
  base_cost: number;
  currency: string;
  duration_mins: number;
  lat: number;
  lng: number;
  city: string;
  country: string | null;
  address: string | null;
  capacity_max: number;
  seats_available: number;
  attributes: Record<string, unknown>;
  interest_tags: string[];
  is_active: boolean;
  hours: ApiOperatingHour[];
  created_at: string;
  updated_at: string;
};

export type ApiScored = {
  experience: ApiExperience;
  score: number;
  breakdown: {
    interest: number;
    logistics: number;
    budget: number;
    fit: number;
    weights: Record<string, number>;
  };
  transit_mins: number;
  distance_km: number;
  reasons: string[];
};

export type MatchRequest = {
  lat: number;
  lng: number;
  at: string;                // ISO datetime
  window_end: string;
  interests?: string[];
  priorities?: string[];
  budget_max?: number | null;
  group_type?: string | null;
  accessibility_flags?: string[];
  travel_mode?: "walking" | "driving" | "transit";
  limit?: number;
  city?: string | null;
};

export type MatchResponse = {
  query_window_mins: number;
  candidates_scanned: number;
  results: ApiScored[];
};

export const recommendationsApi = {
  match: (query: MatchRequest) =>
    request<MatchResponse>("/api/recommendations/match", { method: "POST", body: query, auth: false }),

  matchForMe: (query: MatchRequest) =>
    request<MatchResponse>("/api/recommendations/for-me", { method: "POST", body: query }),

  gapFill: (query: {
    itinerary_id: string;
    interests?: string[];
    priorities?: string[];
    budget_max?: number | null;
    group_type?: string | null;
    accessibility_flags?: string[];
    travel_mode?: "walking" | "driving" | "transit";
    min_gap_mins?: number;
    per_gap_limit?: number;
  }) => request("/api/recommendations/gap-fill", { method: "POST", body: query }),
};

export const experiencesApi = {
  list: (params: { city?: string; category?: string; q?: string; limit?: number; offset?: number } = {}) => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) if (v !== undefined) qs.set(k, String(v));
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<ApiExperience[]>(`/api/experiences${suffix}`, { auth: false });
  },
  get: (id: string) => request<ApiExperience>(`/api/experiences/${id}`, { auth: false }),
};

// ---- P2 · Groups + ledger --------------------------------------------------

export type SplitStrategy =
  | "EQUAL"
  | "EXACT_AMOUNT"
  | "PERCENTAGE"
  | "SHARE_WEIGHTED"
  | "ORGANIZER_COVERED";

export type GroupMemberRole = "organizer" | "participant";

export type ApiGroupMember = {
  id: string;
  display_name: string;
  email: string | null;
  role: GroupMemberRole;
  user_id: string | null;
  created_at: string;
};

export type ApiGroup = {
  id: string;
  name: string;
  trip_destination: string | null;
  base_currency: string;
  itinerary_id: string | null;
  created_by: string;
  created_at: string;
  members: ApiGroupMember[];
};

export type ApiExpenseParticipant = {
  id: string;
  member_id: string;
  share_value: number | null;
  computed_amount_base: number;
};

export type ApiExpense = {
  id: string;
  group_id: string;
  title: string;
  description: string | null;
  category: string | null;
  amount: number;
  currency: string;
  fx_rate_to_base: number;
  payer_member_id: string;
  split_strategy: SplitStrategy;
  incurred_at: string;
  created_at: string;
  participants: ApiExpenseParticipant[];
};

export type ApiReimbursement = {
  id: string;
  group_id: string;
  from_member_id: string;
  to_member_id: string;
  amount_base: number;
  note: string | null;
  settled_at: string;
};

export type ApiMemberBalance = {
  member_id: string;
  display_name: string;
  paid_to_vendors: number;
  owed_from_participation: number;
  reimbursements_sent: number;
  reimbursements_received: number;
  // Layer-2 rollup: paid_to_vendors + reimbursements_sent
  total_paid_out: number;
  net_balance: number;
};

export type ApiSettlementTransfer = {
  from_member_id: string;
  from_display_name: string;
  to_member_id: string;
  to_display_name: string;
  amount_base: number;
};

export type ApiOrganizerLedger = {
  group_id: string;
  base_currency: string;
  total_spend_base: number;
  total_reimbursed_base: number;
  balances: ApiMemberBalance[];
  settlements: ApiSettlementTransfer[];
  expenses: ApiExpense[];
  reimbursements: ApiReimbursement[];
};

export type ApiParticipantLedger = {
  group_id: string;
  base_currency: string;
  me_member_id: string;
  my_balance: ApiMemberBalance;
  action_items: {
    counterpart_member_id: string;
    counterpart_display_name: string;
    amount_base: number;
    direction: "owe" | "receive";
  }[];
  my_expenses: {
    expense_id: string;
    title: string;
    amount: number;
    currency: string;
    my_share_base: number;
    paid_by_me: boolean;
    incurred_at: string;
  }[];
};

export const groupsApi = {
  list: () => request<ApiGroup[]>("/api/groups"),
  get: (id: string) => request<ApiGroup>(`/api/groups/${id}`),
  create: (payload: {
    name: string;
    trip_destination?: string;
    base_currency?: string;
    itinerary_id?: string;
    members?: Array<{
      display_name: string;
      email?: string;
      user_id?: string;
      role?: GroupMemberRole;
    }>;
  }) => request<ApiGroup>("/api/groups", { method: "POST", body: payload }),
  update: (id: string, payload: Partial<{ name: string; trip_destination: string; base_currency: string; itinerary_id: string }>) =>
    request<ApiGroup>(`/api/groups/${id}`, { method: "PATCH", body: payload }),
  remove: (id: string) => request<void>(`/api/groups/${id}`, { method: "DELETE" }),

  addMember: (id: string, payload: { display_name: string; email?: string; user_id?: string; role?: GroupMemberRole }) =>
    request<ApiGroupMember>(`/api/groups/${id}/members`, { method: "POST", body: payload }),
  removeMember: (id: string, memberId: string) =>
    request<void>(`/api/groups/${id}/members/${memberId}`, { method: "DELETE" }),
};

export type ExpenseCreatePayload = {
  title: string;
  description?: string;
  category?: string;
  amount: number;
  currency?: string;
  fx_rate_to_base?: number;
  payer_member_id: string;
  split_strategy: SplitStrategy;
  participants: Array<{ member_id: string; share_value?: number }>;
  incurred_at?: string;
};

export const ledgerApi = {
  listExpenses: (groupId: string) => request<ApiExpense[]>(`/api/groups/${groupId}/expenses`),
  createExpense: (groupId: string, payload: ExpenseCreatePayload) =>
    request<ApiExpense>(`/api/groups/${groupId}/expenses`, { method: "POST", body: payload }),
  updateExpense: (groupId: string, expenseId: string, payload: Partial<ExpenseCreatePayload>) =>
    request<ApiExpense>(`/api/groups/${groupId}/expenses/${expenseId}`, { method: "PATCH", body: payload }),
  deleteExpense: (groupId: string, expenseId: string) =>
    request<void>(`/api/groups/${groupId}/expenses/${expenseId}`, { method: "DELETE" }),

  listReimbursements: (groupId: string) => request<ApiReimbursement[]>(`/api/groups/${groupId}/reimbursements`),
  createReimbursement: (groupId: string, payload: {
    from_member_id: string;
    to_member_id: string;
    amount_base: number;
    note?: string;
    settled_at?: string;
  }) => request<ApiReimbursement>(`/api/groups/${groupId}/reimbursements`, { method: "POST", body: payload }),
  deleteReimbursement: (groupId: string, reimbursementId: string) =>
    request<void>(`/api/groups/${groupId}/reimbursements/${reimbursementId}`, { method: "DELETE" }),

  organizerView: (groupId: string) => request<ApiOrganizerLedger>(`/api/groups/${groupId}/ledger`),
  participantView: (groupId: string) => request<ApiParticipantLedger>(`/api/groups/${groupId}/ledger/me`),
};

// ---- P3 · Capacity & Crowd Command Center ---------------------------------

export type CapacitySourceKind = "HOUSING" | "TRANSIT" | "VENUE";
export type NudgeKind = "DISCOUNT" | "BADGE" | "PRIORITY_PASS";
export type ZoneStatus = "STABLE" | "RISING" | "APPROACHING_SATURATION" | "SATURATED";

export type ApiZone = {
  id: string;
  city: string;
  name: string;
  center_lat: number;
  center_lng: number;
  radius_km: number;
  total_capacity: number;
  created_at: string;
};

export type ApiZoneDensity = {
  zone_id: string;
  zone_name: string;
  city: string;
  density_pct: number;
  occupancy_count: number;
  capacity_max: number;
  recorded_at: string | null;
  sources: Record<string, number>;
};

export type ApiSaturationForecast = {
  zone_id: string;
  zone_name: string;
  current_density_pct: number;
  projected_density_pct_60m: number;
  slope_pct_per_min: number;
  minutes_to_saturation: number | null;
  status: ZoneStatus;
  event_pressure_applied: boolean;
};

export type ApiNudge = {
  id: string;
  kind: NudgeKind;
  title: string;
  description: string | null;
  target_zone_id: string | null;
  payload: Record<string, unknown>;
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
};

export type ApiBalancerRecommendation = {
  from_zone_id: string;
  from_zone_name: string;
  from_density_pct: number;
  to_zone_id: string;
  to_zone_name: string;
  to_density_pct: number;
  distance_km: number;
  attached_nudge: ApiNudge | null;
};

export type ApiZoneEvent = {
  id: string;
  zone_id: string;
  name: string;
  start_at: string;
  end_at: string;
  expected_attendance: number;
  created_at: string;
};

export type ApiDepartureBand = {
  label: string;
  start_at: string;
  end_at: string;
  assigned_headcount: number;
};

export type ApiStaggeringPlan = {
  event_id: string;
  event_name: string;
  event_end_at: string;
  total_attendees: number;
  bands: ApiDepartureBand[];
};

export type ApiOperatorDashboard = {
  now: string;
  zone_densities: ApiZoneDensity[];
  forecasts: ApiSaturationForecast[];
  balancer_recommendations: ApiBalancerRecommendation[];
  active_events: ApiZoneEvent[];
};

export type ApiAttendeeCapacityView = {
  zone_id: string;
  zone_name: string;
  density_pct: number;
  status: ZoneStatus;
  forecast: ApiSaturationForecast;
  suggested_alternative: ApiBalancerRecommendation | null;
  tip: string;
};

export type CapacityMetricPayload = {
  zone_id: string;
  source_kind: CapacitySourceKind;
  source_label?: string;
  occupancy_count: number;
  capacity_max: number;
  recorded_at?: string;
};

export const capacityApi = {
  listZones: (params: { city?: string } = {}) => {
    const qs = params.city ? `?city=${encodeURIComponent(params.city)}` : "";
    return request<ApiZone[]>(`/api/zones${qs}`);
  },
  createZone: (payload: Omit<ApiZone, "id" | "created_at">) =>
    request<ApiZone>("/api/zones", { method: "POST", body: payload }),
  postMetric: (payload: CapacityMetricPayload) =>
    request("/api/capacity/metrics", { method: "POST", body: payload }),
  postMetricsBatch: (metrics: CapacityMetricPayload[]) =>
    request("/api/capacity/metrics/batch", { method: "POST", body: { metrics } }),

  densities: () => request<ApiZoneDensity[]>("/api/capacity/densities"),
  forecasts: () => request<ApiSaturationForecast[]>("/api/capacity/forecasts"),
  balancer: () => request<ApiBalancerRecommendation[]>("/api/capacity/balancer"),

  listNudges: (params: { active_only?: boolean } = {}) => {
    const qs = params.active_only === false ? "?active_only=false" : "";
    return request<ApiNudge[]>(`/api/nudges${qs}`);
  },
  createNudge: (payload: {
    kind: NudgeKind;
    title: string;
    description?: string;
    target_zone_id?: string;
    payload?: Record<string, unknown>;
    expires_at?: string;
  }) => request<ApiNudge>("/api/nudges", { method: "POST", body: payload }),

  listZoneEvents: (zoneId: string) => request<ApiZoneEvent[]>(`/api/zones/${zoneId}/events`),
  createZoneEvent: (zoneId: string, payload: Omit<ApiZoneEvent, "id" | "created_at" | "zone_id"> & { zone_id: string }) =>
    request<ApiZoneEvent>(`/api/zones/${zoneId}/events`, { method: "POST", body: payload }),

  stagger: (eventId: string, params: { max_per_band?: number; band_minutes?: number } = {}) =>
    request<ApiStaggeringPlan>(`/api/events/${eventId}/stagger`, {
      method: "POST",
      body: { event_id: eventId, ...params },
    }),

  operatorDashboard: () => request<ApiOperatorDashboard>("/api/operator/dashboard"),
  attendeeView: (zoneId: string) => request<ApiAttendeeCapacityView>(`/api/capacity/for-attendee?zone_id=${encodeURIComponent(zoneId)}`),
};

// ---- travel data (hotels, weather, flights, locations) --------------------

export type ApiLocationHit = {
  name: string;
  iata_code: string;
  sub_type: string;
  city_name: string | null;
  country_code: string | null;
  geo: { latitude: number; longitude: number } | null;
};

export type ApiHotelOffer = {
  hotel_id: string;
  hotel_name: string;
  available: boolean;
  offers: Array<{
    id: string;
    check_in_date: string;
    check_out_date: string;
    room_description: string | null;
    price: { currency: string; total: string; base: string | null };
  }>;
};

export type ApiHotelsResponse = {
  city_code: string;
  hotels: Array<{ hotel_id: string; name: string }>;
  offers: ApiHotelOffer[];
};

export type ApiFlightOffer = {
  id: string;
  currency: string;
  total: string;
  itineraries: Array<{
    duration: string;
    segments: Array<{
      departure_iata: string;
      departure_at: string;
      arrival_iata: string;
      arrival_at: string;
      carrier_code: string;
      number: string;
      duration: string | null;
      stops: number;
    }>;
  }>;
};

export type ApiFlightsResponse = {
  origin: string;
  destination: string;
  offers: ApiFlightOffer[];
};

export type ApiWeatherResponse = {
  location: { name?: string; country?: string; lat: number; lon: number };
  current: {
    temperature_c: number;
    weather_code: number;
    wind_kph: number;
    humidity: number;
  };
  daily: Array<{
    date: string;
    temp_max: number;
    temp_min: number;
    weather_code: number;
    precipitation_mm: number;
  }>;
};

function qs(params: Record<string, string | number | undefined>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") p.set(k, String(v));
  }
  return p.toString() ? `?${p.toString()}` : "";
}

export const travelApi = {
  weather: (params: { place?: string; lat?: number; lon?: number }) =>
    request<ApiWeatherResponse>(`/api/travel/weather${qs(params)}`, { auth: false }),

  hotels: (params: {
    city?: string;
    cityCode?: string;
    checkIn?: string;
    checkOut?: string;
    adults?: number;
  }) => request<ApiHotelsResponse>(`/api/travel/hotels${qs(params)}`, { auth: false }),

  flights: (params: {
    origin?: string;
    destination?: string;
    originCity?: string;
    destinationCity?: string;
    departureDate: string;
    returnDate?: string;
    adults?: number;
    currency?: string;
    max?: number;
  }) => request<ApiFlightsResponse>(`/api/travel/flights${qs(params)}`, { auth: false }),

  locations: (params: { keyword: string; subType?: string }) =>
    request<{ results: ApiLocationHit[] }>(`/api/travel/locations${qs(params)}`, { auth: false }),
};

// ---- P4 · Editorial & Narrative Discovery ---------------------------------

export type StoryUpdateKind = "WEATHER" | "CROWD" | "PRICE" | "GENERIC";

export type ApiContextTag = {
  key: string;
  display: string;
  description: string;
  experience_filter_summary: string;
};

export type ApiStoryPost = {
  id: string;
  author_id: string;
  provider_id: string | null;
  experience_id: string | null;
  title: string;
  slug: string;
  summary: string | null;
  body_md: string;
  cover_image_url: string | null;
  city: string | null;
  location_hint: Record<string, unknown> | null;
  context_tags: string[];
  narrative_quality_score: number;
  published: boolean;
  published_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ApiActiveUpdate = {
  id: string;
  kind: StoryUpdateKind;
  message: string;
  matched_condition: Record<string, unknown>;
};

export type ApiStoryUpdate = {
  id: string;
  post_id: string;
  kind: StoryUpdateKind;
  message: string;
  condition: Record<string, unknown>;
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
};

export type ApiRankedStory = {
  post: ApiStoryPost;
  score: number;
  matched_tags: string[];
  quality_component: number;
  match_component: number;
  freshness_component: number;
};

export type ApiFeedResponse = {
  stories: ApiRankedStory[];
  considered: number;
  applied_tag: string | null;
};

export type ApiStoryReadResponse = {
  post: ApiStoryPost;
  active_updates: ApiActiveUpdate[];
};

export type StoryRuntimeContext = {
  weather?: "rain" | "clear" | "snow" | "cloudy" | string;
  temperature_c?: number;
  hour_utc?: number;
  crowd_pct?: number;
};

function _storyCtxQs(ctx: StoryRuntimeContext | undefined): string {
  if (!ctx) return "";
  const qs = new URLSearchParams();
  if (ctx.weather !== undefined) qs.set("weather", ctx.weather);
  if (ctx.temperature_c !== undefined) qs.set("temperature_c", String(ctx.temperature_c));
  if (ctx.hour_utc !== undefined) qs.set("hour_utc", String(ctx.hour_utc));
  if (ctx.crowd_pct !== undefined) qs.set("crowd_pct", String(ctx.crowd_pct));
  const s = qs.toString();
  return s ? `?${s}` : "";
}

export const storiesApi = {
  listContextTags: () => request<ApiContextTag[]>("/api/context-tags", { auth: false }),

  feed: (params: { tag?: string; city?: string; limit?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.tag) qs.set("tag", params.tag);
    if (params.city) qs.set("city", params.city);
    if (params.limit) qs.set("limit", String(params.limit));
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<ApiFeedResponse>(`/api/stories${suffix}`, { auth: false });
  },

  feedForMe: (params: { tag?: string; city?: string; limit?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.tag) qs.set("tag", params.tag);
    if (params.city) qs.set("city", params.city);
    if (params.limit) qs.set("limit", String(params.limit));
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<ApiFeedResponse>(`/api/stories/for-me${suffix}`);
  },

  read: (slug: string, ctx?: StoryRuntimeContext) =>
    request<ApiStoryReadResponse>(`/api/stories/${encodeURIComponent(slug)}${_storyCtxQs(ctx)}`, { auth: false }),

  // ---- provider writes -----------------------------------------------------
  create: (payload: {
    title: string;
    body_md: string;
    summary?: string;
    cover_image_url?: string;
    city?: string;
    location_hint?: Record<string, unknown>;
    experience_id?: string;
    context_tags?: string[];
  }) => request<ApiStoryPost>("/api/stories", { method: "POST", body: payload }),

  update: (storyId: string, payload: Partial<{
    title: string;
    body_md: string;
    summary: string;
    cover_image_url: string;
    city: string;
    location_hint: Record<string, unknown>;
    experience_id: string;
    context_tags: string[];
  }>) => request<ApiStoryPost>(`/api/stories/${storyId}`, { method: "PATCH", body: payload }),

  publish: (storyId: string) =>
    request<ApiStoryPost>(`/api/stories/${storyId}/publish`, { method: "POST" }),

  remove: (storyId: string) => request<void>(`/api/stories/${storyId}`, { method: "DELETE" }),

  addUpdate: (storyId: string, payload: {
    kind: StoryUpdateKind;
    message: string;
    condition?: Record<string, unknown>;
    expires_at?: string;
  }) => request<ApiStoryUpdate>(`/api/stories/${storyId}/updates`, { method: "POST", body: payload }),

  removeUpdate: (storyId: string, updateId: string) =>
    request<void>(`/api/stories/${storyId}/updates/${updateId}`, { method: "DELETE" }),
};

// ---- P5 · Itinerary Dependency Graph & Recovery ---------------------------

export type NodeKind =
  | "FLIGHT" | "TRAIN" | "TRANSFER" | "HOTEL" | "ACTIVITY" | "MEAL" | "GENERIC";
export type NodeStatus =
  | "SCHEDULED" | "AT_RISK" | "IMPACTED" | "DISRUPTED" | "REPLACED";
export type EdgeKind = "REQUIRES" | "SEQUENCED" | "OPTIONAL";
export type DisruptionKind =
  | "DELAY" | "CANCELLATION" | "WEATHER" | "OVERBOOKED" | "OTHER";
export type RefundClass =
  | "FULLY_REFUNDABLE" | "PARTIALLY_REFUNDABLE" | "NON_REFUNDABLE";

export type ApiItineraryNode = {
  id: string;
  itinerary_id: string;
  kind: NodeKind;
  title: string;
  start_at: string;
  end_at: string;
  location_label: string | null;
  lat: number | null;
  lng: number | null;
  cost: number;
  currency: string;
  refund_class: RefundClass;
  change_fee: number;
  provider_ref: string | null;
  status: NodeStatus;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ApiItineraryEdge = {
  id: string;
  itinerary_id: string;
  from_node_id: string;
  to_node_id: string;
  edge_kind: EdgeKind;
  min_buffer_mins: number;
  created_at: string;
};

export type ApiGraph = {
  itinerary_id: string;
  nodes: ApiItineraryNode[];
  edges: ApiItineraryEdge[];
};

export type ApiBufferRisk = {
  edge_id: string;
  from_node_id: string;
  from_title: string;
  to_node_id: string;
  to_title: string;
  actual_buffer_mins: number;
  required_buffer_mins: number;
  severity: "warning" | "critical";
  message: string;
};

export type ApiRiskReport = {
  itinerary_id: string;
  risks: ApiBufferRisk[];
  at_risk_node_ids: string[];
};

export type ApiDisruption = {
  id: string;
  itinerary_id: string;
  node_id: string;
  kind: DisruptionKind;
  delta_mins: number;
  note: string | null;
  is_resolved: boolean;
  created_at: string;
};

export type ApiImpactReport = {
  disrupted_node_ids: string[];
  impacted_node_ids: string[];
  impacted_nodes: ApiItineraryNode[];
};

export type ApiPlanAction = {
  node_id: string;
  kind: "SHIFT" | "MODIFY" | "CANCEL" | "REBOOK" | "DROP_OPTIONAL";
  detail: string;
  delta_mins: number;
  monetary_penalty: number;
};

export type ApiRecoveryPlan = {
  id: string;
  itinerary_id: string;
  label: string;
  strategy: "fastest" | "cheapest" | "least_impact" | string;
  penalty: number;
  cost_delta: number;
  time_delta_mins: number;
  nodes_modified: number;
  actions: ApiPlanAction[];
  summary: string | null;
  is_applied: boolean;
  applied_at: string | null;
  created_at: string;
};

export type ApiRecoveryResponse = {
  itinerary_id: string;
  disruptions: ApiDisruption[];
  plans: ApiRecoveryPlan[];
};

export type ApiApplyReport = {
  plan_id: string;
  label: string;
  strategy: string;
  nodes_shifted: number;
  nodes_modified: number;
  nodes_cancelled: number;
  nodes_dropped: number;
  edges_removed: number;
  residual_conflicts: string[];
  graph: ApiGraph;
};

export const graphApi = {
  get: (itineraryId: string) => request<ApiGraph>(`/api/itineraries/${itineraryId}/graph`),

  addNode: (itineraryId: string, payload: {
    kind: NodeKind; title: string;
    start_at: string; end_at: string;
    location_label?: string; lat?: number; lng?: number;
    cost?: number; currency?: string;
    refund_class?: RefundClass; change_fee?: number;
    provider_ref?: string; metadata_json?: Record<string, unknown>;
  }) => request<ApiItineraryNode>(`/api/itineraries/${itineraryId}/nodes`, { method: "POST", body: payload }),

  updateNode: (itineraryId: string, nodeId: string, payload: Partial<{
    kind: NodeKind; title: string; start_at: string; end_at: string;
    location_label: string; lat: number; lng: number;
    cost: number; currency: string; refund_class: RefundClass; change_fee: number;
    provider_ref: string; status: NodeStatus;
    metadata_json: Record<string, unknown>;
  }>) => request<ApiItineraryNode>(`/api/itineraries/${itineraryId}/nodes/${nodeId}`, { method: "PATCH", body: payload }),

  removeNode: (itineraryId: string, nodeId: string) =>
    request<void>(`/api/itineraries/${itineraryId}/nodes/${nodeId}`, { method: "DELETE" }),

  addEdge: (itineraryId: string, payload: {
    from_node_id: string; to_node_id: string;
    edge_kind?: EdgeKind; min_buffer_mins?: number;
  }) => request<ApiItineraryEdge>(`/api/itineraries/${itineraryId}/edges`, { method: "POST", body: payload }),

  removeEdge: (itineraryId: string, edgeId: string) =>
    request<void>(`/api/itineraries/${itineraryId}/edges/${edgeId}`, { method: "DELETE" }),

  risks: (itineraryId: string) => request<ApiRiskReport>(`/api/itineraries/${itineraryId}/risks`),
  applyRisks: (itineraryId: string) =>
    request<ApiRiskReport>(`/api/itineraries/${itineraryId}/risks/apply`, { method: "POST" }),

  declareDisruptions: (itineraryId: string, payload: Array<{
    node_id: string; kind: DisruptionKind; delta_mins?: number; note?: string;
  }>) => request<ApiDisruption[]>(`/api/itineraries/${itineraryId}/disruptions`, { method: "POST", body: payload }),

  impact: (itineraryId: string) => request<ApiImpactReport>(`/api/itineraries/${itineraryId}/impact`),

  generateRecovery: (itineraryId: string) =>
    request<ApiRecoveryResponse>(`/api/itineraries/${itineraryId}/recovery`, { method: "POST" }),

  applyPlan: (itineraryId: string, planId: string) =>
    request<ApiApplyReport>(`/api/itineraries/${itineraryId}/recovery/${planId}/apply`, { method: "POST" }),
};

// ---- realtime subscription -------------------------------------------------

export function subscribeToUpdates(onEvent: (event: unknown) => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  const source = new EventSource(`${API_BASE}/api/realtime/stream`);
  source.onmessage = (e) => {
    try { onEvent(JSON.parse(e.data)); } catch { /* ignore */ }
  };
  return () => source.close();
}
