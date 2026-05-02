import { useEffect, useMemo, useState } from 'react'
import { getAreas, getEnemies, getPages, getRealms, getRecipes, getSpells } from './api.js'
import { Sidebar } from './components/Sidebar.js'
import { AreasPage } from './pages/AreasPage.js'
import { BattlePage } from './pages/BattlePage.js'
import { CultivationPage } from './pages/CultivationPage.js'
import { EnemiesPage } from './pages/EnemiesPage.js'
import { RealmsPage } from './pages/RealmsPage.js'
import { RecipesPage } from './pages/RecipesPage.js'
import { SpellsPage } from './pages/SpellsPage.js'
import type { AppDrafts } from './types.js'
import { cloneDeep, stableStringify } from './utils.js'

const initialDrafts: AppDrafts = {
  pages: [],
  realms: null,
  recipes: null,
  enemies: null,
  areas: null,
  spells: null,
}

function App() {
  const [drafts, setDrafts] = useState<AppDrafts>(initialDrafts)
  const [baselineDrafts, setBaselineDrafts] = useState<AppDrafts>(initialDrafts)
  const [currentPage, setCurrentPage] = useState('cultivation')
  const [loading, setLoading] = useState(true)
  const [draftRevision, setDraftRevision] = useState(0)

  const loadAll = async () => {
    setLoading(true)
    try {
      const [pages, realms, recipes, enemies, areas, spells] = await Promise.all([
        getPages(),
        getRealms(),
        getRecipes(),
        getEnemies(),
        getAreas(),
        getSpells(),
      ])
      const next = { pages, realms, recipes, enemies, areas, spells }
      setDrafts(next)
      setBaselineDrafts(cloneDeep(next))
      setDraftRevision((prev) => prev + 1)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadAll()
  }, [])

  const ready = useMemo(() => drafts.realms && drafts.recipes && drafts.enemies && drafts.areas && drafts.spells, [drafts])
  const hasUnsavedChanges = useMemo(
    () => stableStringify(drafts) !== stableStringify(baselineDrafts),
    [drafts, baselineDrafts],
  )

  const discardUnsavedChanges = () => {
    setDrafts(cloneDeep(baselineDrafts))
    setDraftRevision((prev) => prev + 1)
  }

  let content = <div className="empty-state">正在加载数值模型...</div>
  if (ready) {
    if (currentPage === 'realms') {
      content = (
        <RealmsPage
          key={`realms-${draftRevision}`}
          payload={drafts.realms!}
          onChanged={(next) => setDrafts((prev) => ({ ...prev, realms: next }))}
          onSaved={(next) => setDrafts((prev) => ({ ...prev, realms: next }))}
        />
      )
    } else if (currentPage === 'recipes') {
      content = (
        <RecipesPage
          key={`recipes-${draftRevision}`}
          payload={drafts.recipes!}
          onChanged={(next) => setDrafts((prev) => ({ ...prev, recipes: next }))}
          onSaved={(next) => setDrafts((prev) => ({ ...prev, recipes: next }))}
        />
      )
    } else if (currentPage === 'enemies') {
      content = (
        <EnemiesPage
          key={`enemies-${draftRevision}`}
          payload={drafts.enemies!}
          onChanged={(next) => setDrafts((prev) => ({ ...prev, enemies: next }))}
          onSaved={(next) => setDrafts((prev) => ({ ...prev, enemies: next }))}
        />
      )
    } else if (currentPage === 'areas') {
      content = (
        <AreasPage
          key={`areas-${draftRevision}`}
          payload={drafts.areas!}
          onChanged={(next) => setDrafts((prev) => ({ ...prev, areas: next }))}
          onSaved={(next) => setDrafts((prev) => ({ ...prev, areas: next }))}
        />
      )
    } else if (currentPage === 'spells') {
      content = (
        <SpellsPage
          key={`spells-${draftRevision}`}
          payload={drafts.spells!}
          onChanged={(next) => setDrafts((prev) => ({ ...prev, spells: next }))}
          onSaved={(next) => setDrafts((prev) => ({ ...prev, spells: next }))}
        />
      )
    } else if (currentPage === 'battle') {
      content = <BattlePage realms={drafts.realms!} areas={drafts.areas!} enemies={drafts.enemies!} />
    } else {
      content = <CultivationPage realms={drafts.realms!} recipes={drafts.recipes!} areas={drafts.areas!} enemies={drafts.enemies!} />
    }
  }

  return (
    <div className="app-shell">
      <Sidebar pages={drafts.pages} current={currentPage} onChange={setCurrentPage} />
      <main className="main-shell">
        <div className="topbar">
          <div>
            <h1>修仙数值模型</h1>
            <p>放弃未保存修改会恢复到当前本地 data 文件状态，不会改动已保存的本地配置。</p>
          </div>
          <div className="topbar__actions">
            <button type="button" onClick={discardUnsavedChanges} disabled={loading || !hasUnsavedChanges}>
              {loading ? '读取中...' : '放弃未保存修改'}
            </button>
          </div>
        </div>
        {content}
      </main>
    </div>
  )
}

export default App
