import { renderCompareValue } from '../utils.js'

export function MetricCard({ label, baseValue, draftValue }: { label: string; baseValue: unknown; draftValue: unknown }) {
  const { same, baseText, draftText } = renderCompareValue(baseValue, draftValue)
  return (
    <div className="metric-card metric-card--plain">
      <div className="metric-card__label">{label}</div>
      <div className="metric-card__value">
        {same ? (
          <span className="compare-inline compare-inline--same">{draftText}</span>
        ) : (
          <span className="compare-inline">
            <span className="compare-inline__before">{baseText}</span>
            <span className="compare-inline__arrow">→</span>
            <span className="compare-inline__after">{draftText}</span>
          </span>
        )}
      </div>
    </div>
  )
}
