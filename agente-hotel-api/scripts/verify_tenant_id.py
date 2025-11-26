import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.settings import settings

async def verify_schema():
    # Get URL and switch to port 5432 for direct connection
    url = settings.postgres_url
    if "6543" in url:
        url = url.replace("6543", "5432")
    
    print(f"Connecting to: {url.split('@')[1]}") # Log safe part of URL
    
    engine = create_async_engine(url, echo=False)
    
    async with engine.connect() as conn:
        tables = ["audit_logs", "lock_audit", "dlq_permanent_failures"]
        for table in tables:
            print(f"Checking table: {table}")
            result = await conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' AND column_name = 'tenant_id'"))
            row = result.fetchone()
            if row:
                print(f"✅ 'tenant_id' column found in {table}")
            else:
                print(f"❌ 'tenant_id' column NOT found in {table}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify_schema())
