import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { TurnoverChart } from '../components/TurnoverChart'
import { ScoreGauge } from '../components/ui/ScoreGauge'
import { api, type Application } from '../lib/api'
import { PRODUCT_LABEL, PURPOSE_LABEL, ageLabel, dateTime, registryStatus, rub, ruleLabel } from '../lib/format'

const AMOUNT_STEP = 10_000

export function SpecialistDossierPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [item, setItem] = useState<Application | null>(null)
  const [amount, setAmount] = useState(0)
  const [term, setTerm] = useState(12)
  const [rate, setRate] = useState(25.5)
  const [comment, setComment] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!id) return
    api
      .specialistDossier(id)
      .then((data) => {
        setItem(data)
        setAmount(data.offer_amount || data.requested_amount)
        setTerm(data.offer_term_months || data.requested_term_months)
        setRate(data.offer_rate || 25.5)
      })
      .catch(() => navigate('/bank'))
  }, [id, navigate])

  async function decide(action: string) {
    if (!id) return
    setBusy(true)
    setError('')
    try {
      const updated = await api.specialistDecide(id, {
        action,
        amount,
        term_months: term,
        rate_annual: rate,
        extra_fields: ['purpose_details'],
        extra_comment: comment.trim(),
        reject_reason: comment.trim(),
      })
      setItem(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка')
    } finally {
      setBusy(false)
    }
  }

  if (!item) return <div className="text-muted-foreground">Открываем досье…</div>
  const scoring = item.scoring
  const company = item.company
  const rules = ((item.policy?.rules as string[]) || []).map(ruleLabel).join(' → ')
  const enrichment = item.enrichment as {
    fns?: { tax_arrears: boolean; arrears_amount: number }
    bki?: { status?: string; overdue_days: number | null; current_debt: number | null; monthly_payment?: number | null }
    egrul?: { status: string }
  } | null
  const commentReady = comment.trim().length > 0
  const otherBank = item.extra_turnover || 0
  const turnoverSeries = (company?.turnovers || []).map((value) => value + otherBank)
  const baselineRate = item.offer_rate ?? 25.5
  const counterofferUnchanged =
    amount === item.requested_amount && term === item.requested_term_months && rate === baselineRate
  const bkiKnown = enrichment?.bki?.status !== 'timeout'
  const aboveKassaLimit = item.product === 'kassa' && company != null && amount > company.kassa_limit
  const weakDscr = item.dscr != null && item.dscr < 1

  return (
    <div className="fade-up grid gap-8 lg:grid-cols-[0.9fr_1.1fr]">
      <div className="space-y-6">
        <div>
          <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">{item.public_number}</p>
          <h1 className="display mt-2 text-4xl">{company?.short_name}</h1>
          <p className="mt-2 text-muted-foreground">
            {PURPOSE_LABEL[item.purpose]} · {PRODUCT_LABEL[item.product]} · {rub(item.requested_amount)} /{' '}
            {item.requested_term_months} мес.
          </p>
          {item.purpose_details ? <p className="mt-2 text-sm">Цель клиента: {item.purpose_details}</p> : null}
          {item.profile_note ? <p className="mt-2 text-sm">Что устарело: {item.profile_note}</p> : null}
        </div>
        {scoring ? <ScoreGauge value={scoring.total} /> : null}
        {company ? (
          <dl className="grid grid-cols-2 gap-3 rounded-3xl border border-white/8 p-5 text-sm">
            <div>
              <dt className="text-muted-foreground">ИНН</dt>
              <dd>{company.inn}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Возраст бизнеса</dt>
              <dd>{ageLabel(company.business_age_months)}</dd>
            </div>
            <div className="col-span-2">
              <dt className="text-muted-foreground">ОКВЭД</dt>
              <dd>
                {company.okved} · {company.okved_name}
              </dd>
            </div>
            <div className="col-span-2">
              <dt className="text-muted-foreground">Среднемесячный оборот</dt>
              <dd className="text-lg">
                {rub((company.avg_turnover || 0) + otherBank)}
                {otherBank ? <span className="mt-1 block text-sm text-muted-foreground">из другого банка {rub(otherBank)}</span> : null}
              </dd>
            </div>
          </dl>
        ) : null}
        {company?.turnovers?.length ? (
          <div className="rounded-3xl border border-white/8 p-5">
            <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Обороты, 6 месяцев</div>
            <div className="mt-3">
              <TurnoverChart values={turnoverSeries} />
            </div>
            {item.dscr != null ? (
              <p className="mt-3 text-sm">
                DSCR {item.dscr.toFixed(2)} — прибыль по ОКВЭД / (платёж по заявке
                {item.monthly_payment ? ` ${rub(item.monthly_payment)}` : ''} + платежи по выданным{' '}
                {rub(item.issued_monthly_payment)} + платёж БКИ{' '}
                {bkiKnown ? rub(enrichment?.bki?.monthly_payment) : 'Н/Д'}).
              </p>
            ) : null}
            {item.monthly_payment ? (
              <p className="text-sm text-muted-foreground">Платёж по запросу: {rub(item.monthly_payment)} / мес.</p>
            ) : null}
          </div>
        ) : null}
        <div className="rounded-3xl border border-white/8 p-5 text-sm">
          <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Путь политики</div>
          <p className="mt-2 font-medium">{rules || 'ещё нет автоматического следа'}</p>
          <p className="mt-3 text-muted-foreground">{String(item.policy?.specialist_summary || item.client_message || '')}</p>
        </div>
        {item.risk_memo ? (
          <div className="rounded-3xl border border-white/8 p-5 text-sm">
            <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Risk memo</div>
            <p className="mt-2 leading-relaxed">{item.risk_memo}</p>
          </div>
        ) : null}
        <dl className="grid grid-cols-2 gap-3 rounded-3xl border border-white/8 p-5 text-sm">
          <div>
            <dt className="text-muted-foreground">ЕГРЮЛ</dt>
            <dd>{registryStatus(enrichment?.egrul?.status)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">ФНС</dt>
            <dd>{enrichment?.fns?.tax_arrears ? `долг ${rub(enrichment.fns.arrears_amount)}` : 'без недоимки'}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">БКИ просрочка</dt>
            <dd>{bkiKnown ? `${enrichment?.bki?.overdue_days ?? 0} дн.` : 'Н/Д (таймаут бюро)'}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Долг в БКИ</dt>
            <dd>
              {bkiKnown ? rub(enrichment?.bki?.current_debt) : 'Требуется ручная проверка'}
              {bkiKnown && enrichment?.bki?.monthly_payment ? `, ${rub(enrichment.bki.monthly_payment)} / мес.` : ''}
            </dd>
          </div>
        </dl>
        {item.pipeline.length ? (
          <ol className="space-y-2 text-xs text-muted-foreground">
            {item.pipeline.map((step) => (
              <li key={step.code}>
                {step.title}: {step.detail} ({step.ms} мс)
              </li>
            ))}
          </ol>
        ) : null}
        {scoring ? (
          <div className="space-y-3">
            {scoring.factors.map((factor) => (
              <div key={factor.code}>
                <div className="flex justify-between text-sm">
                  <span>{factor.title}</span>
                  <span>
                    {factor.points}/{factor.max_points}
                  </span>
                </div>
                <div className="mt-1 h-1 overflow-hidden rounded-full bg-white/10">
                  <div className="h-full bg-primary" style={{ width: `${(factor.points / factor.max_points) * 100}%` }} />
                </div>
                <div className="mt-1 text-xs text-muted-foreground">{factor.comment}</div>
              </div>
            ))}
          </div>
        ) : null}
      </div>

      <div className="rounded-3xl border border-white/8 p-6">
        <h2 className="display text-2xl">Решение специалиста</h2>
        <p className="mt-2 text-sm text-muted-foreground">Скоринг — подсказка. Исход выбираете вы.</p>
        <div className="mt-6 grid grid-cols-3 gap-3">
          <label className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
            Сумма
            <input
              className="mt-2 w-full rounded-2xl border border-white/10 bg-background px-3 py-2 text-base"
              type="number"
              step={AMOUNT_STEP}
              value={amount}
              onChange={(event) => setAmount(Number(event.target.value))}
            />
          </label>
          <label className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
            Срок
            <input
              className="mt-2 w-full rounded-2xl border border-white/10 bg-background px-3 py-2 text-base"
              type="number"
              value={term}
              onChange={(event) => setTerm(Number(event.target.value))}
            />
          </label>
          <label className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
            Ставка
            <input
              className="mt-2 w-full rounded-2xl border border-white/10 bg-background px-3 py-2 text-base"
              type="number"
              step="0.1"
              value={rate}
              onChange={(event) => setRate(Number(event.target.value))}
            />
          </label>
        </div>
        <textarea
          className="mt-4 w-full rounded-2xl border border-white/10 bg-background px-4 py-3"
          rows={3}
          placeholder="Комментарий клиенту, причина отказа или текст дозапроса"
          value={comment}
          onChange={(event) => setComment(event.target.value)}
        />
        {aboveKassaLimit ? (
          <p className="mt-3 text-sm text-warn">Сумма выше доступного лимита «Кассы».</p>
        ) : null}
        {weakDscr ? (
          <p className="mt-3 text-sm text-warn">DSCR ниже 1: платёж больше расчётной прибыли.</p>
        ) : null}
        {counterofferUnchanged && item.available_actions.includes('counteroffer') ? (
          <p className="mt-3 text-sm text-muted-foreground">Для встречки измените сумму, срок или ставку.</p>
        ) : null}
        {error ? <p className="mt-3 text-primary">{error}</p> : null}
        <div className="mt-6 grid grid-cols-2 gap-3">
          <button disabled={busy || !item.available_actions.includes('offer')} onClick={() => decide('offer')} className="rounded-full bg-ok/20 py-3 text-ok disabled:opacity-30">
            Оферта
          </button>
          <button
            disabled={busy || counterofferUnchanged || !item.available_actions.includes('counteroffer')}
            onClick={() => decide('counteroffer')}
            className="rounded-full bg-warn/20 py-3 text-warn disabled:opacity-30"
          >
            Встречка
          </button>
          <button
            disabled={busy || !commentReady || !item.available_actions.includes('extra_request')}
            onClick={() => decide('extra_request')}
            className="rounded-full border border-white/15 py-3 disabled:opacity-30"
          >
            Дозапрос
          </button>
          <button
            disabled={busy || !commentReady || !item.available_actions.includes('reject')}
            onClick={() => decide('reject')}
            className="rounded-full bg-primary/20 py-3 text-primary disabled:opacity-30"
          >
            Отказ
          </button>
        </div>
        <ol className="mt-8 space-y-3 text-sm">
          {item.events.map((event) => (
            <li key={event.id} className="flex justify-between gap-4">
              <span>{event.message}</span>
              <span className="text-muted-foreground">{dateTime(event.at)}</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}
