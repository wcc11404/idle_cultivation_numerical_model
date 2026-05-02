export function cloneDeep<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

export function stableStringify(value: unknown): string {
  const normalize = (input: any): any => {
    if (Array.isArray(input)) {
      return input.map(normalize)
    }
    if (input && typeof input === 'object') {
      return Object.keys(input)
        .sort()
        .reduce<Record<string, any>>((acc, key) => {
          acc[key] = normalize(input[key])
          return acc
        }, {})
    }
    return input
  }
  return JSON.stringify(normalize(value))
}

export function formatModelNumber(value: unknown): string {
  const num = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(num)) {
    if (value === null || value === undefined) return ''
    return String(value)
  }
  const fixed = num.toFixed(2)
  return fixed.replace(/\.00$/, '').replace(/(\.\d*[1-9])0+$/, '$1')
}

export function fmt(value: unknown): string {
  if (typeof value === 'number') {
    return formatModelNumber(value)
  }
  if (value === null || value === undefined) return ''
  return String(value)
}

export function uniqueKeys(rows: Record<string, any>[]): string[] {
  const keys = new Set<string>()
  rows.forEach((row) => Object.keys(row).forEach((key) => keys.add(key)))
  return [...keys]
}

export function renderCompareValue(baseValue: unknown, draftValue: unknown): { same: boolean; baseText: string; draftText: string } {
  const baseText = fmt(baseValue)
  const draftText = fmt(draftValue)
  return { same: baseText === draftText, baseText, draftText }
}
