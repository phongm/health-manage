import { describe, expect, it } from 'vitest'
import { calcBmr, calcRemaining, calcTargetKcal, calcTdee, computeProfileTargets, detectExclusion } from './index'

describe('nutrition core', () => {
  it('calculates male BMR', () => {
    expect(calcBmr(1, 70, 175, 30)).toBe(1648.8)
  })

  it('calculates female BMR', () => {
    expect(calcBmr(2, 50, 150, 30)).toBe(1126.5)
  })

  it('clamps aggressive cut to female safety floor', () => {
    const tdee = calcTdee(1126.5, 1)
    const { target, warnings } = calcTargetKcal(tdee, 1126.5, 2, 1, 2)
    expect(target).toBe(1200)
    expect(warnings).toContain('rate_too_aggressive')
    expect(warnings).toContain('below_bmr')
    expect(warnings).toContain('below_floor')
  })

  it('detects kidney as excluded health flag', () => {
    expect(detectExclusion({ birthYear: 1990, nowYear: 2026, weightKg: 70, heightCm: 170, healthFlags: ['kidney'] }).reason).toBe(
      'kidney',
    )
  })

  it('computes protein target for fat loss', () => {
    const result = computeProfileTargets(
      {
        gender: 1,
        birthYear: 1996,
        heightCm: 175,
        weightKg: 70,
        activityLevel: 2,
        goal: 1,
        goalRateKgWk: 0.5,
      },
      2026,
    )
    expect(result.isExcluded).toBe(false)
    expect(result.targetNutrients.protein_g).toBe(126)
    expect(result.targetKcal).toBeLessThan(result.tdeeKcal)
  })

  it('credits only 70% of exercise to remaining energy', () => {
    const remaining = calcRemaining({ energy_kcal: 1500, protein_g: 100 }, { energy_kcal: 500, protein_g: 40 }, 200)
    expect(remaining.energy_kcal).toBe(1140)
    expect(remaining.protein_g).toBe(60)
  })
})
