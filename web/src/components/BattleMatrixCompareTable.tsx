import { renderCompareValue } from '../utils.js'

type MatrixRow = {
  境界: string
  当前境界最大灵石掉落数量: string
  区域: string
  平均战斗次数: string
  平均战斗效率: string
  灵石掉落数量: string
}

function buildGroups(rows: MatrixRow[]) {
  const rowspans = new Map<string, number>()
  rows.forEach((row) => {
    rowspans.set(row.境界, (rowspans.get(row.境界) ?? 0) + 1)
  })
  return rowspans
}

export function BattleMatrixCompareTable({
  title,
  baseRows,
  draftRows,
}: {
  title: string
  baseRows: MatrixRow[]
  draftRows: MatrixRow[]
}) {
  const maxRows = Math.max(baseRows.length, draftRows.length)
  const displayRows: MatrixRow[] = Array.from({ length: maxRows }).map((_, index) => draftRows[index] ?? baseRows[index])
  const rowspans = buildGroups(displayRows)
  const renderedGroup = new Set<string>()

  return (
    <section className="card">
      <h3>{title}</h3>
      <div className="table-wrap">
        <table className="data-table compare-table compare-table--single">
          <thead>
            <tr>
              <th className="compare-table__cell">境界</th>
              <th className="compare-table__cell">当前境界最大灵石掉落数量</th>
              <th className="compare-table__cell">区域</th>
              <th className="compare-table__cell">平均战斗次数</th>
              <th className="compare-table__cell">平均战斗效率</th>
              <th className="compare-table__cell">灵石掉落数量</th>
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: maxRows }).map((_, index) => {
              const baseRow = baseRows[index] ?? ({} as MatrixRow)
              const draftRow = draftRows[index] ?? ({} as MatrixRow)
              const current = displayRows[index]
              return (
                <tr key={`${current?.境界 ?? 'row'}-${index}`}>
                  {!renderedGroup.has(current.境界) ? (
                    (() => {
                      renderedGroup.add(current.境界)
                      const compare = renderCompareValue(baseRow.当前境界最大灵石掉落数量, draftRow.当前境界最大灵石掉落数量)
                      return (
                        <>
                          <td rowSpan={rowspans.get(current.境界) ?? 1} className="compare-table__cell compare-table__cell--merged">
                            {current.境界}
                          </td>
                          <td rowSpan={rowspans.get(current.境界) ?? 1} className="compare-table__cell compare-table__cell--merged">
                            {compare.same ? (
                              <span className="compare-inline compare-inline--same">{compare.draftText}</span>
                            ) : (
                              <span className="compare-inline">
                                <span className="compare-inline__before">{compare.baseText}</span>
                                <span className="compare-inline__arrow">→</span>
                                <span className="compare-inline__after">{compare.draftText}</span>
                              </span>
                            )}
                          </td>
                        </>
                      )
                    })()
                  ) : null}
                  {(['区域', '平均战斗次数', '平均战斗效率', '灵石掉落数量'] as const).map((column) => {
                    const compare = renderCompareValue(baseRow[column], draftRow[column])
                    return (
                      <td key={column} className="compare-table__cell">
                        {compare.same ? (
                          <span className="compare-inline compare-inline--same">{compare.draftText}</span>
                        ) : (
                          <span className="compare-inline">
                            <span className="compare-inline__before">{compare.baseText}</span>
                            <span className="compare-inline__arrow">→</span>
                            <span className="compare-inline__after">{compare.draftText}</span>
                          </span>
                        )}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
