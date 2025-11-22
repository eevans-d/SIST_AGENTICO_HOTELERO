import asyncio
import os
import sys
from sqlalchemy import text

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import get_db, engine
from app.core.settings import settings
import asyncpg

async def test_connection():
    print(f"Testing connection to: {settings.postgres_url.split('@')[-1]}") # Hide credentials
    print(f"Use Supabase: {settings.use_supabase}")
    
    # Test asyncpg directly
    print("\n--- Testing asyncpg directly ---")
    try:
        url = settings.postgres_url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(
            url, 
            ssl="require", 
            statement_cache_size=0
        )
        version = await conn.fetchval("SELECT version()")
        print(f"Asyncpg connection successful! Version: {version}")
        await conn.close()
    except Exception as e:
        print(f"Asyncpg connection failed: {e}")

    print("\n--- Testing SQLAlchemy ---")
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT count(*) FROM tenants"))
            count = result.scalar()
            print(f"Connection successful! Tenant count: {count}")
            
            # Check SSL
            result = await conn.execute(text("SHOW ssl"))
            ssl_status = result.scalar()
            print(f"SSL Status: {ssl_status}")
            
    except Exception as e:
        print(f"Connection failed: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    # Load .env.development manually if needed, but settings should pick it up if we set ENV var
    # or we can just rely on settings loading .env if it exists.
    # Since we created .env.development, we might need to tell settings to use it or overwrite .env
    
    # For this test, let's just set the env vars explicitly or rely on pydantic loading .env
    # But settings.py loads .env by default.
    # We should probably rename .env.development to .env for the test, or set env vars.
    
    # Let's just print what settings loaded first.
    asyncio.run(test_connection())
