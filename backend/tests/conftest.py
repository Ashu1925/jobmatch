import os


os.environ.setdefault("SERPAPI_API_KEY", "test-serpapi-key")
os.environ.setdefault("SEARCHAPI_API_KEY", "test-searchapi-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:test@localhost:1925/jobmatch",
)
