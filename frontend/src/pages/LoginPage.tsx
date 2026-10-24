import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Mark } from '../components/Mark'
import { NumberTicker } from '../components/ui/NumberTicker'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [loginName, setLoginName] = useState('ip')
  const [password, setPassword] = useState('ip123')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [accounts, setAccounts] = useState<{ login: string; password: string; hint: string }[]>([])

  useEffect(() => {
    api.demoAccounts().then(setAccounts).catch(() => undefined)
  }, [])

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const me = await login(loginName, password)
      navigate(me.role === 'specialist' ? '/bank' : '/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось войти')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fade-up grid min-h-svh lg:grid-cols-[1.15fr_0.85fr]">
      <section className="relative hidden overflow-hidden bg-[#090909] p-14 lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -left-24 top-24 h-72 w-72 rounded-full bg-primary/20 blur-3xl" />
        <div className="absolute bottom-10 right-10 h-80 w-80 rounded-full bg-accent/10 blur-3xl" />
        <div className="relative flex items-center gap-3">
          <Mark />
          <span className="text-sm uppercase tracking-[0.28em] text-muted-foreground">Альфа-хакатон 2026</span>
        </div>
        <div className="relative max-w-xl">
          <p className="mb-5 text-sm uppercase tracking-[0.3em] text-primary">кредитный конвейер</p>
          <h1 className="display text-6xl leading-[1.02]">Кредит под задачу бизнеса</h1>
          <p className="mt-6 max-w-md text-lg text-muted-foreground">
            Скажите, зачем деньги. Продукт и статус появятся сами.
          </p>
        </div>
        <div className="relative grid grid-cols-3 gap-8">
          {[
            { label: 'лимит «Кассы»', value: 1.25, suffix: ' млн ₽' },
            { label: 'варианта решения', value: 4, suffix: '' },
            { label: 'роли в кабинете', value: 2, suffix: '' },
          ].map((item) => (
            <div key={item.label}>
              <div className="display text-3xl leading-none">
                <NumberTicker value={item.value} />
                {item.suffix ? <span className="ml-1 text-2xl text-muted-foreground">{item.suffix}</span> : null}
              </div>
              <div className="mt-3 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{item.label}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="flex items-center justify-center px-6 py-16">
        <form
          onSubmit={submit}
          className="w-full max-w-md rounded-3xl border border-white/12 bg-[#141414] p-8 shadow-[0_0_80px_rgba(239,49,36,0.08)]"
        >
          <h2 className="display text-3xl">Войти в кабинет</h2>
          <p className="mt-2 text-sm text-muted-foreground">Вход для клиентов банка. Новую компанию заводить не надо.</p>
          <label className="mt-8 block text-xs uppercase tracking-[0.18em] text-muted-foreground">Логин</label>
          <input
            className="mt-2 w-full rounded-2xl border border-white/10 bg-background px-4 py-3 outline-none ring-primary/40 focus:ring-2"
            value={loginName}
            onChange={(event) => setLoginName(event.target.value)}
          />
          <label className="mt-5 block text-xs uppercase tracking-[0.18em] text-muted-foreground">Пароль</label>
          <input
            type="password"
            className="mt-2 w-full rounded-2xl border border-white/10 bg-background px-4 py-3 outline-none ring-primary/40 focus:ring-2"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {error ? <p className="mt-3 text-sm text-primary">{error}</p> : null}
          <button
            disabled={busy}
            className="mt-8 w-full rounded-full bg-primary py-3 font-medium text-primary-foreground transition hover:brightness-110 disabled:opacity-60"
          >
            {busy ? 'Входим…' : 'Продолжить'}
          </button>
          <div className="mt-8 space-y-2">
            <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Демо-учётки</div>
            {accounts.map((account) => (
              <button
                type="button"
                key={account.login}
                onClick={() => {
                  setLoginName(account.login)
                  setPassword(account.password)
                }}
                className="w-full rounded-2xl border border-white/8 px-4 py-3 text-left hover:border-primary/40"
              >
                <div className="font-medium">
                  {account.login} / {account.password}
                </div>
                <div className="text-xs text-muted-foreground">{account.hint}</div>
              </button>
            ))}
          </div>
        </form>
      </section>
    </div>
  )
}
