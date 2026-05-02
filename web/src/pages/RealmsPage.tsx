import { useEffect, useMemo, useState } from 'react'
import { saveRealms } from '../api.js'
import type { RealmsPayload } from '../types.js'
import { EditableTable } from '../components/EditableTable.js'

export function RealmsPage({ payload, onChanged, onSaved }: { payload: RealmsPayload; onChanged?: (next: RealmsPayload) => void; onSaved: (next: RealmsPayload) => void }) {
  const [editor, setEditor] = useState<Record<string, any>>(payload.editor)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    onChanged?.({ ...payload, editor })
  }, [editor, onChanged])

  const lianqiRows = editor.lianqiRows ?? []
  const updateField = (key: string, value: any) => setEditor((prev) => ({ ...prev, [key]: value }))

  const attrFields = [
    ['foundation_base_health', 'health 基准'],
    ['foundation_base_attack', 'attack 基准'],
    ['foundation_base_defense', 'defense 基准'],
    ['stat_level_multiplier', '层内递推倍率'],
    ['stat_realm_multiplier', '跨大境界首层倍率'],
  ]
  const resourceFields = [
    ['foundation_base_cost', 'spirit_energy_cost 基准'],
    ['foundation_base_stone_cost', 'spirit_stone_cost 基准'],
    ['foundation_base_max_spirit', 'max_spirit_energy 基准'],
    ['resource_level_multiplier', '层内递推倍率'],
    ['resource_realm_multiplier', '跨大境界首层倍率'],
  ]

  const warning = useMemo(() => {
    const statLevel = Number(editor.stat_level_multiplier ?? 1)
    const statRealm = Number(editor.stat_realm_multiplier ?? 1)
    const resourceLevel = Number(editor.resource_level_multiplier ?? 1)
    const resourceRealm = Number(editor.resource_realm_multiplier ?? 1)
    return {
      stat: statLevel ** 9 >= statRealm,
      resource: resourceLevel ** 9 >= resourceRealm,
    }
  }, [editor])

  const handleSave = async () => {
    setSaving(true)
    try {
      const next = await saveRealms({ ...editor, lianqiRows })
      setEditor(next.editor)
      onSaved(next)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <h2>境界配置（realms）</h2>
        <p>保持原有基准值 + 倍率逻辑，炼气期继续允许逐层手调。</p>
      </header>
      <section className="card card-grid two-up">
        <div>
          <h3>属性（筑基1层基准 + 属性倍率）</h3>
          <div className="form-grid">
            {attrFields.map(([key, label]) => (
              <label key={key} className="field">
                <span>{label}</span>
                <input type="number" value={editor[key] ?? ''} step={key.includes('multiplier') ? 0.01 : 1} min={1} onChange={(e) => updateField(key, Number(e.target.value))} />
              </label>
            ))}
          </div>
          {warning.stat ? <p className="hint hint--warn">属性层内递推倍率的 9 次方应小于属性跨大境界首层倍率。</p> : null}
        </div>
        <div>
          <h3>资源（筑基1层基准 + 资源倍率）</h3>
          <div className="form-grid">
            {resourceFields.map(([key, label]) => (
              <label key={key} className="field">
                <span>{label}</span>
                <input type="number" value={editor[key] ?? ''} step={key.includes('multiplier') ? 0.01 : 1} min={1} onChange={(e) => updateField(key, Number(e.target.value))} />
              </label>
            ))}
          </div>
          {warning.resource ? <p className="hint hint--warn">资源层内递推倍率的 9 次方应小于资源跨大境界首层倍率。</p> : null}
        </div>
      </section>
      <section className="card">
        <h3>炼气期手动编辑（保留手动值）</h3>
        <EditableTable
          columns={[
            { key: '层级', label: '层级', readOnly: true },
            { key: 'health', label: 'health', type: 'number', min: 0 },
            { key: 'attack', label: 'attack', type: 'number', min: 0 },
            { key: 'defense', label: 'defense', type: 'number', min: 0 },
            { key: 'spirit_stone_cost', label: 'spirit_stone_cost', type: 'number', min: 0 },
            { key: 'spirit_energy_cost', label: 'spirit_energy_cost', type: 'number', min: 0 },
            { key: 'max_spirit_energy', label: 'max_spirit_energy', type: 'number', min: 0 },
          ]}
          rows={lianqiRows}
          onChange={(rows) => updateField('lianqiRows', rows)}
        />
      </section>
      <div className="actions-row">
        <button type="button" className="primary-btn" onClick={handleSave} disabled={saving}>{saving ? '保存中...' : '保存 realms 配置'}</button>
      </div>
    </div>
  )
}
