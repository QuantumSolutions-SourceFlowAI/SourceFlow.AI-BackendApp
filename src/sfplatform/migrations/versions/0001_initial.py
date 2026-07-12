"""initial schema

Revision ID: 0001
Revises:
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute("CREATE TYPE tenant_status AS ENUM ('active','suspended')")
    op.execute("CREATE TYPE chatbot_status AS ENUM ('no_documents','ready')")
    op.execute("CREATE TYPE chatbot_tone AS ENUM ('formal','friendly','sales')")
    op.execute("CREATE TYPE document_status AS ENUM ('processing','ready','error')")
    op.execute("CREATE TYPE message_sender AS ENUM ('customer','assistant')")
    op.execute("CREATE TYPE feedback_rating AS ENUM ('useful','not_useful')")
    op.execute("CREATE TYPE subscription_status AS ENUM ('active','past_due','cancelled')")
    op.execute("CREATE TYPE user_role AS ENUM ('admin','worker')")

    op.execute("""
        CREATE TABLE tenant (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            business_name VARCHAR(255) NOT NULL,
            status tenant_status NOT NULL DEFAULT 'active',
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP
        )""")

    op.execute("""
        CREATE TABLE users (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            tenant_id BIGINT NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role user_role NOT NULL DEFAULT 'worker',
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP
        )""")
    op.execute("CREATE INDEX idx_users_tenant ON users(tenant_id)")

    op.execute("""
        CREATE TABLE chatbot (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            tenant_id BIGINT NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            tone chatbot_tone NOT NULL,
            status chatbot_status NOT NULL DEFAULT 'no_documents',
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP
        )""")
    op.execute("CREATE UNIQUE INDEX idx_unique_chatbot_name_per_tenant ON chatbot(tenant_id, name)")

    op.execute("""
        CREATE TABLE document (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            tenant_id BIGINT NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
            chatbot_id BIGINT NOT NULL REFERENCES chatbot(id) ON DELETE CASCADE,
            file_name VARCHAR(255) NOT NULL,
            size_bytes BIGINT NOT NULL,
            status document_status NOT NULL DEFAULT 'processing',
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP
        )""")
    op.execute("CREATE INDEX idx_document_tenant ON document(tenant_id)")
    op.execute("CREATE INDEX idx_document_chatbot ON document(chatbot_id)")

    op.execute("""
        CREATE TABLE chunk (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            tenant_id BIGINT NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
            document_id BIGINT NOT NULL REFERENCES document(id) ON DELETE CASCADE,
            text_content TEXT NOT NULL,
            position INT NOT NULL,
            embedding_vector VECTOR(1024) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        )""")
    op.execute("CREATE INDEX idx_chunk_document ON chunk(document_id)")
    op.execute("CREATE INDEX idx_chunk_tenant ON chunk(tenant_id)")
    op.execute("CREATE INDEX idx_vector_hnsw ON chunk USING hnsw (embedding_vector vector_cosine_ops)")

    op.execute("""
        CREATE TABLE conversation (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            tenant_id BIGINT NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
            chatbot_id BIGINT NOT NULL REFERENCES chatbot(id) ON DELETE CASCADE,
            started_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP
        )""")
    op.execute("CREATE INDEX idx_conversation_tenant ON conversation(tenant_id)")
    op.execute("CREATE INDEX idx_conversation_chatbot ON conversation(chatbot_id)")

    op.execute("""
        CREATE TABLE message (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            tenant_id BIGINT NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
            conversation_id BIGINT NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
            sender message_sender NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL DEFAULT now(),
            answer_text TEXT,
            answer_grounded BOOLEAN,
            tokens_used INT
        )""")
    op.execute("CREATE INDEX idx_message_conversation ON message(conversation_id)")
    op.execute("CREATE INDEX idx_message_tenant ON message(tenant_id)")

    op.execute("""
        CREATE TABLE message_source (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            message_id BIGINT NOT NULL REFERENCES message(id) ON DELETE CASCADE,
            chunk_id BIGINT NOT NULL REFERENCES chunk(id) ON DELETE CASCADE
        )""")
    op.execute("CREATE UNIQUE INDEX idx_unique_message_chunk ON message_source(message_id, chunk_id)")
    op.execute("CREATE INDEX idx_message_source_chunk ON message_source(chunk_id)")

    op.execute("""
        CREATE TABLE answer_feedback (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            tenant_id BIGINT NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
            message_id BIGINT NOT NULL REFERENCES message(id) ON DELETE CASCADE,
            rating feedback_rating NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        )""")
    op.execute("CREATE UNIQUE INDEX idx_unique_feedback_message ON answer_feedback(message_id)")

    op.execute("""
        CREATE TABLE answer_cache (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            tenant_id BIGINT NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
            chatbot_id BIGINT NOT NULL REFERENCES chatbot(id) ON DELETE CASCADE,
            question_hash CHAR(64) NOT NULL,
            question_text TEXT NOT NULL,
            answer_text TEXT NOT NULL,
            answer_grounded BOOLEAN NOT NULL,
            source_snapshot TEXT,
            hit_count INT NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            last_hit_at TIMESTAMP
        )""")
    op.execute("CREATE UNIQUE INDEX idx_unique_cache_question ON answer_cache(tenant_id, chatbot_id, question_hash)")
    op.execute("CREATE INDEX idx_answer_cache_chatbot ON answer_cache(chatbot_id)")

    op.execute("""
        CREATE TABLE token_consumption (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            tenant_id BIGINT NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
            period_start TIMESTAMP NOT NULL,
            period_end TIMESTAMP NOT NULL,
            tokens_used INT NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        )""")
    op.execute("CREATE UNIQUE INDEX idx_unique_tenant_period ON token_consumption(tenant_id, period_start)")

    op.execute("""
        CREATE TABLE plan (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            max_bots INT NOT NULL,
            max_tokens INT NOT NULL,
            price_amount DECIMAL(10,2) NOT NULL,
            price_currency VARCHAR(3) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP
        )""")

    op.execute("""
        CREATE TABLE subscription (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            tenant_id BIGINT UNIQUE NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
            plan_id BIGINT NOT NULL REFERENCES plan(id) ON DELETE RESTRICT,
            renewal_date TIMESTAMP NOT NULL,
            status subscription_status NOT NULL DEFAULT 'active',
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP
        )""")
    op.execute("CREATE INDEX idx_subscription_plan ON subscription(plan_id)")


def downgrade() -> None:
    for t in ["subscription", "plan", "token_consumption", "answer_cache",
              "answer_feedback", "message_source", "message", "conversation",
              "chunk", "document", "chatbot", "users", "tenant"]:
        op.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
    for e in ["user_role", "subscription_status", "feedback_rating", "message_sender",
              "document_status", "chatbot_tone", "chatbot_status", "tenant_status"]:
        op.execute(f"DROP TYPE IF EXISTS {e}")
