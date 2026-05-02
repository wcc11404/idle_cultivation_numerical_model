import { useEffect, useState } from 'react'
import { getCultivationPreview } from '../api.js'
import { CompareTable } from '../components/CompareTable.js'
import { MetricCard } from '../components/MetricCard.js'
import type { AreasPayload, EnemiesPayload, RealmsPayload, RecipesPayload } from '../types.js'

export function CultivationPage({ realms, recipes, areas, enemies }: { realms: RealmsPayload; recipes: RecipesPayload; areas: AreasPayload; enemies: EnemiesPayload }) {
  const [preview, setPreview] = useState<any | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      setLoading(true)
      try {
        const next = await getCultivationPreview({
          realmsEditor: realms.editor,
          recipeRows: recipes.rows,
          areasConfig: areas.config,
          enemyRows: enemies.rows,
        })
        if (!cancelled) setPreview(next)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [realms.editor, recipes.rows, areas.config, enemies.rows])

  return (
    <div className="page-stack">
      <header className="page-header">
        <h2>修炼建模可视化</h2>
        <p>直接在数值上展示基础配置与草稿配置的前后变化；相同则显示单值，不同则显示 X → Y。</p>
      </header>
      {loading || !preview ? <div className="card">正在计算预览...</div> : (
        <>
          <section className="metrics-grid">
            <MetricCard label="破境草 / 天" baseValue={preview.metrics.base_foundation_herb_per_day} draftValue={preview.metrics.draft_foundation_herb_per_day} />
            <MetricCard label="总灵气耗时（天）" baseValue={preview.metrics.base_total_spirit_days} draftValue={preview.metrics.draft_total_spirit_days} />
            <MetricCard label="总材料耗时（天）" baseValue={preview.metrics.base_total_material_days} draftValue={preview.metrics.draft_total_material_days} />
          </section>
          <CompareTable title="大境界耗时汇总（Max）" baseRows={preview.realmSummary.base} draftRows={preview.realmSummary.draft} />
          <CompareTable title="升级明细" baseRows={preview.upgradeDetail.base} draftRows={preview.upgradeDetail.draft} />
        </>
      )}
    </div>
  )
}
