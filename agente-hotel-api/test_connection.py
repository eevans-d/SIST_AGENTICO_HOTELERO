import asyncio
import os
import asyncpg

async def main():
    # Load from .env
    from dotenv import load_dotenv
    load_dotenv()
    
    url = os.getenv("POSTGRES_URL")
    # asyncpg.connect needs postgresql://, not postgresql+asyncpg://
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    print(f"Connecting to: {url[:50]}...")
    
    try:
        # Connect with statement_cache_size=0
        conn = await asyncpg.connect(url, statement_cache_size=0)
        print("✓ Connection successful!")
        
        # Test query
        version = await conn.fetchval("SELECT version()")
        print(f"✓ Database version: {version[:100]}")
        
        # Check if users table exists
        result = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"
        )
        print(f"✓ Users table exists: {result}")
        
        await conn.close()
        print("✓ Connection closed successfully")
        
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
