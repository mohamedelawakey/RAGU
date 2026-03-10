# Database Migrations

This folder is reserved for Alembic migrations.

## Basic Commands

1. **Initialize Alembic (Once):**
   ```bash
   alembic init backend/db/migrations
   ```

2. **Generate a New Migration (After modifying `backend/db/models/postgres_models.py`):**
   ```bash
   alembic revision --autogenerate -m "Migration description"
   ```

3. **Apply Migrations to the Database:**
   ```bash
   alembic upgrade head
   ```
