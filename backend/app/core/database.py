from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

is_sqlite = settings.DATABASE_URL.startswith("sqlite")

connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True if not is_sqlite else False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    if not is_sqlite:
        with engine.connect() as conn:
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
            except Exception as e:
                print(f"[Warning] Failed to enable pgvector extension: {e}")
            
            try:
                conn.execute(text(f"ALTER TABLE code_chunks ALTER COLUMN embedding TYPE vector({settings.EMBEDDING_DIMENSION});"))
                conn.commit()
                print(f"[DB Migration] Verified/upgraded code_chunks.embedding column to vector({settings.EMBEDDING_DIMENSION}).")
            except Exception as e:
                # Table may not exist yet; create_all will create it with Vector(3072)
                pass
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
