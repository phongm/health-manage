const BASE_URL = 'http://127.0.0.1:8100/api/health/v1'

type ApiResult<T> = { code: number; message: string; data: T }

export class ApiError extends Error {
  code: number
  status: number
  constructor(message: string, code = 9001, status = 500) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
  }
}

export type FoodItem = {
  food_id: number
  name: string
  category: string
  nutrients_per_100g: Record<string, number>
  portions: { label: string; grams: number; is_default: boolean }[]
}

export type Dashboard = {
  date: string
  target: Record<string, number>
  intake: Record<string, number>
  exercise: { kcal_burned: number; credited_kcal: number }
  remaining: Record<string, number>
  meals: Record<string, { kcal: number; logged: boolean }>
  next_meal: string
  micros?: Record<string, { intake?: number; target?: number; remaining?: number }>
  items: {
    id: number
    meal_type: string
    food_id: number | null
    food_name: string
    grams: number
    portion_label: string | null
    nutrients: Record<string, number>
    input_source: string
  }[]
}

export type RecItem = {
  food_id: number
  name: string
  role: string
  grams: number
  portion_label: string
  nutrients: Record<string, number>
  swappable: boolean
}

export type Recommendation = {
  rec_id: number
  meal_type: string
  scene: string
  items: RecItem[]
  total: Record<string, number>
  budget: { energy_kcal: number }
  reasons: string[]
  avoid_list: { title: string; reason: string; level: string }[]
  swaps_remaining: number
  version: string
}

export type ParseResult = {
  items: {
    food_id: number
    name: string
    grams: number
    portion_label: string
    confidence: number
    need_confirm?: boolean
  }[]
  unresolved: string[]
  parser?: string
}

function getToken(): string {
  const app = getApp<{ globalData: { token: string } }>()
  return app.globalData.token || wx.getStorageSync('token') || ''
}

export function request<T>(path: string, method: 'GET' | 'POST' | 'PUT' | 'DELETE', data?: object): Promise<T> {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BASE_URL}${path}`,
      method,
      data,
      header: {
        'Content-Type': 'application/json',
        Authorization: getToken() ? `Bearer ${getToken()}` : '',
      },
      success(res) {
        const body = res.data as ApiResult<T>
        if (res.statusCode >= 200 && res.statusCode < 300 && body?.code === 0) {
          resolve(body.data)
          return
        }
        reject(new ApiError(body?.message || `请求失败 ${res.statusCode}`, body?.code || 9001, res.statusCode))
      },
      fail(err) {
        reject(err)
      },
    })
  })
}

export const api = {
  login: (code: string) =>
    request<{ token: string; is_new_user: boolean; profile_completed: boolean }>('/auth/login', 'POST', { code }),
  getProfile: () => request<Record<string, unknown>>('/profile', 'GET'),
  putProfile: (payload: object) => request<Record<string, unknown>>('/profile', 'PUT', payload),
  getPreferences: () => request<Record<string, unknown>>('/preferences', 'GET'),
  putPreferences: (payload: object) => request<Record<string, unknown>>('/preferences', 'PUT', payload),
  searchFoods: (q: string) => request<{ items: FoodItem[] }>(`/foods/search?q=${encodeURIComponent(q)}`, 'GET'),
  getFood: (id: number) => request<FoodItem>(`/foods/${id}`, 'GET'),
  hotFoods: () => request<{ items: FoodItem[] }>('/foods/hot?limit=30', 'GET'),
  parseText: (text: string) => request<ParseResult>('/parse/text', 'POST', { text }),
  parseImage: (hint: string, imageFileId?: string) =>
    request<ParseResult>('/parse/image', 'POST', { hint, image_file_id: imageFileId || null }),
  createIntake: (payload: object) => request<{ created_ids: number[]; today: Dashboard }>('/intake', 'POST', payload),
  deleteIntake: (id: number) => request<{ today: Dashboard }>(`/intake/${id}`, 'DELETE'),
  getDashboard: (date: string) => request<Dashboard>(`/dashboard?date=${date}`, 'GET'),
  recommend: (payload: { date: string; meal_type?: string; scene?: string }) =>
    request<Recommendation>('/recommend', 'POST', payload),
  swap: (recId: number, foodId: number, reason: string) =>
    request<Recommendation>(`/recommend/${recId}/swap`, 'POST', { food_id: foodId, reason }),
  feedback: (recId: number, action: string, foodIds: number[]) =>
    request<{ ok: boolean }>(`/recommend/${recId}/feedback`, 'POST', { action, food_ids: foodIds }),
  avoidList: (date: string) =>
    request<{ items: { title: string; reason: string; level: string }[] }>(`/avoid-list?date=${date}`, 'GET'),
  recommendPlan: (start: string, days = 3, scene?: string) =>
    request<{ days: { date: string; meals: Recommendation[] }[] }>('/recommend/plan', 'POST', { start, days, scene }),
  getWeight: (from: string, to: string) =>
    request<{
      logs: { log_date: string; weight_kg: number }[]
      ma7: { log_date: string; weight_kg: number }[]
      trend_kg_per_week: number | null
    }>(`/weight?from=${from}&to=${to}`, 'GET'),
  putWeight: (payload: { log_date: string; weight_kg: number; body_fat_pct?: number }) =>
    request<{ log_date: string; weight_kg: number }>('/weight', 'POST', payload),
  listExercises: () =>
    request<{ items: { id: number; name: string; category: string; met: number[] }[] }>('/exercises', 'GET'),
  createExercise: (payload: object) =>
    request<{ id: number; kcal_burned: number; credited_kcal: number; today: Dashboard }>('/exercise', 'POST', payload),
  listExerciseLogs: (date: string) =>
    request<{ items: { id: number; name: string; duration_min: number; intensity: number; kcal_burned: number }[] }>(
      `/exercise?date=${date}`,
      'GET',
    ),
  deleteExercise: (id: number) => request<{ today: Dashboard }>(`/exercise/${id}`, 'DELETE'),
  weeklyReport: () => request<Record<string, unknown>>('/report/weekly', 'GET'),
  exportData: () => request<Record<string, unknown>>('/export', 'GET'),
  contribute: (payload: object) =>
    request<{ id: number; status: number; message: string }>('/foods/contribute', 'POST', payload),
  sync: (since?: string) => request<Record<string, unknown>>(since ? `/sync?since=${encodeURIComponent(since)}` : '/sync', 'GET'),
  syncBatch: (ops: { client_op_id: string; type: string; payload: object }[]) =>
    request<{ results: { client_op_id: string; idempotent?: boolean; result?: unknown }[] }>('/sync/batch', 'POST', { ops }),
  membership: () =>
    request<{
      plan: string
      payment_enabled: boolean
      quotas: Record<string, number>
      note: string
    }>('/membership', 'GET'),
}
