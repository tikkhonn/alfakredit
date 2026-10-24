import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { PipelineTrace } from '../components/PipelineTrace'
import { api, type Application, type Recommend } from '../lib/api'
import { useAuth } from '../lib/auth'
import { rub } from '../lib/format'

const PURPOSES = [
  { code: 'cash_gap', title: 'Кассовый разрыв', subtitle: 'Счёт уже выставили, оплата от покупателей придёт позже' },
  { code: 'restock', title: 'Закупка и оборот', subtitle: 'Товар, сырьё или сезон — короткий цикл' },
  { code: 'growth', title: 'Рост и оборудование', subtitle: 'Станки, ремонт, новая точка, долгий проект' },
]

const AMOUNT_STEP = 10_000

function snapAmount(value: number, min: number, max: number) {
  const rounded = Math.round(value / AMOUNT_STEP) * AMOUNT_STEP
  return Math.min(max, Math.max(min, rounded))
}

export function NewApplicationPage() {
  const { me } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const purposeFromUrl = params.get('purpose') || ''
  const [step, setStep] = useState(0)
  const [purpose, setPurpose] = useState(purposeFromUrl)
  const [product, setProduct] = useState('kassa')
  const [amount, setAmount] = useState(800000)
  const [term, setTerm] = useState(6)
  const [details, setDetails] = useState('')
  const [profileChanged, setProfileChanged] = useState(false)
  const [rec, setRec] = useState<Recommend | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [trace, setTrace] = useState<Application | null>(null)
  const company = me?.company

  useEffect(() => {
    if (!purpose) return
    api
      .recommend(purpose)
      .then((result) => {
        setRec(result)
        setProduct(result.product)
        setAmount(result.suggested_amount)
        setTerm(result.suggested_term_months)
        if (purposeFromUrl === purpose) setStep(1)
      })
      .catch(() => undefined)
  }, [purpose, purposeFromUrl])

  useEffect(() => {
    if (!purpose || step !== 1) return
    const timer = window.setTimeout(() => {
      api
        .recommend(purpose, amount, term)
        .then((result) => setRec((prev) => ({ ...result, product: prev?.product || result.product })))
        .catch(() => undefined)
    }, 220)
    return () => window.clearTimeout(timer)
  }, [amount, purpose, step, term])

  const override = rec && rec.product !== product
  const steps = useMemo(() => ['Цель', 'Условия', 'Профиль'], [])

  const finishTrace = useCallback(() => {
    if (trace) navigate(`/applications/${trace.id}`)
  }, [navigate, trace])

  async function submit() {
    setBusy(true)
    setError('')
    try {
      const created = await api.createApplication({
        purpose,
        product,
        requested_amount: amount,
        requested_term_months: term,
        purpose_details: details || null,
        profile_changed: profileChanged,
      })
      setTrace(created)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось отправить')
    } finally {
      setBusy(false)
    }
  }

  if (!company) return null

  if (trace) {
    return (
      <div className="fade-up mx-auto max-w-xl rounded-3xl border border-white/8 p-8">
        <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">{trace.public_number}</p>
        <h1 className="display mt-2 text-4xl">Проверяем заявку</h1>
        <p className="mt-3 text-muted-foreground">ЕГРЮЛ, ФНС и БКИ — моки, без живых бюро.</p>
        <div className="mt-8">
          <PipelineTrace steps={trace.pipeline} onDone={finishTrace} />
        </div>
      </div>
    )
  }

  return (
    <div className="fade-up mx-auto max-w-3xl">
      <div className="mb-8 flex gap-6">
        {steps.map((label, index) => (
          <div key={label} className="flex items-center gap-3 text-sm">
            <span
              className={`grid h-8 w-8 place-items-center rounded-full ${index === step ? 'bg-primary text-white' : 'border border-white/15 text-muted-foreground'}`}
            >
              {index + 1}
            </span>
            <span className={index === step ? 'text-foreground' : 'text-muted-foreground'}>{label}</span>
          </div>
        ))}
      </div>

      {step === 0 && (
        <div>
          <h1 className="display text-4xl">Зачем нужны деньги?</h1>
          <p className="mt-3 text-muted-foreground">Назовите задачу. Продукт подскажем сами.</p>
          <div className="mt-8 space-y-3">
            {PURPOSES.map((item) => (
              <button
                key={item.code}
                onClick={() => setPurpose(item.code)}
                className={`w-full rounded-3xl border px-6 py-5 text-left ${purpose === item.code ? 'border-primary bg-primary/8' : 'border-white/8'}`}
              >
                <div className="display text-2xl">{item.title}</div>
                <div className="mt-1 text-sm text-muted-foreground">{item.subtitle}</div>
              </button>
            ))}
          </div>
          <button
            disabled={!purpose}
            onClick={() => setStep(1)}
            className="mt-8 rounded-full bg-primary px-6 py-3 text-primary-foreground disabled:opacity-40"
          >
            Дальше
          </button>
        </div>
      )}

      {step === 1 && rec && (
        <div>
          <h1 className="display text-4xl">Вам подходит «{rec.product_name}»</h1>
          <p className="mt-3 text-muted-foreground">{rec.why}</p>
          <div className="mt-6 grid gap-3 md:grid-cols-2">
            <button
              onClick={() => setProduct('kassa')}
              className={`rounded-3xl border p-5 text-left ${product === 'kassa' ? 'border-primary' : 'border-white/8'}`}
            >
              <div className="display text-xl">Касса</div>
              <div className="mt-2 text-sm text-muted-foreground">
                Оборотный экспресс-кредит под поступления. Решение автоматом, если сумма в лимите.
              </div>
            </button>
            <button
              onClick={() => setProduct('razvitie')}
              className={`rounded-3xl border p-5 text-left ${product === 'razvitie' ? 'border-primary' : 'border-white/8'}`}
            >
              <div className="display text-xl">Развитие</div>
              <div className="mt-2 text-sm text-muted-foreground">Срок 12–36 мес. Смотрит кредитный специалист.</div>
            </button>
          </div>
          {override ? (
            <p className="mt-4 text-sm text-warn">
              Для этой задачи мы рекомендовали «{rec.product_name}». Другой продукт меняет маршрут заявки.
            </p>
          ) : null}
          <label className="mt-8 block text-xs uppercase tracking-[0.18em] text-muted-foreground">Сумма</label>
          <div className="mt-2 flex flex-wrap items-end gap-4">
            <div className="display text-4xl">{rub(amount)}</div>
            <input
              type="number"
              min={rec.min_amount}
              max={rec.max_amount}
              step={AMOUNT_STEP}
              value={amount}
              onChange={(event) => setAmount(snapAmount(Number(event.target.value), rec.min_amount, rec.max_amount))}
              className="w-40 rounded-2xl border border-white/10 bg-background px-3 py-2 text-sm"
            />
          </div>
          <input
            type="range"
            min={rec.min_amount}
            max={rec.max_amount}
            step={AMOUNT_STEP}
            value={amount}
            onChange={(event) => setAmount(Number(event.target.value))}
            className="mt-4 w-full accent-primary"
          />
          {rec.monthly_payment ? (
            <p className="mt-3 text-sm">
              Платёж около {rub(rec.monthly_payment)} в месяц
              {rec.indicative_rate ? ` при ставке ${rec.indicative_rate}%` : ''}.
            </p>
          ) : null}
          {rec.kassa_limit != null && product === 'kassa' ? (
            <p className="mt-2 text-sm text-muted-foreground">Сейчас доступно в «Кассе»: {rub(rec.kassa_limit)}</p>
          ) : null}
          <label className="mt-6 block text-xs uppercase tracking-[0.18em] text-muted-foreground">Срок, мес.</label>
          <input
            type="number"
            min={rec.min_term_months}
            max={rec.max_term_months}
            className="mt-2 w-32 rounded-2xl border border-white/10 bg-background px-4 py-3"
            value={term}
            onChange={(event) => setTerm(Number(event.target.value))}
          />
          {product === 'razvitie' ? (
            <>
              <label className="mt-6 block text-xs uppercase tracking-[0.18em] text-muted-foreground">На что пойдут деньги</label>
              <textarea
                className="mt-2 w-full rounded-2xl border border-white/10 bg-background px-4 py-3"
                rows={3}
                value={details}
                onChange={(event) => setDetails(event.target.value)}
                placeholder="Вторая печь, ремонт точки, оборудование…"
              />
            </>
          ) : null}
          <div className="mt-8 flex gap-3">
            <button onClick={() => setStep(0)} className="rounded-full border border-white/15 px-6 py-3">
              Назад
            </button>
            <button onClick={() => setStep(2)} className="rounded-full bg-primary px-6 py-3 text-primary-foreground">
              Подтвердить профиль
            </button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div>
          <h1 className="display text-4xl">Это уже есть в банке</h1>
          <p className="mt-3 text-muted-foreground">Реквизиты не перебиваем. Если что-то устарело — отметьте ниже.</p>
          <dl className="mt-8 grid gap-4 rounded-3xl border border-white/8 p-6 md:grid-cols-2">
            {[
              ['Компания', company.short_name],
              ['ИНН', company.inn],
              ['Форма', company.legal_form === 'ip' ? 'ИП' : 'ООО'],
              ['ОКВЭД', `${company.okved} · ${company.okved_name}`],
              ['В реестре с', company.registered_at],
              ['Оборот / мес.', rub(company.avg_turnover)],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</dt>
                <dd className="mt-1">{value}</dd>
              </div>
            ))}
          </dl>
          <label className="mt-6 flex items-start gap-3 rounded-2xl border border-white/8 p-4 text-sm">
            <input
              type="checkbox"
              className="mt-1 accent-primary"
              checked={profileChanged}
              onChange={(event) => setProfileChanged(event.target.checked)}
            />
            <span>Данные устарели, пусть посмотрит специалист</span>
          </label>
          {error ? <p className="mt-4 text-primary">{error}</p> : null}
          <div className="mt-8 flex gap-3">
            <button onClick={() => setStep(1)} className="rounded-full border border-white/15 px-6 py-3">
              Назад
            </button>
            <button
              disabled={busy}
              onClick={submit}
              className="rounded-full bg-primary px-6 py-3 text-primary-foreground disabled:opacity-50"
            >
              {busy ? 'Отправляем…' : 'Отправить заявку'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
