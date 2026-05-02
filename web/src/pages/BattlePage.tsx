import { useEffect, useMemo, useState } from 'react'
import { getBattlePreview } from '../api.js'
import { BattleMatrixCompareTable } from '../components/BattleMatrixCompareTable.js'
import { CompareTable } from '../components/CompareTable.js'
import { MetricCard } from '../components/MetricCard.js'
import { formatModelNumber } from '../utils.js'
import type { AreasPayload, EnemiesPayload, RealmsPayload } from '../types.js'

export function BattlePage({ realms, areas, enemies }: { realms: RealmsPayload; areas: AreasPayload; enemies: EnemiesPayload }) {
  const realmNames = realms.config?.realm_order ?? []
  const [realmName, setRealmName] = useState<string>(realmNames[0] ?? '炼气期')
  const [level, setLevel] = useState<number>(1)
  const [areaId, setAreaId] = useState<string>(areas.areaOptions[0]?.id ?? '')
  const [preview, setPreview] = useState<any | null>(null)

  const maxLevel = useMemo(() => Number(realms.config?.realms?.[realmName]?.max_level ?? 1), [realms.config, realmName])

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      const next = await getBattlePreview({
        realmsEditor: realms.editor,
        areasConfig: areas.config,
        enemyRows: enemies.rows,
        realm_name: realmName,
        level,
        area_id: areaId,
      })
      if (!cancelled) setPreview(next)
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [realms.editor, areas.config, enemies.rows, realmName, level, areaId])

  const normalizeMatrix = (rows: Record<string, any>[], rewards: Record<string, any>[]) => {
    const rewardMap = new Map<string, number>()
    const maxSpiritByRealm = new Map<string, number>()
    rewards.forEach((row) => {
      if (row.item_id === 'spirit_stone') {
        const rewardValue = Number(row.avg_per_hour ?? 0)
        rewardMap.set(`${row.realm_name}:${row.level}:${row.area_id}`, rewardValue)
        const realmKey = `${row.realm_name}${row.level}层`
        maxSpiritByRealm.set(realmKey, Math.max(maxSpiritByRealm.get(realmKey) ?? 0, rewardValue))
      }
    })
    return rows.map((row) => ({
      境界: `${row.realm_name}${row.level}层`,
      当前境界最大灵石掉落数量: formatModelNumber(maxSpiritByRealm.get(`${row.realm_name}${row.level}层`) ?? 0),
      区域: row.area_name,
      平均战斗次数: row.infinite_fights ? '♾️' : formatModelNumber(row.avg_fights),
      平均战斗效率: formatModelNumber(row.avg_fights_per_hour),
      灵石掉落数量: formatModelNumber(rewardMap.get(`${row.realm_name}:${row.level}:${row.area_id}`) ?? 0),
    }))
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <h2>战斗建模可视化</h2>
        <p>直接在数值上展示基础配置与草稿配置的前后变化；所有小数统一保留两位并去尾零。</p>
      </header>
      <section className="card card-grid three-up">
        <label className="field"><span>玩家大境界</span><select value={realmName} onChange={(e) => setRealmName(e.target.value)}>{realmNames.map((name: string) => <option key={name} value={name}>{name}</option>)}</select></label>
        <label className="field"><span>玩家层级</span><input type="number" min={1} max={maxLevel} value={level} onChange={(e) => setLevel(Number(e.target.value))} /></label>
        <label className="field"><span>普通历练区域</span><select value={areaId} onChange={(e) => setAreaId(e.target.value)}>{areas.areaOptions.map((option) => <option key={option.id} value={option.id}>{option.name}（{option.id}）</option>)}</select></label>
      </section>
      {!preview ? <div className="card">正在计算预览...</div> : (
        <>
          <section className="metrics-grid">
            <MetricCard label="平均战斗场次" baseValue={preview.custom?.base?.infinite_fights ? '♾️' : preview.custom?.base?.avg_fights} draftValue={preview.custom?.draft?.infinite_fights ? '♾️' : preview.custom?.draft?.avg_fights} />
            <MetricCard label="平均战斗效率（次/小时）" baseValue={preview.custom?.base?.avg_fights_per_hour} draftValue={preview.custom?.draft?.avg_fights_per_hour} />
            <MetricCard label="灵石掉落数量（每小时）" baseValue={preview.custom?.base?.avg_item_per_hour?.spirit_stone ?? 0} draftValue={preview.custom?.draft?.avg_item_per_hour?.spirit_stone ?? 0} />
          </section>
          <CompareTable title="破境草洞穴结果" baseRows={[preview.cave.base]} draftRows={[preview.cave.draft]} />
          <CompareTable title="南麓试练塔最大通关层" baseRows={preview.tower.base ?? []} draftRows={preview.tower.draft ?? []} />
          <BattleMatrixCompareTable title="普通历练矩阵" baseRows={normalizeMatrix(preview.matrix.base ?? [], preview.matrix.baseRewards ?? [])} draftRows={normalizeMatrix(preview.matrix.draft ?? [], preview.matrix.draftRewards ?? [])} />
        </>
      )}
    </div>
  )
}
