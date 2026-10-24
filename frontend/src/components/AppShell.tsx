import { LogOut } from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { cn } from '../lib/cn'
import { Mark } from './Mark'

export function AppShell() {
  const { me, logout } = useAuth()
  const navigate = useNavigate()
  const [bkiDown, setBkiDown] = useState(false)

  useEffect(() => {
    api
      .chaos()
      .then((state) => setBkiDown(state.bki_down))
      .catch(() => undefined)
  }, [])

  async function toggleChaos() {
    const next = !bkiDown
    setBkiDown(next)
    try {
      const state = await api.setChaos(next)
      setBkiDown(state.bki_down)
    } catch {
      setBkiDown(!next)
    }
  }

  return (
    <div className="min-h-svh bg-background text-foreground">
      <header className="sticky top-0 z-20 border-b border-white/8 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <button className="flex items-center gap-3" onClick={() => navigate(me?.role === 'specialist' ? '/bank' : '/')}>
            <Mark />
            <div className="text-left">
              <div className="display text-sm tracking-wide">Кредитный кабинет</div>
              <div className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                {me?.role === 'specialist' ? 'рабочее место банка' : 'для предпринимателя'}
              </div>
            </div>
          </button>
          <div className="flex items-center gap-6">
            {me?.role === 'specialist' ? (
              <NavLink to="/bank" className={({ isActive }) => cn('text-sm', isActive ? 'text-foreground' : 'text-muted-foreground')}>
                Очередь
              </NavLink>
            ) : (
              <>
                <NavLink to="/" className={({ isActive }) => cn('text-sm', isActive ? 'text-foreground' : 'text-muted-foreground')}>
                  Кабинет
                </NavLink>
                <NavLink to="/new" className={({ isActive }) => cn('text-sm', isActive ? 'text-foreground' : 'text-muted-foreground')}>
                  Новая заявка
                </NavLink>
              </>
            )}
            <button
              type="button"
              onClick={toggleChaos}
              className={cn(
                'rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.16em]',
                bkiDown ? 'border-warn text-warn' : 'border-white/10 text-muted-foreground',
              )}
            >
              Сбой БКИ {bkiDown ? 'вкл' : 'выкл'}
            </button>
            <div className="text-right">
              <div className="text-sm">{me?.full_name}</div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                {me?.role === 'specialist' ? 'специалист' : me?.company?.short_name}
              </div>
            </div>
            <button
              aria-label="Выйти"
              className="rounded-full border border-white/10 p-2 text-muted-foreground hover:text-foreground"
              onClick={() => {
                logout()
                navigate('/login')
              }}
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-10">
        <Outlet />
      </main>
    </div>
  )
}
