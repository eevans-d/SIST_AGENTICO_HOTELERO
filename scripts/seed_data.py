#!/usr/bin/env python3
# ════════════════════════════════════════════════════════════════════════════════
# Seed Data Script for Staging Deployment
# ════════════════════════════════════════════════════════════════════════════════
# Purpose: Load initial data (tenants, users, rooms, configurations)
# Usage: python scripts/seed_data.py
# Generated: 2025-10-23
# ════════════════════════════════════════════════════════════════════════════════

import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agente-hotel-api'))

from app.core.database import AsyncSessionFactory, Base, engine
from app.models.schemas import Tenant, User, TenantUserIdentifier, Room
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

# ════════════════════════════════════════════════════════════════════════════════
# SEED DATA DEFINITIONS
# ════════════════════════════════════════════════════════════════════════════════

STAGING_TENANTS = [
    {
        "name": "Hotel Plaza Mayor",
        "slug": "hotel-plaza-mayor",
        "description": "5-star luxury hotel in city center",
        "active": True,
        "metadata": {
            "city": "Madrid",
            "country": "Spain",
            "phone": "+34-91-360-0600",
            "email": "info@plazamayor.es",
            "timezone": "Europe/Madrid"
        }
    },
    {
        "name": "Beachfront Resort",
        "slug": "beachfront-resort",
        "description": "All-inclusive beach resort",
        "active": True,
        "metadata": {
            "city": "Cancun",
            "country": "Mexico",
            "phone": "+52-998-881-1000",
            "email": "info@beachfront.mx",
            "timezone": "America/Mexico_City"
        }
    },
    {
        "name": "Mountain Lodge",
        "slug": "mountain-lodge",
        "description": "Boutique mountain hotel",
        "active": True,
        "metadata": {
            "city": "Aspen",
            "country": "USA",
            "phone": "+1-970-925-3220",
            "email": "info@mountainlodge.com",
            "timezone": "America/Denver"
        }
    }
]

STAGING_USERS_BY_TENANT = {
    "hotel-plaza-mayor": [
        {
            "username": "admin_plaza",
            "email": "admin@plazamayor.es",
            "phone": "+34-91-360-0601",
            "role": "admin",
            "channel": "whatsapp"
        },
        {
            "username": "staff_plaza_1",
            "email": "staff1@plazamayor.es",
            "phone": "+34-91-360-0602",
            "role": "staff",
            "channel": "whatsapp"
        },
        {
            "username": "staff_plaza_2",
            "email": "staff2@plazamayor.es",
            "phone": "+34-91-360-0603",
            "role": "staff",
            "channel": "gmail"
        },
        {
            "username": "guest_plaza_1",
            "email": "guest1@example.com",
            "phone": "+34-600-000-001",
            "role": "guest",
            "channel": "whatsapp"
        }
    ],
    "beachfront-resort": [
        {
            "username": "admin_beach",
            "email": "admin@beachfront.mx",
            "phone": "+52-998-881-1001",
            "role": "admin",
            "channel": "whatsapp"
        },
        {
            "username": "staff_beach_1",
            "email": "staff@beachfront.mx",
            "phone": "+52-998-881-1002",
            "role": "staff",
            "channel": "whatsapp"
        }
    ],
    "mountain-lodge": [
        {
            "username": "admin_mountain",
            "email": "admin@mountainlodge.com",
            "phone": "+1-970-925-3221",
            "role": "admin",
            "channel": "whatsapp"
        },
        {
            "username": "concierge",
            "email": "concierge@mountainlodge.com",
            "phone": "+1-970-925-3222",
            "role": "staff",
            "channel": "whatsapp"
        }
    ]
}

STAGING_ROOMS_BY_TENANT = {
    "hotel-plaza-mayor": [
        {
            "room_number": "101",
            "room_type": "single",
            "capacity": 1,
            "price_per_night": 150.00,
            "features": ["wifi", "bathroom", "tv"]
        },
        {
            "room_number": "102",
            "room_type": "single",
            "capacity": 1,
            "price_per_night": 150.00,
            "features": ["wifi", "bathroom", "tv"]
        },
        {
            "room_number": "201",
            "room_type": "double",
            "capacity": 2,
            "price_per_night": 250.00,
            "features": ["wifi", "bathroom", "tv", "balcony"]
        },
        {
            "room_number": "202",
            "room_type": "double",
            "capacity": 2,
            "price_per_night": 250.00,
            "features": ["wifi", "bathroom", "tv", "balcony"]
        },
        {
            "room_number": "301",
            "room_type": "suite",
            "capacity": 4,
            "price_per_night": 500.00,
            "features": ["wifi", "bathroom", "tv", "balcony", "hot_tub", "kitchen"]
        }
    ],
    "beachfront-resort": [
        {
            "room_number": "B101",
            "room_type": "beachfront_single",
            "capacity": 1,
            "price_per_night": 200.00,
            "features": ["wifi", "bathroom", "tv", "beach_access"]
        },
        {
            "room_number": "B102",
            "room_type": "beachfront_double",
            "capacity": 2,
            "price_per_night": 350.00,
            "features": ["wifi", "bathroom", "tv", "beach_access", "balcony"]
        },
        {
            "room_number": "B103",
            "room_type": "beachfront_suite",
            "capacity": 4,
            "price_per_night": 600.00,
            "features": ["wifi", "bathroom", "tv", "beach_access", "hot_tub", "kitchen"]
        },
        {
            "room_number": "B104",
            "room_type": "beachfront_suite",
            "capacity": 4,
            "price_per_night": 600.00,
            "features": ["wifi", "bathroom", "tv", "beach_access", "hot_tub", "kitchen"]
        },
        {
            "room_number": "B105",
            "room_type": "standard",
            "capacity": 2,
            "price_per_night": 280.00,
            "features": ["wifi", "bathroom", "tv"]
        }
    ],
    "mountain-lodge": [
        {
            "room_number": "M101",
            "room_type": "mountain_view",
            "capacity": 2,
            "price_per_night": 180.00,
            "features": ["wifi", "bathroom", "tv", "fireplace"]
        },
        {
            "room_number": "M102",
            "room_type": "mountain_view",
            "capacity": 2,
            "price_per_night": 180.00,
            "features": ["wifi", "bathroom", "tv", "fireplace"]
        },
        {
            "room_number": "M201",
            "room_type": "cabin",
            "capacity": 4,
            "price_per_night": 320.00,
            "features": ["wifi", "bathroom", "tv", "fireplace", "kitchen", "hot_tub"]
        },
        {
            "room_number": "M202",
            "room_type": "cabin",
            "capacity": 4,
            "price_per_night": 320.00,
            "features": ["wifi", "bathroom", "tv", "fireplace", "kitchen", "hot_tub"]
        },
        {
            "room_number": "M301",
            "room_type": "penthouse",
            "capacity": 6,
            "price_per_night": 550.00,
            "features": ["wifi", "bathroom", "tv", "fireplace", "kitchen", "hot_tub", "views"]
        }
    ]
}

# ════════════════════════════════════════════════════════════════════════════════
# ASYNC SEED FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════════

async def init_database():
    """Initialize database tables via SQLAlchemy ORM."""
    print("📊 Initializing database schema...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database schema created successfully")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        raise

async def seed_tenants(session: AsyncSession):
    """Seed tenant data."""
    print("\n🏨 Seeding tenants...")
    try:
        for tenant_data in STAGING_TENANTS:
            tenant = Tenant(
                name=tenant_data["name"],
                slug=tenant_data["slug"],
                description=tenant_data["description"],
                active=tenant_data["active"],
                metadata=tenant_data["metadata"],
                created_at=datetime.utcnow()
            )
            session.add(tenant)
        
        await session.commit()
        print(f"✅ Seeded {len(STAGING_TENANTS)} tenants")
    except Exception as e:
        await session.rollback()
        print(f"❌ Error seeding tenants: {e}")
        raise

async def seed_users(session: AsyncSession):
    """Seed user data and tenant-user identifiers."""
    print("\n👥 Seeding users...")
    try:
        for tenant_slug, users in STAGING_USERS_BY_TENANT.items():
            # Get tenant
            result = await session.execute(
                text(f"SELECT id FROM tenant WHERE slug = '{tenant_slug}'")
            )
            tenant_id = result.scalar()
            
            if not tenant_id:
                print(f"⚠️  Tenant {tenant_slug} not found, skipping users")
                continue
            
            for user_data in users:
                user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    phone=user_data["phone"],
                    role=user_data["role"],
                    active=True,
                    created_at=datetime.utcnow()
                )
                session.add(user)
                await session.flush()
                
                # Create tenant-user identifier
                identifier = TenantUserIdentifier(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    channel=user_data["channel"],
                    channel_user_id=user_data["phone"],  # Use phone as channel identifier
                    metadata={"verified": True},
                    created_at=datetime.utcnow()
                )
                session.add(identifier)
        
        await session.commit()
        total_users = sum(len(u) for u in STAGING_USERS_BY_TENANT.values())
        print(f"✅ Seeded {total_users} users across {len(STAGING_USERS_BY_TENANT)} tenants")
    except Exception as e:
        await session.rollback()
        print(f"❌ Error seeding users: {e}")
        raise

async def seed_rooms(session: AsyncSession):
    """Seed room data."""
    print("\n🛏️  Seeding rooms...")
    try:
        total_rooms = 0
        for tenant_slug, rooms in STAGING_ROOMS_BY_TENANT.items():
            # Get tenant
            result = await session.execute(
                text(f"SELECT id FROM tenant WHERE slug = '{tenant_slug}'")
            )
            tenant_id = result.scalar()
            
            if not tenant_id:
                print(f"⚠️  Tenant {tenant_slug} not found, skipping rooms")
                continue
            
            for room_data in rooms:
                room = Room(
                    tenant_id=tenant_id,
                    room_number=room_data["room_number"],
                    room_type=room_data["room_type"],
                    capacity=room_data["capacity"],
                    price_per_night=room_data["price_per_night"],
                    features=room_data["features"],
                    available=True,
                    created_at=datetime.utcnow()
                )
                session.add(room)
                total_rooms += 1
        
        await session.commit()
        print(f"✅ Seeded {total_rooms} rooms")
    except Exception as e:
        await session.rollback()
        print(f"❌ Error seeding rooms: {e}")
        raise

async def main():
    """Main seed function."""
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║          🌱 STAGING DATABASE SEED SCRIPT                      ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    
    try:
        # Initialize database schema
        await init_database()
        
        # Create session and seed data
        async with AsyncSessionFactory() as session:
            await seed_tenants(session)
            await seed_users(session)
            await seed_rooms(session)
        
        print("\n✅ ════════════════════════════════════════════════════════════════")
        print("✅ ALL SEED DATA LOADED SUCCESSFULLY")
        print("✅ ════════════════════════════════════════════════════════════════")
        print("\n📊 Summary:")
        print(f"   • Tenants: {len(STAGING_TENANTS)}")
        print(f"   • Users: {sum(len(u) for u in STAGING_USERS_BY_TENANT.values())}")
        print(f"   • Rooms: {sum(len(r) for r in STAGING_ROOMS_BY_TENANT.values())}")
        
    except Exception as e:
        print(f"\n❌ SEED FAILED: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
