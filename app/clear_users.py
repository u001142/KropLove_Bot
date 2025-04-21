from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# URL з твого Render (використовується Internal DB URL)
DATABASE_URL = "postgresql://kroplove_db_user:GCS7ikUKQk0q0PZ5vsWBJ4KV75xcOe4B@dpg-d02p2qadbo4c73f1i8m0-a/kroplove_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def clear_users():
    with SessionLocal() as session:
        session.execute("DELETE FROM users_v2;")  # або 'users' якщо таблиця так називається
        session.commit()
        print("✅ Усі анкети (users_v2) очищено!")

if __name__ == "__main__":
    clear_users()
