import { useEffect, useId, useRef } from 'react'

type Props = {
  value: number
  max?: number
  label?: string
}

export function ScoreGauge({ value, max = 100, label = 'скоринг' }: Props) {
  const strokeRef = useRef<SVGCircleElement>(null)
  const gradId = useId().replace(/:/g, '')
  const radius = 45
  const dist = 2 * Math.PI * radius
  const distHalf = dist / 2
  const strokeDasharray = `${distHalf} ${distHalf}`
  const offset = Math.min(value / max, 1) * -distHalf
  const band = value >= 75 ? 'strong' : value >= 60 ? 'good' : value >= 50 ? 'mid' : 'weak'
  const colors: Record<string, string[]> = {
    weak: ['#ef3124', '#d6544b'],
    mid: ['#e7c27d', '#d6544b'],
    good: ['#7dcea0', '#e7c27d'],
    strong: ['#7dcea0', '#4ad4a0'],
  }

  useEffect(() => {
    strokeRef.current?.animate(
      [{ strokeDashoffset: '0' }, { strokeDashoffset: String(offset) }],
      { duration: 1200, easing: 'cubic-bezier(0.65, 0, 0.35, 1)', fill: 'forwards' },
    )
  }, [offset])

  return (
    <div className="relative mx-auto w-56">
      <svg className="mx-auto h-36 w-full" viewBox="0 0 100 50" aria-hidden>
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="1" y2="0">
            {colors[band].map((color, index) => (
              <stop key={color} offset={`${index * 100}%`} stopColor={color} />
            ))}
          </linearGradient>
        </defs>
        <g fill="none" strokeWidth="8" transform="translate(50, 50.5)">
          <circle className="stroke-white/10" r={radius} />
          <circle
            ref={strokeRef}
            stroke={`url(#${gradId})`}
            strokeDasharray={strokeDasharray}
            r={radius}
            strokeLinecap="round"
          />
        </g>
      </svg>
      <div className="absolute inset-x-0 bottom-1 text-center">
        <div className="display text-4xl">{value}</div>
        <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">{label}</div>
      </div>
    </div>
  )
}
