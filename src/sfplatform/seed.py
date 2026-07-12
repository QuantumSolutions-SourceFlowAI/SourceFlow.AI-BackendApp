from sqlalchemy import text

from sfplatform.db import SessionLocal


def seed() -> None:
    with SessionLocal() as s:
        exists = s.execute(text("SELECT 1 FROM tenant WHERE id = 1")).first()
        if exists:
            return
        s.execute(text("INSERT INTO tenant (business_name, status) VALUES ('PyME Demo SAC','active')"))
        s.execute(text(
            "INSERT INTO plan (name, max_bots, max_tokens, price_amount, price_currency) "
            "VALUES ('free', 1, 100000, 0.00, 'USD')"))
        s.execute(text(
            "INSERT INTO subscription (tenant_id, plan_id, renewal_date, status) "
            "VALUES (1, 1, now() + interval '30 days', 'active')"))
        s.execute(text(
            "INSERT INTO chatbot (tenant_id, name, tone, status) "
            "VALUES (1, 'Asistente Demo', 'friendly', 'no_documents')"))
        s.commit()


if __name__ == "__main__":
    seed()
    print("Seed complete.")
