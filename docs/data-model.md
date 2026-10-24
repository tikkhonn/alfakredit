# Модель данных

- `company` — действующий клиент банка: реквизиты, обороты за 6 месяцев, блок счёта.
- `user` — `ip` / `ooo` (role=client) и `spec` (role=specialist).
- `application` — заявка: цель, продукт, суммы, статус, JSON-снимки enrichment/scoring/policy/pipeline, оферта, поля дозапроса, флаги `profile_changed`, `extra_turnover`, `collateral_msp`.
- `applicationevent` — таймлайн. Клиенту видны `message`, специалисту ещё `detail`.

Идентификаторы UUID. Публичный номер `APP-2026-NNNN`. Деньги — целые рубли, шаг суммы 10 000 ₽.

```mermaid
erDiagram
  COMPANY ||--o{ USER : employs
  COMPANY ||--o{ APPLICATION : files
  APPLICATION ||--o{ APPLICATIONEVENT : timeline

  COMPANY {
    string id PK
    string legal_form
    string inn UK
    string ogrn
    string name
    string short_name
    string okved
    string okved_name
    date registered_at
    string status
    string director_name
    boolean account_blocked
    json turnovers
  }

  USER {
    string id PK
    string login UK
    string password_hash
    string full_name
    string role
    string company_id FK
  }

  APPLICATION {
    string id PK
    string public_number UK
    string company_id FK
    string created_by_user_id FK
    string purpose
    string product
    int requested_amount
    int requested_term_months
    string purpose_details
    string status
    json enrichment
    json scoring
    json policy
    json pipeline
    int offer_amount
    int offer_term_months
    float offer_rate
    json extra_fields
    string extra_comment
    string client_message
    string decided_by
    boolean profile_changed
    int extra_turnover
    boolean collateral_msp
    datetime created_at
    datetime updated_at
  }

  APPLICATIONEVENT {
    string id PK
    string application_id FK
    datetime at
    string actor
    string action
    string status
    string message
    json detail
  }
```
