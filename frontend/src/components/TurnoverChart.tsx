import { rub } from '../lib/format'

export function TurnoverChart({ values }: { values: number[] }) {
  if (!values.length) return null
  const max = Math.max(...values)
  const min = Math.min(...values)
  const width = 320
  const height = 120
  const pad = 8
  const points = values.map((value, index) => {
    const x = pad + (index / Math.max(values.length - 1, 1)) * (width - pad * 2)
    const y = height - pad - ((value - min) / Math.max(max - min, 1)) * (height - pad * 2)
    return `${x},${y}`
  })

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} className="h-28 w-full" aria-hidden>
        <polyline fill="none" stroke="#ef3124" strokeWidth="2.5" points={points.join(' ')} />
        {values.map((value, index) => {
          const [x, y] = points[index].split(',')
          return <circle key={value + index} cx={x} cy={y} r="3" fill="#f4f1ec" />
        })}
      </svg>
      <div className="mt-2 flex justify-between text-xs text-muted-foreground">
        <span>6 месяцев</span>
        <span>
          {rub(min)} — {rub(max)}
        </span>
      </div>
    </div>
  )
}
