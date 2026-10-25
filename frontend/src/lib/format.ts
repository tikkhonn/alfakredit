export function rub(value: number | null | undefined) {
  if (value == null) return '—'
  return new Intl.NumberFormat('ru-RU').format(value) + ' ₽'
}

export function dateTime(value: string) {
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

export function greeting() {
  const hour = new Date().getHours()
  if (hour < 6 || hour >= 23) return 'Доброй ночи'
  if (hour < 12) return 'Доброе утро'
  if (hour < 18) return 'Добрый день'
  return 'Добрый вечер'
}

export function ageLabel(months: number) {
  const years = Math.floor(months / 12)
  const rest = months % 12
  if (years <= 0) return `${months} мес.`
  const yearWord = years === 1 ? 'год' : years < 5 ? 'года' : 'лет'
  if (rest === 0) return `${years} ${yearWord}`
  return `${years} ${yearWord} ${rest} мес.`
}

export const PURPOSE_LABEL: Record<string, string> = {
  cash_gap: 'Кассовый разрыв',
  restock: 'Закупка и оборот',
  growth: 'Рост и оборудование',
}

export const RULE_LABEL: Record<string, string> = {
  'stop:legal_status': 'стоп: компания не действует',
  'stop:account_blocked': 'стоп: счёт ограничен',
  'stop:tax_arrears': 'стоп: налоговая задолженность',
  'stop:bki_overdue': 'стоп: просрочка в БКИ',
  missing_fields: 'не хватает данных',
  'fallback:bki_timeout': 'БКИ не ответило, заявку смотрит специалист',
  'cure:tax_cleared': 'налог погашен, нужна ручная оценка',
  'client:profile_changed': 'клиент сообщил, что данные устарели',
  'collateral:msp': 'клиент готов к поручительству МСП',
  'product:razvitie_requires_specialist': '«Развитие» решает специалист',
  'score:borderline': 'пограничный скоринг',
  'kassa:within_limit': 'сумма внутри лимита «Кассы»',
  'kassa:other_bank_turnover': 'учтены обороты другого банка',
  'kassa:above_limit': 'запрос выше лимита «Кассы»',
  'score:strong': 'скоринг высокий',
  'score:good': 'скоринг хороший',
  'score:moderate': 'скоринг средний',
  'score:weak': 'скоринг слабый',
  'specialist:offer': 'специалист подтвердил оферту',
  'specialist:counteroffer': 'специалист предложил другие условия',
  'specialist:reject': 'специалист отказал',
  'specialist:extra_request': 'специалист запросил уточнение',
}

export function ruleLabel(rule: string) {
  return RULE_LABEL[rule] || rule
}

export function registryStatus(status?: string | null) {
  if (status === 'active') return 'действует'
  return status || '—'
}

export const PRODUCT_LABEL: Record<string, string> = {
  kassa: 'Касса',
  razvitie: 'Развитие',
}

export const STATUS_TONE: Record<string, string> = {
  offer: 'text-ok',
  issued: 'text-ok',
  counteroffer: 'text-warn',
  extra_requested: 'text-warn',
  in_review: 'text-foreground',
  rejected: 'text-primary',
  closed: 'text-muted-foreground',
  signing: 'text-ok',
  submitted: 'text-muted-foreground',
}
