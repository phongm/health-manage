import type { ActivityLevel, Gender, Goal, Nutrients, ProfileInput, ProfileTargets } from './types'

export const ACTIVITY_FACTOR: Record<ActivityLevel, number> = {
  1: 1.2,
  2: 1.375,
  3: 1.55,
  4: 1.725,
  5: 1.9,
}

export const SAFETY_FLOOR: Record<Gender, number> = { 1: 1500, 2: 1200 }
export const KCAL_PER_KG_FAT = 7700
export const MAX_DEFICIT_RATIO = 0.25
export const EXERCISE_CREDIT_RATIO = 0.7

const EXCLUDE_HEALTH_FLAGS = new Set([
  'diabetes',
  'hypertension',
  'kidney',
  'pregnant',
  'lactating',
  'eating_disorder',
])

export function calcAge(birthYear: number, nowYear: number): number {
  return Math.max(nowYear - birthYear, 1)
}

export function calcBmi(weightKg: number, heightCm: number): number {
  const heightM = heightCm / 100
  return round1(weightKg / (heightM * heightM))
}

export function calcBmr(gender: Gender, weightKg: number, heightCm: number, age: number): number {
  const base = 10 * weightKg + 6.25 * heightCm - 5 * age
  return round1(base + (gender === 1 ? 5 : -161))
}

export function calcTdee(bmr: number, activityLevel: ActivityLevel): number {
  return round1(bmr * ACTIVITY_FACTOR[activityLevel])
}

export function calcTargetKcal(
  tdee: number,
  bmr: number,
  gender: Gender,
  goal: Goal,
  goalRateKgWk: number,
): { target: number; warnings: string[] } {
  const warnings: string[] = []
  if (goal === 2) return { target: round1(tdee), warnings }
  if (goal === 3) return { target: round1(tdee * 1.1), warnings }

  let deficit = (goalRateKgWk * KCAL_PER_KG_FAT) / 7
  if (deficit > tdee * MAX_DEFICIT_RATIO) {
    deficit = tdee * MAX_DEFICIT_RATIO
    warnings.push('rate_too_aggressive')
  }

  let target = tdee - deficit
  if (target < bmr) {
    target = bmr
    warnings.push('below_bmr')
  }
  const floor = SAFETY_FLOOR[gender]
  if (target < floor) {
    target = floor
    warnings.push('below_floor')
  }
  return { target: round1(target), warnings }
}

export function calcTargetNutrients(targetKcal: number, weightKg: number, goal: Goal): Nutrients {
  const proteinG = weightKg * (goal === 1 ? 1.8 : 1.4)
  const fatG = (targetKcal * 0.25) / 9
  const choKcal = targetKcal - proteinG * 4 - fatG * 9
  const choG = Math.max(choKcal / 4, weightKg * 1.5)
  return {
    energy_kcal: round1(targetKcal),
    protein_g: round1(proteinG),
    fat_g: round1(fatG),
    cho_g: round1(choG),
    fiber_g: 27.0,
    sodium_mg: 2000.0,
  }
}

export function detectExclusion(input: {
  birthYear: number
  nowYear: number
  weightKg: number
  heightCm: number
  healthFlags?: string[]
}): { isExcluded: boolean; reason: string | null } {
  const flags = new Set((input.healthFlags || []).filter((f) => f && f !== 'none'))
  for (const flag of flags) {
    if (EXCLUDE_HEALTH_FLAGS.has(flag)) return { isExcluded: true, reason: flag }
  }
  if (calcAge(input.birthYear, input.nowYear) < 18) {
    return { isExcluded: true, reason: 'underage' }
  }
  if (calcBmi(input.weightKg, input.heightCm) < 18.5) {
    return { isExcluded: true, reason: 'low_bmi' }
  }
  return { isExcluded: false, reason: null }
}

export function computeProfileTargets(input: ProfileInput, nowYear: number): ProfileTargets {
  const exclusion = detectExclusion({
    birthYear: input.birthYear,
    nowYear,
    weightKg: input.weightKg,
    heightCm: input.heightCm,
    healthFlags: input.healthFlags,
  })
  const age = calcAge(input.birthYear, nowYear)
  const bmr = calcBmr(input.gender, input.weightKg, input.heightCm, age)
  const tdee = calcTdee(bmr, input.activityLevel)
  const { target, warnings } = calcTargetKcal(
    tdee,
    bmr,
    input.gender,
    input.goal,
    input.goalRateKgWk ?? 0.5,
  )
  return {
    bmrKcal: bmr,
    tdeeKcal: tdee,
    targetKcal: target,
    targetNutrients: calcTargetNutrients(target, input.weightKg, input.goal),
    warnings,
    isExcluded: exclusion.isExcluded,
    excludeReason: exclusion.reason,
    bmi: calcBmi(input.weightKg, input.heightCm),
    age,
  }
}

function round1(n: number): number {
  return Math.round(n * 10) / 10
}

export function scaleNutrients(per100g: Record<string, number>, grams: number): Record<string, number> {
  const scaled: Record<string, number> = {}
  for (const [key, value] of Object.entries(per100g)) {
    if (value == null) continue
    scaled[key] = Math.round((value * grams) / 10) / 10
  }
  return scaled
}

export function calcRemaining(
  target: Record<string, number>,
  intake: Record<string, number>,
  exerciseKcal = 0,
): Record<string, number> {
  const credit = exerciseKcal * EXERCISE_CREDIT_RATIO
  const remaining: Record<string, number> = {}
  for (const [key, value] of Object.entries(target)) {
    const consumed = intake[key] || 0
    remaining[key] = round1(key === 'energy_kcal' ? value + credit - consumed : value - consumed)
  }
  return remaining
}
