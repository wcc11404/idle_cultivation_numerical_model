import { useEffect, useState } from 'react'
import { saveEnemies } from '../api.js'
import { EditableTable } from '../components/EditableTable.js'
import type { EnemiesPayload } from '../types.js'

export function EnemiesPage({ payload, onChanged, onSaved }: { payload: EnemiesPayload; onChanged?: (next: EnemiesPayload) => void; onSaved: (next: EnemiesPayload) => void }) {
  const [rows, setRows] = useState<Record<string, any>[]>(payload.rows)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    onChanged?.({ ...payload, rows })
  }, [rows, onChanged])

  const handleSave = async () => {
    setSaving(true)
    try {
      const next = await saveEnemies(rows)
      setRows(next.rows)
      onSaved(next)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <h2>敌人模板配置（enemies）</h2>
        <p>可修改每个模板的生命/攻击/防御基值和成长率。</p>
      </header>
      <section className="card">
        <EditableTable
          columns={[
            { key: 'template_id', label: 'template_id', readOnly: true, width: '120px' },
            { key: '敌人名称', label: '敌人名称', readOnly: true, width: '140px' },
            { key: 'health_base', label: '生命基值', type: 'number', min: 0 },
            { key: 'attack_base', label: '攻击基值', type: 'number', min: 0 },
            { key: 'defense_base', label: '防御基值', type: 'number', min: 0 },
            { key: 'health_growth', label: '生命增长率', type: 'number', min: 0, step: 0.01 },
            { key: 'attack_growth', label: '攻击增长率', type: 'number', min: 0, step: 0.01 },
            { key: 'defense_growth', label: '防御增长率', type: 'number', min: 0, step: 0.01 },
          ]}
          rows={rows}
          onChange={setRows}
        />
      </section>
      <div className="actions-row"><button type="button" className="primary-btn" onClick={handleSave} disabled={saving}>{saving ? '保存中...' : '保存 enemies 配置'}</button></div>
    </div>
  )
}
