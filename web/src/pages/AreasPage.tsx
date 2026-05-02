import { useEffect, useMemo, useState } from 'react'
import { saveAreas } from '../api.js'
import { EditableTable } from '../components/EditableTable.js'
import type { AreasPayload } from '../types.js'
import { cloneDeep } from '../utils.js'

export function AreasPage({ payload, onChanged, onSaved }: { payload: AreasPayload; onChanged?: (next: AreasPayload) => void; onSaved: (next: AreasPayload) => void }) {
  const [config, setConfig] = useState<any>(payload.config)
  const [saving, setSaving] = useState(false)
  const [selectedAreaId, setSelectedAreaId] = useState<string>(payload.areaOptions[0]?.id ?? '')
  const [selectedTemplateIndex, setSelectedTemplateIndex] = useState<number>(0)

  useEffect(() => {
    onChanged?.({ ...payload, config })
  }, [config, onChanged])

  const overviewRows = useMemo(() => {
    const rows = payload.overviewRows
    return rows.map((row) => {
      const area = config.normal_areas?.[row.area_id] ?? {}
      return {
        ...row,
        区域名称: area.name ?? row['区域名称'],
        默认连续历练: Boolean(area.default_continuous),
      }
    })
  }, [config, payload.overviewRows])

  const handleOverviewChange = (rows: Record<string, any>[]) => {
    const next = cloneDeep(config)
    rows.forEach((row) => {
      const areaId = String(row.area_id)
      const area = next.normal_areas?.[areaId]
      if (!area) return
      area.name = row['区域名称']
      area.default_continuous = Boolean(row['默认连续历练'])
    })
    setConfig(next)
  }

  const selectedArea = config.normal_areas?.[selectedAreaId]
  const templateRows = useMemo(() => {
    const templates = selectedArea?.enemies_template ?? []
    return templates.map((template: any, index: number) => {
      const enemy = template.enemies?.[0] ?? {}
      const templateId = String(enemy.template ?? '')
      return {
        序号: index + 1,
        敌人模板: templateId,
        敌人名称: payload.enemyNameMap[templateId] ?? templateId,
        等级下限: Number(enemy.min_level ?? 1),
        等级上限: Number(enemy.max_level ?? 1),
        权重: Number(template.weight ?? 0),
      }
    })
  }, [selectedArea, payload.enemyNameMap])

  const currentTemplate = selectedArea?.enemies_template?.[selectedTemplateIndex]
  const dropRows = useMemo(() => {
    const drops = currentTemplate?.drops ?? {}
    return Object.entries(drops).map(([itemId, info]: [string, any]) => ({
      item_id: itemId,
      掉落名称: payload.itemNameMap[itemId] ?? itemId,
      min: Number(info.min ?? 0),
      max: Number(info.max ?? 0),
      chance: Number(info.chance ?? 1),
    }))
  }, [currentTemplate, payload.itemNameMap])

  const handleTemplateChange = (rows: Record<string, any>[]) => {
    const next = cloneDeep(config)
    const area = next.normal_areas?.[selectedAreaId]
    if (!area) return
    area.enemies_template = rows.map((row) => ({
      enemies: [{
        template: row['敌人模板'],
        min_level: Number(row['等级下限']),
        max_level: Number(row['等级上限']),
      }],
      weight: Number(row['权重']),
      drops: cloneDeep(area.enemies_template?.[Number(row['序号']) - 1]?.drops ?? {}),
    }))
    setConfig(next)
  }

  const handleDropChange = (rows: Record<string, any>[]) => {
    const next = cloneDeep(config)
    const template = next.normal_areas?.[selectedAreaId]?.enemies_template?.[selectedTemplateIndex]
    if (!template) return
    template.drops = {}
    rows.forEach((row) => {
      if (!row.item_id) return
      template.drops[String(row.item_id)] = {
        min: Number(row.min),
        max: Number(row.max),
        chance: Number(row.chance),
      }
    })
    setConfig(next)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const next = await saveAreas(config)
      setConfig(next.config)
      onSaved(next)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <h2>历练区域配置（areas）</h2>
        <p>保留 normal_areas 的总表 + 区域明细 + 敌人池掉落三层编辑结构。</p>
      </header>
      <section className="card">
        <EditableTable
          columns={[
            { key: 'area_id', label: 'area_id', readOnly: true, width: '130px' },
            { key: '区域名称', label: '区域名称' },
            { key: '默认连续历练', label: '默认连续历练', type: 'checkbox' },
            { key: '敌人池数量', label: '敌人池数量', readOnly: true },
            { key: '权重总和', label: '权重总和', readOnly: true },
            { key: '敌人等级范围', label: '敌人等级范围', readOnly: true },
            { key: '掉落种类', label: '掉落种类', readOnly: true, width: '260px' },
            { key: '理论最大灵石掉落效率（每小时）', label: '理论最大灵石掉落效率（每小时）', readOnly: true },
          ]}
          rows={overviewRows}
          onChange={handleOverviewChange}
        />
      </section>
      {selectedArea ? (
        <>
          <section className="card card-grid two-up align-start">
            <label className="field">
              <span>选择区域</span>
              <select value={selectedAreaId} onChange={(e) => { setSelectedAreaId(e.target.value); setSelectedTemplateIndex(0) }}>
                {payload.areaOptions.map((option) => <option key={option.id} value={option.id}>{option.name}（{option.id}）</option>)}
              </select>
            </label>
            <label className="field">
              <span>区域描述</span>
              <textarea value={selectedArea.description ?? ''} rows={4} onChange={(e) => {
                const next = cloneDeep(config)
                next.normal_areas[selectedAreaId].description = e.target.value
                setConfig(next)
              }} />
            </label>
          </section>
          <section className="card">
            <h3>敌人池</h3>
            <EditableTable
              columns={[
                { key: '序号', label: '序号', readOnly: true },
                { key: '敌人模板', label: '敌人模板', type: 'select', options: Object.entries(payload.enemyNameMap).map(([value, label]) => ({ value, label: `${label}（${value}）` })) },
                { key: '敌人名称', label: '敌人名称', readOnly: true },
                { key: '等级下限', label: '等级下限', type: 'number', min: 1 },
                { key: '等级上限', label: '等级上限', type: 'number', min: 1 },
                { key: '权重', label: '权重', type: 'number', min: 0 },
              ]}
              rows={templateRows}
              onChange={handleTemplateChange}
            />
          </section>
          <section className="card">
            <div className="actions-row">
              <h3>掉落编辑</h3>
              <select value={selectedTemplateIndex} onChange={(e) => setSelectedTemplateIndex(Number(e.target.value))}>
                {(selectedArea.enemies_template ?? []).map((template: any, index: number) => {
                  const enemy = template.enemies?.[0] ?? {}
                  const templateId = String(enemy.template ?? '')
                  return <option key={index} value={index}>第{index + 1}条：{payload.enemyNameMap[templateId] ?? templateId}</option>
                })}
              </select>
            </div>
            <EditableTable
              columns={[
                { key: 'item_id', label: 'item_id', type: 'select', options: Object.entries(payload.itemNameMap).map(([value, label]) => ({ value, label: `${label}（${value}）` })) },
                { key: '掉落名称', label: '掉落名称', readOnly: true },
                { key: 'min', label: '最小数量', type: 'number', min: 0 },
                { key: 'max', label: '最大数量', type: 'number', min: 0 },
                { key: 'chance', label: '概率', type: 'number', min: 0, max: 1, step: 0.05 },
              ]}
              rows={dropRows}
              onChange={handleDropChange}
            />
          </section>
        </>
      ) : null}
      <div className="actions-row"><button type="button" className="primary-btn" onClick={handleSave} disabled={saving}>{saving ? '保存中...' : '保存 areas 配置'}</button></div>
    </div>
  )
}
