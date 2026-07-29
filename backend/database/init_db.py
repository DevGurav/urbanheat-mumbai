from app.database.connection import engine
from app.database.models import Base


print("Creating tables...")


Base.metadata.create_all(
    bind=engine
)


print("Database initialized")