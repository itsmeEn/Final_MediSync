import { describe, it, expect } from 'vitest'
import { parseColorToRgb, contrastRatio, ensureWcagAaText } from '../utils/colorTheme'

describe('colorTheme', () => {
  it('parses hex colors', () => {
    expect(parseColorToRgb('#ffffff')).toEqual({ r: 255, g: 255, b: 255 })
    expect(parseColorToRgb('#000')).toEqual({ r: 0, g: 0, b: 0 })
    expect(parseColorToRgb('1976d2')).toEqual({ r: 25, g: 118, b: 210 })
  })

  it('parses rgb/rgba colors', () => {
    expect(parseColorToRgb('rgb(255, 0, 128)')).toEqual({ r: 255, g: 0, b: 128 })
    const rgba = parseColorToRgb('rgba(0, 0, 0, 0.5)')
    expect(rgba).not.toBeNull()
  })

  it('computes contrast ratio', () => {
    const white = { r: 255, g: 255, b: 255 }
    const black = { r: 0, g: 0, b: 0 }
    expect(contrastRatio(white, black)).toBeGreaterThan(20)
  })

  it('ensures WCAG AA text contrast by selecting fg and adjusting bg when needed', () => {
    const bg = parseColorToRgb('#777777')!
    const { bg: adjBg, fg } = ensureWcagAaText(bg, 4.5)
    const effective = contrastRatio(adjBg, fg)
    expect(effective).toBeGreaterThanOrEqual(4.5)
  })
})
