import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Application, type QueueStats } from '../lib/api'
import { PRODUCT_LABEL, PURPOSE_LABEL, STATUS_TONE, dateTime, rub } from '../lib/format'

export function SpecialistQueuePage() {
  const [pending, setPending] = useState(true)
  const [items, setItems] = useState<Application[]>([])
  const [stats, setStats] = useState<QueueStats | null>(null)

  useEffect(() => {
    api.specialistQueue(pending).then(setItems).catch(() => undefined)
    api.specialistStats().then(setStats).catch(() => undefined)
  }, [pending])

  return (
    <div className="fade-up">
      <div className="flex items-end justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Банк</p>
          <h1 className="display mt-2 text-5xl">Очередь решений</h1>
        </div>
        <div className="flex rounded-full border border-white/10 p-1">
          <button
            onClick={() => setPending(true)}
            className={`rounded-full px-4 py-2 text-sm ${pending ? 'bg-primary text-white' : 'text-muted-foreground'}`}
          >
            Нужно решение
          </button>
          <button
            onClick={() => setPending(false)}
            className={`rounded-full px-4 py-2 text-sm ${!pending ? 'bg-primary text-white' : 'text-muted-foreground'}`}
          >
            Все заявки
          </button>
        </div>
      </div>
      {stats ? (
        <p className="mt-4 text-sm text-muted-foreground">
          Автоконвейер {stats.auto_share == null ? '—' : `${stats.auto_share}%`}
          {' · '}
          вручную {stats.manual_count}
          {' · '}в очереди {stats.queue_size}
        </p>
      ) : null}

      <div className="mt-8 overflow-hidden rounded-3xl border border-white/8">
        {items.length === 0 ? (
          <div className="px-6 py-14 text-muted-foreground">
            {pending ? 'Пока никого. Чистые «Кассы» закрывает автоконвейер.' : 'Заявок ещё нет.'}
          </div>
        ) : (
          items.map((item) => (
            <Link
              key={item.id}
              to={`/bank/${item.id}`}
              className="grid grid-cols-[140px_1fr_160px_140px_160px] items-center gap-4 border-b border-white/6 px-6 py-5 last:border-0 hover:bg-white/3"
            >
              <div>{item.public_number}</div>
              <div>
                <div>{item.company?.short_name}</div>
                <div className="text-sm text-muted-foreground">
                  {PURPOSE_LABEL[item.purpose]} · {PRODUCT_LABEL[item.product]} · {rub(item.requested_amount)}
                </div>
              </div>
              <div className={STATUS_TONE[item.status]}>{item.status_label}</div>
              <div className="text-sm text-muted-foreground">{item.decided_by === 'system' ? 'система' : 'человек'}</div>
              <div className="text-right text-sm text-muted-foreground">{dateTime(item.updated_at)}</div>
            </Link>
          ))
        )}
      </div>
    </div>
  )
}
