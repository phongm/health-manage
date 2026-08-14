export const KEYS = {
  token: 'token',
  profile: 'profile',
  prefs: 'prefs',
  recIndex: 'rec_index',
  foodsHot: 'foods_hot',
  syncQueue: 'sync_queue',
  meta: 'meta',
  records: (ym: string) => `rec_${ym}`,
} as const

export const SINGLE_KEY_LIMIT = 900 * 1024
export const TOTAL_LIMIT = 8 * 1024 * 1024

export type StorageAdapter = {
  get(key: string): unknown
  set(key: string, value: unknown): void
  remove(key: string): void
  info(): { currentSize: number; limitSize: number; keys: string[] }
}

export class CapacityError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'CapacityError'
  }
}

export function createStorage(adapter: StorageAdapter) {
  return {
    get<T>(key: string): T | null {
      const value = adapter.get(key)
      return (value as T) ?? null
    },
    set(key: string, value: unknown) {
      const serialized = JSON.stringify(value)
      const size = unescape(encodeURIComponent(serialized)).length
      if (size > SINGLE_KEY_LIMIT) {
        throw new CapacityError(`storage key ${key} exceeds 900KB`)
      }
      adapter.set(key, value)
    },
    remove(key: string) {
      adapter.remove(key)
    },
  }
}
