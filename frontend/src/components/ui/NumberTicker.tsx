import { useEffect, useState } from 'react'

type Props = {
  value: number
  className?: string
  prefix?: string
  suffix?: string
  duration?: number
}

export function NumberTicker({ value, className, prefix = '', suffix = '', duration = 1.1 }: Props) {
  const [n, setN] = useState(0)

  useEffect(() => {
    let frame = 0
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / (duration * 1000))
      const eased = 1 - (1 - t) ** 3
      const next = eased * value
      setN(Number.isInteger(value) ? Math.round(next) : Math.round(next * 100) / 100)
      if (t < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [duration, value])

  return (
    <span className={className}>
      {prefix}
      <span className="tabular-nums">
        {new Intl.NumberFormat('ru-RU', {
          maximumFractionDigits: Number.isInteger(value) ? 0 : 2,
        }).format(n)}
      </span>
      {suffix}
    </span>
  )
}
