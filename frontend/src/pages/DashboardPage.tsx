import { ArrowUpRight } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { NumberTicker } from '../components/ui/NumberTicker'
import { api, type Application } from '../lib/api'
import { useAuth } from '../lib/auth'
import { PRODUCT_LABEL, PURPOSE_LABEL, STATUS_TONE, dateTime, greeting, rub } from '../lib/format'

const INTENTS = [
  { code: 'cash_gap', title: 'Кассовый разрыв', text: 'Счёт уже выставили, оплата от покупателей придёт позже' },
  { code: 'restock', title: 'Закупка и оборот', text: 'Товар, сырьё или сезон — короткий цикл' },
  { code: 'growth', title: 'Рост и оборудование', text: 'Станки, ремонт, новая точка, долгий проект' },
]

export function DashboardPage() {
  const { me, refresh } = useAuth()
  const navigate = useNavigate()
  const [items, setItems] = useState<Application[]>([])
  const company = me?.company

  useEffect(() => {
    api.applications().then(setItems).catch(() => undefined)
    refresh().catch(() => undefined)
  }, [refresh])

  if (!company) return null

  return (
    <div className="fade-up space-y-10">
      <div>
        <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">{greeting()}</p>
        <h1 className="display mt-2 text-5xl">{company.short_name}</h1>
        <p className="mt-3 max-w-2xl text-muted-foreground">Обороты и реквизиты уже в банке. Осталось сказать, зачем деньги.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {[
          { label: 'Средний оборот', value: company.avg_turnover, suffix: ' ₽' },
          { label: 'Доступно в «Кассе»', value: company.kassa_limit, suffix: ' ₽' },
          { label: 'Заявок', value: items.length, suffix: '' },
        ].map((card, index) => (
          <div
            key={card.label}
            className="fade-up rounded-3xl border border-white/8 bg-linear-to-b from-white/6 to-transparent p-6 transition hover:border-white/16"
            style={{ animationDelay: `${index * 80}ms` }}
          >
            <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{card.label}</div>
            <NumberTicker value={card.value} suffix={card.suffix} className="display mt-4 block text-4xl" />
          </div>
        ))}
      </div>

      <div>
        <div className="mb-4 flex items-end justify-between">
          <h2 className="display text-2xl">Что случилось в бизнесе?</h2>
          <Link to="/new" className="text-sm text-primary">
            Новая заявка
          </Link>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {INTENTS.map((intent) => (
            <button
              key={intent.code}
              onClick={() => navigate(`/new?purpose=${intent.code}`)}
              className="group rounded-3xl border border-white/8 p-6 text-left transition hover:border-primary/50"
            >
              <div className="flex items-start justify-between">
                <div className="display text-xl">{intent.title}</div>
                <ArrowUpRight className="text-muted-foreground group-hover:text-primary" size={18} />
              </div>
              <p className="mt-3 text-sm text-muted-foreground">{intent.text}</p>
            </button>
          ))}
        </div>
      </div>

      <div>
        <h2 className="display mb-4 text-2xl">Заявки</h2>
        <div className="overflow-hidden rounded-3xl border border-white/8">
          {items.length === 0 ? (
            <div className="px-6 py-12 text-muted-foreground">Пока пусто. Начните с задачи бизнеса.</div>
          ) : (
            items.map((item) => (
              <Link
                key={item.id}
                to={`/applications/${item.id}`}
                className="grid grid-cols-[140px_1fr_160px_180px] items-center gap-4 border-b border-white/6 px-6 py-5 last:border-0 hover:bg-white/3"
              >
                <div className="font-medium">{item.public_number}</div>
                <div>
                  <div>
                    {PURPOSE_LABEL[item.purpose]} · {PRODUCT_LABEL[item.product]}
                  </div>
                  <div className="text-sm text-muted-foreground">{rub(item.requested_amount)}</div>
                </div>
                <div className={STATUS_TONE[item.status]}>{item.status_label}</div>
                <div className="text-right text-sm text-muted-foreground">{dateTime(item.created_at)}</div>
              </Link>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
