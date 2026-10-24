import { useEffect, useRef, useState } from 'react'
import type { PipelineStep } from '../lib/api'

export function PipelineTrace({
  steps,
  onDone,
}: {
  steps: PipelineStep[]
  onDone?: () => void
}) {
  const [visible, setVisible] = useState(0)
  const doneRef = useRef(onDone)
  doneRef.current = onDone

  useEffect(() => {
    if (!steps.length) {
      doneRef.current?.()
      return
    }
    let index = 0
    let timer = 0
    const tick = () => {
      index += 1
      setVisible(index)
      if (index >= steps.length) {
        timer = window.setTimeout(() => doneRef.current?.(), 350)
        return
      }
      const wait = Math.min(420, 80 + steps[index - 1].ms)
      timer = window.setTimeout(tick, wait)
    }
    timer = window.setTimeout(tick, 80)
    return () => window.clearTimeout(timer)
  }, [steps])

  if (!steps.length) return null

  return (
    <ol className="space-y-3">
      {steps.map((step, index) => {
        const shown = index < visible
        const tone =
          step.status === 'timeout' || step.status === 'arrears' || step.status === 'fallback'
            ? 'text-warn'
            : 'text-ok'
        return (
          <li key={step.code} className={`flex items-start justify-between gap-4 text-sm ${shown ? 'opacity-100' : 'opacity-25'}`}>
            <div>
              <div className="font-medium">{step.title}</div>
              <div className="text-xs text-muted-foreground">{step.detail}</div>
            </div>
            <div className={`shrink-0 tabular-nums ${shown ? tone : 'text-muted-foreground'}`}>
              {shown ? `${step.ms} мс` : '…'}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
