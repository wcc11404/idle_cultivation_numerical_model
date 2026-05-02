import { fmt } from '../utils.js'

export type TableColumn = {
  key: string
  label: string
  type?: 'text' | 'number' | 'checkbox' | 'select'
  readOnly?: boolean
  options?: Array<{ value: string; label: string }>
  min?: number
  max?: number
  step?: number
  width?: string
}

export function EditableTable({
  columns,
  rows,
  onChange,
}: {
  columns: TableColumn[]
  rows: Record<string, any>[]
  onChange: (rows: Record<string, any>[]) => void
}) {
  const updateCell = (rowIndex: number, key: string, value: any) => {
    const next = rows.map((row, index) => (index === rowIndex ? { ...row, [key]: value } : row))
    onChange(next)
  }

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} style={column.width ? { width: column.width } : undefined}>{column.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {columns.map((column) => {
                const value = row[column.key]
                if (column.readOnly) {
                  return <td key={column.key}>{fmt(value)}</td>
                }
                if (column.type === 'checkbox') {
                  return (
                    <td key={column.key}>
                      <input type="checkbox" checked={Boolean(value)} onChange={(e) => updateCell(rowIndex, column.key, e.target.checked)} />
                    </td>
                  )
                }
                if (column.type === 'select') {
                  return (
                    <td key={column.key}>
                      <select value={String(value ?? '')} onChange={(e) => updateCell(rowIndex, column.key, e.target.value)}>
                        {(column.options ?? []).map((option) => (
                          <option key={option.value} value={option.value}>{option.label}</option>
                        ))}
                      </select>
                    </td>
                  )
                }
                if (column.type === 'number') {
                  return (
                    <td key={column.key}>
                      <input
                        type="number"
                        value={value ?? ''}
                        min={column.min}
                        max={column.max}
                        step={column.step ?? 1}
                        onChange={(e) => updateCell(rowIndex, column.key, e.target.value === '' ? '' : Number(e.target.value))}
                      />
                    </td>
                  )
                }
                return (
                  <td key={column.key}>
                    <input type="text" value={String(value ?? '')} onChange={(e) => updateCell(rowIndex, column.key, e.target.value)} />
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
