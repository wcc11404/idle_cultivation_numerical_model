import type { PageMeta } from '../types.js'

export function Sidebar({ pages, current, onChange }: { pages: PageMeta[]; current: string; onChange: (key: string) => void }) {
  const groups = pages.reduce<Record<string, PageMeta[]>>((acc, page) => {
    acc[page.group] ||= []
    acc[page.group].push(page)
    return acc
  }, {})

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <h1>数值模型</h1>
        <p>本地数值配置工具</p>
      </div>
      {Object.entries(groups).map(([group, items]) => (
        <section key={group} className="sidebar__group">
          <div className="sidebar__title">{group}</div>
          {items.map((page) => (
            <button
              key={page.key}
              type="button"
              className={page.key === current ? 'sidebar__item sidebar__item--active' : 'sidebar__item'}
              onClick={() => onChange(page.key)}
            >
              {page.label.replace('可视化', '')}
            </button>
          ))}
        </section>
      ))}
    </aside>
  )
}
