import sys
from sqlalchemy import create_engine, text

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

LIVE_DB_URL = "postgresql://utsav_db_nrue_user:FDjZCVInjYxzZc2tmvc5bjuPrrPA65Rx@dpg-dbcddfmq1p3s73d2ug20-a.singapore-postgres.render.com/utsav_db_nrue"

def main():
    print("Connecting to live Singapore PostgreSQL...")
    engine = create_engine(LIVE_DB_URL)
    with engine.begin() as conn:
        # Check current alembic version
        ver_res = conn.execute(text("SELECT version_num FROM alembic_version;")).fetchall()
        print("Current alembic_version:", [r[0] for r in ver_res])

        # Check if invitation_cards table exists
        exists = conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name='invitation_cards';"
        )).fetchall()

        if not exists:
            print("Creating invitation_cards table...")
            conn.execute(text("""
                CREATE TABLE invitation_cards (
                    id VARCHAR(36) PRIMARY KEY,
                    event_id VARCHAR(36) NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                    theme_proposal_id VARCHAR(36) REFERENCES theme_proposals(id) ON DELETE SET NULL,
                    layout_variant VARCHAR(50) NOT NULL,
                    wording_text TEXT NOT NULL,
                    guest_id VARCHAR(36) REFERENCES guests(id) ON DELETE CASCADE,
                    rendered_png BYTEA,
                    rendered_pdf BYTEA,
                    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """))
            conn.execute(text("CREATE INDEX ix_invitation_cards_event_id ON invitation_cards(event_id);"))
            conn.execute(text("CREATE INDEX ix_invitation_cards_theme_proposal_id ON invitation_cards(theme_proposal_id);"))
            conn.execute(text("CREATE INDEX ix_invitation_cards_guest_id ON invitation_cards(guest_id);"))
            print("invitation_cards table and indexes created successfully!")
        else:
            print("invitation_cards table already exists!")

        # Update alembic_version
        conn.execute(text("UPDATE alembic_version SET version_num = '0008_f16_invitation_cards';"))
        new_ver = conn.execute(text("SELECT version_num FROM alembic_version;")).fetchall()
        print("Updated alembic_version to:", [r[0] for r in new_ver])

    print("Live migration completed successfully!")

if __name__ == "__main__":
    main()
