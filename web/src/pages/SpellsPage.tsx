import { useEffect, useMemo, useState } from 'react'
import { applySpellBatch, saveSpells } from '../api.js'
import { EditableTable } from '../components/EditableTable.js'
import type { SpellsPayload } from '../types.js'
import { cloneDeep, uniqueKeys } from '../utils.js'

const PRIMARY_EFFECT_PREFIX = 'effect[0].'

function normalizeText(value: unknown) {
  if (value === null || value === undefined) return ''
  return String(value)
}

function ratioOrDefault(numerator: number, denominator: number, fallback: number) {
  if (!Number.isFinite(numerator) || !Number.isFinite(denominator) || denominator <= 0) {
    return fallback
  }
  const ratio = numerator / denominator
  if (!Number.isFinite(ratio) || ratio <= 0) {
    return fallback
  }
  return Number(ratio.toFixed(2))
}

function findLevel(rows: Record<string, any>[], level: number) {
  return rows.find((row) => Number(row.level) === level)
}

function deriveBatchDefaults(rows: Record<string, any>[]) {
  const level2 = findLevel(rows, 2)
  const level3 = findLevel(rows, 3)
  const level4 = findLevel(rows, 4)
  const level5 = findLevel(rows, 5)
  const level6 = findLevel(rows, 6)

  const spirit5Plus = level6
    ? ratioOrDefault(Number(level6.spirit_cost), Number(level5?.spirit_cost ?? 0), 4)
    : level5
      ? ratioOrDefault(Number(level5.spirit_cost), Number(level4?.spirit_cost ?? 0), 4)
      : 4

  const use2To4 = level3
    ? ratioOrDefault(Number(level3.use_count_required), Number(level2?.use_count_required ?? 0), 10)
    : level2
      ? ratioOrDefault(Number(level2.use_count_required), Number(findLevel(rows, 1)?.use_count_required ?? 0), 10)
      : 10

  const use5Plus = level6
    ? ratioOrDefault(Number(level6.use_count_required), Number(level5?.use_count_required ?? 0), 6)
    : level5
      ? ratioOrDefault(Number(level5.use_count_required), Number(level4?.use_count_required ?? 0), 6)
      : 6

  return {
    level5_plus_spirit_multiplier: spirit5Plus,
    level1_to_4_use_multiplier: use2To4,
    level5_plus_use_multiplier: use5Plus,
  }
}

function buildRows(config: any, spellId: string) {
  const spell = config?.spells?.[spellId]
  if (!spell) return []
  return Object.entries(spell.levels ?? {})
    .sort((a, b) => Number(a[0]) - Number(b[0]))
    .map(([level, row]: [string, any]) => {
      const primaryEffect = Array.isArray(row.effect) ? (row.effect[0] ?? {}) : (row.effect ?? {})
      const result: Record<string, any> = {
        level: Number(level),
        spirit_cost: row.spirit_cost,
        use_count_required: row.use_count_required,
        effect_count: Array.isArray(row.effect) ? row.effect.length : (row.effect ? 1 : 0),
      }
      Object.entries(row.attribute_bonus ?? {}).forEach(([key, value]) => {
        result[`attribute_bonus.${key}`] = value
      })
      Object.entries(primaryEffect).forEach(([key, value]) => {
        result[`${PRIMARY_EFFECT_PREFIX}${key}`] = value
      })
      return result
    })
}

function writeRows(config: any, spellId: string, rows: Record<string, any>[]) {
  const next = cloneDeep(config)
  const spell = next?.spells?.[spellId]
  if (!spell) return next
  const levels: Record<string, any> = {}
  rows.forEach((row) => {
    const level = String(row.level)
    const originalRow = spell.levels?.[level] ?? {}
    const nextRow: Record<string, any> = {
      ...cloneDeep(originalRow),
      spirit_cost: Number(row.spirit_cost),
      use_count_required: Number(row.use_count_required),
      attribute_bonus: {},
    }
    const originalEffects = Array.isArray(originalRow.effect)
      ? cloneDeep(originalRow.effect)
      : originalRow.effect
        ? [cloneDeep(originalRow.effect)]
        : []
    let primaryEffect = cloneDeep(originalEffects[0] ?? {})
    let touchedPrimaryEffect = false
    Object.entries(row).forEach(([key, value]) => {
      if (key.startsWith('attribute_bonus.')) {
        nextRow.attribute_bonus[key.replace('attribute_bonus.', '')] = typeof value === 'number' ? value : Number(value)
      }
      if (key.startsWith(PRIMARY_EFFECT_PREFIX)) {
        const subKey = key.replace(PRIMARY_EFFECT_PREFIX, '')
        if (subKey === 'effect_count') return
        touchedPrimaryEffect = true
        primaryEffect[subKey] = typeof value === 'number'
          ? value
          : (subKey === 'effect_type' || subKey === 'buff_type' || subKey === 'log_effect' || subKey === 'description'
              ? value
              : Number(value))
      }
    })
    if (touchedPrimaryEffect || originalEffects.length > 0) {
      nextRow.effect = [primaryEffect, ...originalEffects.slice(1)]
    } else {
      nextRow.effect = []
    }
    levels[level] = nextRow
  })
  spell.levels = levels
  return next
}

export function SpellsPage({ payload, onChanged, onSaved }: { payload: SpellsPayload; onChanged?: (next: SpellsPayload) => void; onSaved: (next: SpellsPayload) => void }) {
  const [config, setConfig] = useState<any>(payload.config)
  const [selectedSpellId, setSelectedSpellId] = useState<string>(payload.options[0]?.spellId ?? '')
  const [rows, setRows] = useState<Record<string, any>[]>(() => buildRows(payload.config, payload.options[0]?.spellId ?? ''))
  const [saving, setSaving] = useState(false)
  const [batch, setBatch] = useState({
    level2_to_4_spirit_multiplier: 5,
    level5_plus_spirit_multiplier: 4,
    level1_to_4_use_multiplier: 10,
    level5_plus_use_multiplier: 6,
  })

  useEffect(() => {
    setRows(buildRows(config, selectedSpellId))
  }, [config, selectedSpellId])

  useEffect(() => {
    const nextRows = buildRows(config, selectedSpellId)
    const derived = deriveBatchDefaults(nextRows)
    setBatch((prev) => ({
      ...prev,
      level2_to_4_spirit_multiplier: 5,
      ...derived,
    }))
  }, [config, selectedSpellId])

  useEffect(() => {
    onChanged?.({ ...payload, config: writeRows(config, selectedSpellId, rows) })
  }, [rows, config, selectedSpellId, onChanged])

  const options = payload.options
  const selectedSpell = useMemo(() => config?.spells?.[selectedSpellId], [config, selectedSpellId])
  const extraKeys = useMemo(() => uniqueKeys(rows).filter((key) => !['level', 'spirit_cost', 'use_count_required'].includes(key)), [rows])
  const columns = useMemo(() => {
    const base = [
      { key: 'level', label: 'level', readOnly: true as const, width: '80px' },
      { key: 'spirit_cost', label: 'spirit_cost', type: 'number' as const, min: 0 },
      { key: 'use_count_required', label: 'use_count_required', type: 'number' as const, min: 0 },
      { key: 'effect_count', label: 'effect_count', readOnly: true as const, width: '110px' },
    ]
    const extras = extraKeys.map((key) => {
      if (key === 'effect_count') {
        return { key, label: key, readOnly: true as const, width: '110px' }
      }
      const sample = rows.find((row) => row[key] !== undefined)?.[key]
      return {
        key,
        label: key,
        type: typeof sample === 'number' ? ('number' as const) : ('text' as const),
      }
    })
    return [...base, ...extras]
  }, [extraKeys, rows])

  const applySpiritBatch = async () => {
    const nextRows = await applySpellBatch({
      rows,
      level2_to_4_spirit_multiplier: batch.level2_to_4_spirit_multiplier,
      level5_plus_spirit_multiplier: batch.level5_plus_spirit_multiplier,
      level1_to_4_use_multiplier: null,
      level5_plus_use_multiplier: null,
    })
    setRows(nextRows)
    setBatch((prev) => ({
      ...prev,
      level2_to_4_spirit_multiplier: 5,
      ...deriveBatchDefaults(nextRows),
    }))
  }

  const applyUseBatch = async () => {
    const nextRows = await applySpellBatch({
      rows,
      level2_to_4_spirit_multiplier: null,
      level5_plus_spirit_multiplier: null,
      level1_to_4_use_multiplier: batch.level1_to_4_use_multiplier,
      level5_plus_use_multiplier: batch.level5_plus_use_multiplier,
    })
    setRows(nextRows)
    setBatch((prev) => ({
      ...prev,
      ...deriveBatchDefaults(nextRows),
    }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const nextConfig = writeRows(config, selectedSpellId, rows)
      const next = await saveSpells(nextConfig)
      setConfig(next.config)
      onSaved(next)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <h2>术法配置（spells）</h2>
        <p>已适配新的术法配置结构：保留 rarity / element / max_star / stars / 多 effect 列表。表格仍主要编辑每级灵气、熟练度、attribute_bonus，以及第一个 effect；其余 effect 与 stars 会原样保留。</p>
      </header>
      <section className="card card-grid two-up align-start">
        <label className="field">
          <span>选择术法</span>
          <select value={selectedSpellId} onChange={(e) => setSelectedSpellId(e.target.value)}>
            {options.map((option) => (
              <option key={option.spellId} value={option.spellId}>{option.name}（{option.spellId}）</option>
            ))}
          </select>
        </label>
        <div className="meta-block">
          <div><strong>当前术法：</strong>{selectedSpell?.name ?? selectedSpellId}</div>
          <div><strong>类型：</strong>{selectedSpell?.type ?? '-'}</div>
          <div><strong>稀有度：</strong>{normalizeText(selectedSpell?.rarity) || '-'}</div>
          <div><strong>五行：</strong>{normalizeText(selectedSpell?.element) || '-'}</div>
          <div><strong>当前 max_level：</strong>{selectedSpell?.max_level ?? '-'}</div>
          <div><strong>当前 max_star：</strong>{selectedSpell?.max_star ?? '-'}</div>
          <div><strong>配置等级：</strong>{Object.keys(selectedSpell?.levels ?? {}).length}</div>
          <div><strong>星级配置：</strong>{Object.keys(selectedSpell?.stars ?? {}).length}</div>
        </div>
      </section>
      <section className="card card-grid two-up">
        <div>
          <h3>灵气批量倍率</h3>
          <div className="form-grid">
            <label className="field"><span>2-4 级灵气递推倍率</span><input type="number" min={0.1} step={0.1} value={batch.level2_to_4_spirit_multiplier} onChange={(e) => setBatch((prev) => ({ ...prev, level2_to_4_spirit_multiplier: Number(e.target.value) }))} /></label>
            <label className="field"><span>5+ 级灵气递推倍率</span><input type="number" min={0.1} step={0.1} value={batch.level5_plus_spirit_multiplier} onChange={(e) => setBatch((prev) => ({ ...prev, level5_plus_spirit_multiplier: Number(e.target.value) }))} /></label>
          </div>
          <div className="actions-row"><button type="button" onClick={applySpiritBatch}>应用灵气倍率</button></div>
        </div>
        <div>
          <h3>熟练度批量倍率</h3>
          <div className="form-grid">
            <label className="field"><span>2-4 级熟练度递推倍率</span><input type="number" min={0.1} step={0.1} value={batch.level1_to_4_use_multiplier} onChange={(e) => setBatch((prev) => ({ ...prev, level1_to_4_use_multiplier: Number(e.target.value) }))} /></label>
            <label className="field"><span>5+ 级熟练度递推倍率</span><input type="number" min={0.1} step={0.1} value={batch.level5_plus_use_multiplier} onChange={(e) => setBatch((prev) => ({ ...prev, level5_plus_use_multiplier: Number(e.target.value) }))} /></label>
          </div>
          <div className="actions-row"><button type="button" onClick={applyUseBatch}>应用熟练度倍率</button></div>
        </div>
      </section>
      <section className="card">
        <EditableTable columns={columns} rows={rows} onChange={setRows} />
      </section>
      <div className="actions-row"><button type="button" className="primary-btn" onClick={handleSave} disabled={saving}>{saving ? '保存中...' : '保存 spells 配置'}</button></div>
    </div>
  )
}
