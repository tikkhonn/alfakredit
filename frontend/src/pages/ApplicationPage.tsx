import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { OfferPreview } from '../components/OfferPreview'
import { PipelineTrace } from '../components/PipelineTrace'
import { api, type Application } from '../lib/api'
import { useAuth } from '../lib/auth'
import { PRODUCT_LABEL, PURPOSE_LABEL, STATUS_TONE, dateTime, rub } from '../lib/format'

export function ApplicationPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { refresh } = useAuth()
  const [item, setItem] = useState<Application | null>(null)
  const [code, setCode] = useState('')
  const [details, setDetails] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [preview, setPreview] = useState(false)
  const [replay, setReplay] = useState<Application | null>(null)

  async function load() {
    if (!id) return
    const data = await api.application(id)
    setItem(data)
    setDetails(data.purpose_details || '')
  }

  useEffect(() => {
    load().catch(() => navigate('/'))
  }, [id])

  async function run(action: () => Promise<Application>, withTrace = false) {
    setBusy(true)
    setError('')
    try {
      const updated = await action()
      if (withTrace && updated.pipeline?.length) {
        setReplay(updated)
      } else {
        setItem(updated)
        setDetails(updated.purpose_details || details)
      }
      if (updated.status === 'issued') await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка')
    } finally {
      setBusy(false)
    }
  }

  if (replay) {
    return (
      <div className="fade-up mx-auto max-w-xl rounded-3xl border border-white/8 p-8">
        <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">{replay.public_number}</p>
        <h1 className="display mt-2 text-4xl">Считаем заново</h1>
        <div className="mt-8">
          <PipelineTrace
            steps={replay.pipeline}
            onDone={() => {
              setItem(replay)
              setReplay(null)
            }}
          />
        </div>
      </div>
    )
  }

  if (!item) return <div className="text-muted-foreground">Загружаем заявку…</div>

  return (
    <div className="fade-up grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
      <div>
        <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">{item.public_number}</p>
        <h1 className="display mt-2 text-5xl">
          {PURPOSE_LABEL[item.purpose]}
          <span className="text-muted-foreground"> · {PRODUCT_LABEL[item.product]}</span>
        </h1>
        <p className={`mt-4 text-lg ${STATUS_TONE[item.status]}`}>{item.status_label}</p>
        {item.client_message && item.status !== 'issued' ? (
          <p className="mt-4 max-w-xl text-muted-foreground">{item.client_message}</p>
        ) : null}
        {item.purpose_details ? <p className="mt-3 text-sm text-muted-foreground">Цель: {item.purpose_details}</p> : null}

        <dl className="mt-8 grid grid-cols-2 gap-4 rounded-3xl border border-white/8 p-6">
          <div>
            <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Запрос</dt>
            <dd className="mt-1 text-xl">{rub(item.requested_amount)}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Срок</dt>
            <dd className="mt-1 text-xl">{item.requested_term_months} мес.</dd>
          </div>
          {item.offer_amount ? (
            <>
              <div>
                <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Предложение</dt>
                <dd className="mt-1 text-xl">{rub(item.offer_amount)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Ставка</dt>
                <dd className="mt-1 text-xl">{item.offer_rate}%</dd>
              </div>
              {item.monthly_payment ? (
                <div className="col-span-2">
                  <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Платёж в месяц</dt>
                  <dd className="mt-1 text-xl">{rub(item.monthly_payment)}</dd>
                </div>
              ) : null}
            </>
          ) : null}
        </dl>

        {item.available_actions.includes('submit_extra') && (
          <div className="mt-6 rounded-3xl border border-warn/40 p-6">
            <h2 className="display text-2xl">Нужно уточнение</h2>
            <p className="mt-2 text-sm text-muted-foreground">{item.extra_comment}</p>
            <textarea
              className="mt-4 w-full rounded-2xl border border-white/10 bg-background px-4 py-3"
              rows={3}
              value={details}
              onChange={(event) => setDetails(event.target.value)}
            />
            <button
              disabled={busy}
              onClick={() => id && run(() => api.extra(id, { purpose_details: details }), true)}
              className="mt-4 rounded-full bg-primary px-5 py-2 text-primary-foreground"
            >
              Отправить уточнение
            </button>
          </div>
        )}

        {item.available_actions.includes('what_if') && (
          <div className="mt-6 rounded-3xl border border-warn/40 p-6">
            <h2 className="display text-2xl">Как взять запрошенную сумму?</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Сейчас банк предлагает меньше, чем вы просили. Можно показать обороты в другом банке или снизить риск залогом.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                disabled={busy}
                onClick={() => id && run(() => api.whatIf(id, 'other_bank'), true)}
                className="rounded-full bg-primary px-5 py-2 text-primary-foreground"
              >
                Выписка из другого банка
              </button>
              <button
                disabled={busy}
                onClick={() => id && run(() => api.whatIf(id, 'msp_collateral'), true)}
                className="rounded-full border border-white/15 px-5 py-2"
              >
                Залог / поручительство МСП
              </button>
            </div>
          </div>
        )}

        {item.available_actions.includes('cure') && (
          <div className="mt-6 rounded-3xl border border-primary/40 p-6">
            <h2 className="display text-2xl">Сначала налоги</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Пока есть недоимка, кредит недоступен. В демо можно смоделировать погашение — заявка останется той же.
            </p>
            <button
              disabled={busy}
              onClick={() => id && run(() => api.cure(id), true)}
              className="mt-4 rounded-full bg-primary px-5 py-2 text-primary-foreground"
            >
              Смоделировать погашение налога
            </button>
          </div>
        )}

        {item.available_actions.includes('accept') && (
          <div className="mt-6 rounded-3xl border border-ok/30 p-6">
            <h2 className="display text-2xl">Принять условия</h2>
            <p className="mt-2 text-muted-foreground">
              {rub(item.offer_amount)} на {item.offer_term_months} мес. под {item.offer_rate}%
              {item.monthly_payment ? `, около ${rub(item.monthly_payment)} в месяц` : ''}.
            </p>
            <div className="mt-5 flex gap-3">
              <button
                disabled={busy}
                onClick={() => id && run(() => api.accept(id))}
                className="rounded-full bg-primary px-5 py-2 text-primary-foreground"
              >
                Принимаю
              </button>
              <button
                disabled={busy}
                onClick={() => id && run(() => api.decline(id))}
                className="rounded-full border border-white/15 px-5 py-2"
              >
                Отказаться
              </button>
            </div>
          </div>
        )}

        {item.available_actions.includes('sign') && (
          <div className="mt-6 rounded-3xl border border-white/8 p-6">
            <h2 className="display text-2xl">Подписание</h2>
            <p className="mt-2 text-sm text-muted-foreground">Код внутри кабинета — заглушка ДБО. Для демо: 123456.</p>
            {item.available_actions.includes('preview') ? (
              <button onClick={() => setPreview(true)} className="mt-4 text-sm text-primary">
                Условия и график платежей
              </button>
            ) : null}
            <div className="mt-4 flex items-center gap-3">
              <input
                className="w-40 rounded-2xl border border-white/10 bg-background px-4 py-3 tracking-[0.4em]"
                value={code}
                onChange={(event) => setCode(event.target.value)}
                placeholder="123456"
              />
              <button
                disabled={busy}
                onClick={() => id && run(() => api.sign(id, code))}
                className="rounded-full bg-primary px-5 py-2 text-primary-foreground"
              >
                Подписать
              </button>
            </div>
          </div>
        )}

        {error ? <p className="mt-4 text-primary">{error}</p> : null}
        {item.status === 'issued' ? (
          <div className="mt-6 rounded-3xl bg-ok/10 p-6 text-ok">Выдача смоделирована. Проводок в АБС нет.</div>
        ) : null}
      </div>

      <aside className="space-y-6">
        {item.pipeline.length ? (
          <div className="rounded-3xl border border-white/8 p-6">
            <h2 className="display text-xl">Проверки</h2>
            <ol className="mt-4 space-y-3 text-sm">
              {item.pipeline.map((step) => (
                <li key={step.code} className="flex justify-between gap-3">
                  <span>
                    {step.title}
                    <span className="block text-xs text-muted-foreground">{step.detail}</span>
                  </span>
                  <span className="text-muted-foreground">{step.ms} мс</span>
                </li>
              ))}
            </ol>
          </div>
        ) : null}
        <div className="rounded-3xl border border-white/8 p-6">
          <h2 className="display text-xl">Как шла заявка</h2>
          <ol className="mt-6 space-y-5">
            {item.events.map((event, index) => (
              <li key={event.id} className="relative pl-6">
                <span className="absolute left-0 top-1.5 h-2 w-2 rounded-full bg-primary" />
                {index < item.events.length - 1 ? <span className="absolute left-[3px] top-4 h-full w-px bg-white/10" /> : null}
                <div className="text-sm">{event.message}</div>
                <div className="text-xs text-muted-foreground">{dateTime(event.at)}</div>
              </li>
            ))}
          </ol>
        </div>
      </aside>
      {preview ? <OfferPreview item={item} onClose={() => setPreview(false)} /> : null}
    </div>
  )
}
