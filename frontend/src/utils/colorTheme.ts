export type Rgb = { r: number; g: number; b: number }

const clamp = (n: number, min = 0, max = 255) => Math.min(max, Math.max(min, n))

export const parseColorToRgb = (input: string): Rgb | null => {
  const raw = String(input || '').trim()
  if (!raw) return null

  const hex = raw.startsWith('#') ? raw.slice(1) : raw
  if (/^[0-9a-fA-F]{3}$/.test(hex)) {
    const a = hex.charAt(0)
    const b0 = hex.charAt(1)
    const c = hex.charAt(2)
    const r = parseInt(a + a, 16)
    const g = parseInt(b0 + b0, 16)
    const b = parseInt(c + c, 16)
    return { r, g, b }
  }
  if (/^[0-9a-fA-F]{6}$/.test(hex)) {
    const r = parseInt(hex.slice(0, 2), 16)
    const g = parseInt(hex.slice(2, 4), 16)
    const b = parseInt(hex.slice(4, 6), 16)
    return { r, g, b }
  }

  const rgbMatch = raw.match(/^rgba?\(\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})(?:\s*,\s*([0-9]*\.?[0-9]+)\s*)?\)$/i)
  if (rgbMatch) {
    const r = clamp(Number(rgbMatch[1]))
    const g = clamp(Number(rgbMatch[2]))
    const b = clamp(Number(rgbMatch[3]))
    const a = rgbMatch[4] != null ? Math.max(0, Math.min(1, Number(rgbMatch[4]))) : 1
    if (a >= 1) return { r, g, b }
    const base: Rgb = { r: 255, g: 255, b: 255 }
    return blend(base, { r, g, b }, a)
  }

  return null
}

export const rgbToHex = (rgb: Rgb): string => {
  const to = (n: number) => clamp(Math.round(n)).toString(16).padStart(2, '0')
  return `#${to(rgb.r)}${to(rgb.g)}${to(rgb.b)}`
}

export const blend = (base: Rgb, top: Rgb, alphaTop: number): Rgb => {
  const a = Math.max(0, Math.min(1, alphaTop))
  return {
    r: base.r + (top.r - base.r) * a,
    g: base.g + (top.g - base.g) * a,
    b: base.b + (top.b - base.b) * a,
  }
}

const srgbToLinear = (c: number) => {
  const x = c / 255
  return x <= 0.04045 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4)
}

export const relativeLuminance = (rgb: Rgb): number => {
  const r = srgbToLinear(rgb.r)
  const g = srgbToLinear(rgb.g)
  const b = srgbToLinear(rgb.b)
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

export const contrastRatio = (a: Rgb, b: Rgb): number => {
  const la = relativeLuminance(a)
  const lb = relativeLuminance(b)
  const lighter = Math.max(la, lb)
  const darker = Math.min(la, lb)
  return (lighter + 0.05) / (darker + 0.05)
}

export const adjustTowards = (rgb: Rgb, target: Rgb, amount01: number): Rgb =>
  blend(rgb, target, Math.max(0, Math.min(1, amount01)))

export const ensureWcagAaText = (bg: Rgb, minRatio = 4.5): { bg: Rgb; fg: Rgb; ratio: number } => {
  const white: Rgb = { r: 255, g: 255, b: 255 }
  const black: Rgb = { r: 0, g: 0, b: 0 }

  const rWhite = contrastRatio(bg, white)
  const rBlack = contrastRatio(bg, black)
  const bestFg = rWhite >= rBlack ? white : black
  const bestRatio = Math.max(rWhite, rBlack)
  if (bestRatio >= minRatio) return { bg, fg: bestFg, ratio: bestRatio }

  const toward = bestFg === white ? black : white
  let cur = bg
  let ratio = bestRatio
  for (let i = 0; i < 24 && ratio < minRatio; i += 1) {
    cur = adjustTowards(cur, toward, 0.06)
    ratio = contrastRatio(cur, bestFg)
  }
  return { bg: cur, fg: bestFg, ratio }
}

export const deriveHoverAndActive = (bg: Rgb): { hover: Rgb; active: Rgb; border: Rgb } => {
  const lum = relativeLuminance(bg)
  const toward = lum > 0.5 ? ({ r: 0, g: 0, b: 0 }) : ({ r: 255, g: 255, b: 255 })
  const hover = adjustTowards(bg, toward, 0.06)
  const active = adjustTowards(bg, toward, 0.12)
  const border = adjustTowards(bg, toward, 0.18)
  return { hover, active, border }
}
