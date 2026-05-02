import { useEffect, useState } from 'react'
import { applyRecipeLadder, saveRecipes } from '../api.js'
import { EditableTable } from '../components/EditableTable.js'
import type { RecipesPayload } from '../types.js'

const DEFAULT_LADDER = {
  foundation_success: 60,
  foundation_time: 30,
  foundation_spirit: 30,
  foundation_herb_count: 3,
  golden_success: 65,
  golden_time: 40,
  golden_spirit: 40,
  lower_pill_count: 3,
  success_step: 5,
  time_step: 10,
  spirit_step: 10,
  mat_herb_count: 10,
}

export function RecipesPage({ payload, onChanged, onSaved }: { payload: RecipesPayload; onChanged?: (next: RecipesPayload) => void; onSaved: (next: RecipesPayload) => void }) {
  const [rows, setRows] = useState<Record<string, any>[]>(payload.rows)
  const [ladder, setLadder] = useState(DEFAULT_LADDER)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    onChanged?.({ ...payload, rows })
  }, [rows, onChanged])

  const applyBatch = async () => {
    const nextRows = await applyRecipeLadder({ rows, ...ladder })
    setRows(nextRows)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const next = await saveRecipes(rows)
      setRows(next.rows)
      onSaved(next)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <h2>丹方配置（recipes）</h2>
        <p>保留原有阶梯生成逻辑，支持单行编辑和批量生成。</p>
      </header>
      <section className="card">
        <h3>按阶梯规则批量生成</h3>
        <div className="form-grid form-grid--triple">
          {Object.entries(ladder).map(([key, value]) => (
            <label key={key} className="field">
              <span>{key}</span>
              <input type="number" value={value} min={0} step={1} onChange={(e) => setLadder((prev) => ({ ...prev, [key]: Number(e.target.value) }))} />
            </label>
          ))}
        </div>
        <div className="actions-row"><button type="button" onClick={applyBatch}>应用阶梯规则到全部破境丹方</button></div>
      </section>
      <section className="card">
        <EditableTable
          columns={[
            { key: 'recipe_id', label: 'recipe_id', readOnly: true, width: '110px' },
            { key: '丹药名称', label: '丹药名称', readOnly: true, width: '120px' },
            { key: 'lower_pill_id', label: '低阶丹药ID', readOnly: true, width: '120px' },
            { key: '成功率(%)', label: '成功率(%)', type: 'number', min: 0, max: 100 },
            { key: '耗时(秒)', label: '耗时(秒)', type: 'number', min: 1 },
            { key: '消耗灵气', label: '消耗灵气', type: 'number', min: 0 },
            { key: '低阶丹药数量', label: '低阶丹药数量', type: 'number', min: 0 },
            { key: '草药数量', label: '草药数量', type: 'number', min: 0 },
            { key: '破境草数量', label: '破境草数量', type: 'number', min: 0 },
          ]}
          rows={rows}
          onChange={setRows}
        />
      </section>
      <div className="actions-row"><button type="button" className="primary-btn" onClick={handleSave} disabled={saving}>{saving ? '保存中...' : '保存 recipes 配置'}</button></div>
    </div>
  )
}
