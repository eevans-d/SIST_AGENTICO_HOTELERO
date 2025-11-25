import asyncio
from app.core.database import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as conn:
        tables = ['lock_audit', 'dlq_permanent_failures', 'audit_logs']
        for table in tables:
            result = await conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}' AND column_name='tenant_id'"))
            print(f"tenant_id in {table}: {result.rowcount > 0}")

if __name__ == "__main__":
    asyncio.run(check())
