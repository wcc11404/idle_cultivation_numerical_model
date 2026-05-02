import { renderCompareValue } from '../utils.js'

export function CompareTable({
  title,
  baseRows,
  draftRows,
}: {
  title: string
  baseRows: Record<string, any>[]
  draftRows: Record<string, any>[]
}) {
  const columns = Array.from(new Set([...baseRows.flatMap(Object.keys), ...draftRows.flatMap(Object.keys)]))
  const maxRows = Math.max(baseRows.length, draftRows.length)

  return (
    <section className="card">
      <h3>{title}</h3>
      <div className="table-wrap">
        <table className="data-table compare-table compare-table--single">
          <thead>
            <tr>{columns.map((column) => <th key={column} className="compare-table__cell">{column}</th>)}</tr>
          </thead>
          <tbody>
            {Array.from({ length: maxRows }).map((_, index) => (
              <tr key={index}>
                {columns.map((column) => {
                  const compare = renderCompareValue(baseRows[index]?.[column], draftRows[index]?.[column])
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
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
