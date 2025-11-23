import asyncio
import asyncpg
import os

async def main():
    url = os.getenv("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
    print(f"Connecting to {url}...")
    try:
        conn = await asyncpg.connect(url)
        print("Connection successful")
        version = await conn.fetchval("SELECT version()")
        print(f"DB Version: {version}")
        await conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
