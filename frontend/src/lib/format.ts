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
