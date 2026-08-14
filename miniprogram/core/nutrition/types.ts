export type Gender = 1 | 2
export type ActivityLevel = 1 | 2 | 3 | 4 | 5
export type Goal = 1 | 2 | 3

export type Nutrients = {
  energy_kcal: number
  protein_g: number
  fat_g: number
  cho_g: number
  fiber_g: number
  sodium_mg: number
  [key: string]: number
}

export type ProfileInput = {
  gender: Gender
  birthYear: number
  heightCm: number
  weightKg: number
  activityLevel: ActivityLevel
  goal: Goal
  goalRateKgWk?: number
  healthFlags?: string[]
}

export type ProfileTargets = {
  bmrKcal: number
  tdeeKcal: number
  targetKcal: number
  targetNutrients: Nutrients
  warnings: string[]
  isExcluded: boolean
  excludeReason: string | null
  bmi: number
  age: number
}
