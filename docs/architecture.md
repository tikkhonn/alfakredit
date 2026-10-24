# Архитектура

```mermaid
flowchart LR
  web[React_кабинет] --> api[FastAPI]
  api --> db[PostgreSQL]
  api --> egrul[мок_ЕГРЮЛ]
  api --> fns[мок_ФНС]
  api --> bki[мок_БКИ]
  api --> engine[скоринг_и_политика]
```

Клиентский кабинет и кабинет специалиста — одно SPA, две роли, JWT.

Слои API:

- `routers` — HTTP и права
- `services` — оркестрация заявки
- `domain` — продукты, скоринг, политика, state machine без I/O
- `adapters` — контракты внешних источников на словаре ИНН

Каждое автоматическое решение пишется снимком: enrichment + scoring + policy.rules + pipeline. Клиенту отдаётся человеческий статус, `client_message` и шаги проверок. Скоринг и правила — только специалисту.

```mermaid
flowchart TD
  submit[Заявка] --> pipe[Трассировка АБС ЕГРЮЛ ФНС БКИ]
  pipe -->|BKI chaos| review[Очередь специалиста]
  pipe --> policy[Скоринг и политика]
  policy --> offer[Оферта]
  policy --> counter[Встречка]
  policy --> reject[Отказ]
  policy --> review
  counter --> whatIf[What-If выписка или залог МСП]
  whatIf --> pipe
  reject --> cure[Cure погашение ФНС]
  cure --> pipe
  review --> spec[Дозапрос оферта встречка отказ]
```
