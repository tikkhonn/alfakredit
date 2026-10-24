import type { Application } from '../lib/api'
import { PRODUCT_LABEL, rub } from '../lib/format'

export function OfferPreview({ item, onClose }: { item: Application; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-40 grid place-items-center bg-black/70 p-6 print:static print:bg-white">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-auto rounded-3xl border border-white/10 bg-[#111] p-8 print:border-0 print:bg-white print:text-black">
        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{item.public_number}</p>
        <h2 className="display mt-2 text-3xl">Индивидуальные условия</h2>
        <p className="mt-2 text-muted-foreground">
          {PRODUCT_LABEL[item.product]} · {rub(item.offer_amount)} на {item.offer_term_months} мес. под {item.offer_rate}%
        </p>
        {item.monthly_payment ? (
          <p className="mt-4 text-lg">Платёж около {rub(item.monthly_payment)} в месяц.</p>
        ) : null}
        <table className="mt-6 w-full text-sm">
          <thead className="text-left text-muted-foreground">
            <tr>
              <th className="py-2">Мес.</th>
              <th>Платёж</th>
              <th>Долг</th>
              <th>Проценты</th>
              <th>Остаток</th>
            </tr>
          </thead>
          <tbody>
            {item.schedule.map((row) => (
              <tr key={row.month} className="border-t border-white/8">
                <td className="py-2">{row.month}</td>
                <td>{rub(row.payment)}</td>
                <td>{rub(row.principal)}</td>
                <td>{rub(row.interest)}</td>
                <td>{rub(row.remaining)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-6 text-xs text-muted-foreground">Выдача смоделирована. Проводок в АБС нет.</p>
        <div className="mt-6 flex gap-3 print:hidden">
          <button onClick={() => window.print()} className="rounded-full bg-primary px-5 py-2 text-primary-foreground">
            Печать
          </button>
          <button onClick={onClose} className="rounded-full border border-white/15 px-5 py-2">
            Закрыть
          </button>
        </div>
      </div>
    </div>
  )
}
