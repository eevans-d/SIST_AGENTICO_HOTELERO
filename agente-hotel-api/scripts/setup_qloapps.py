#!/usr/bin/env python3
"""
QloApps PMS Integration Setup and Test Script

This script helps configure and test the connection to QloApps PMS.
"""

import asyncio
import sys
from pathlib import Path
from datetime import date, timedelta
from typing import Optional

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.settings import settings
from app.core.logging import logger
from app.services.qloapps_client import create_qloapps_client, QloAppsClient


class QloAppsSetup:
    """Helper class for QloApps setup and testing."""
    
    def __init__(self):
        self.client: Optional[QloAppsClient] = None
    
    async def test_connection(self) -> bool:
        """Test basic connection to QloApps API."""
        logger.info("=" * 60)
        logger.info("TESTING QLOAPPS CONNECTION")
        logger.info("=" * 60)
        
        try:
            self.client = create_qloapps_client()
            
            logger.info(f"📍 Base URL: {settings.pms_base_url}")
            logger.info(f"🔑 API Key: {'*' * 20}...")
            logger.info(f"🏨 Hotel ID: {settings.pms_hotel_id}")
            
            # Test connection
            is_connected = await self.client.test_connection()
            
            if is_connected:
                logger.info("✅ Connection successful!")
                return True
            else:
                logger.error("❌ Connection failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Connection error: {e}")
            return False
    
    async def get_hotels(self):
        """List all hotels in QloApps."""
        logger.info("\n" + "=" * 60)
        logger.info("LISTING HOTELS")
        logger.info("=" * 60)
        
        try:
            hotels = await self.client.get_hotels()
            
            if hotels:
                logger.info(f"Found {len(hotels)} hotel(s):")
                for hotel in hotels:
                    logger.info(f"  - ID: {hotel.get('id')} | Name: {hotel.get('name')}")
            else:
                logger.warning("No hotels found")
            
            return hotels
            
        except Exception as e:
            logger.error(f"Failed to list hotels: {e}")
            return []
    
    async def get_room_types(self):
        """List all room types."""
        logger.info("\n" + "=" * 60)
        logger.info("LISTING ROOM TYPES")
        logger.info("=" * 60)
        
        try:
            room_types = await self.client.get_room_types()
            
            if room_types:
                logger.info(f"Found {len(room_types)} room type(s):")
                for rt in room_types:
                    logger.info(
                        f"  - ID: {rt.get('id')} | "
                        f"Name: {rt.get('name')} | "
                        f"Max Guests: {rt.get('max_guests')}"
                    )
            else:
                logger.warning("No room types found")
            
            return room_types
            
        except Exception as e:
            logger.error(f"Failed to list room types: {e}")
            return []
    
    async def test_availability(self):
        """Test availability check."""
        logger.info("\n" + "=" * 60)
        logger.info("TESTING AVAILABILITY CHECK")
        logger.info("=" * 60)
        
        try:
            # Test dates: tomorrow to day after tomorrow
            check_in = date.today() + timedelta(days=1)
            check_out = check_in + timedelta(days=1)
            
            logger.info(f"Check-in: {check_in}")
            logger.info(f"Check-out: {check_out}")
            logger.info("Guests: 2 adults")
            
            rooms = await self.client.check_availability(
                hotel_id=settings.pms_hotel_id,
                date_from=check_in,
                date_to=check_out,
                num_rooms=1,
                num_adults=2,
                num_children=0
            )
            
            if rooms:
                logger.info(f"✅ Found {len(rooms)} available room(s):")
                for room in rooms:
                    logger.info(
                        f"  - {room.get('room_type_name')}: "
                        f"{room.get('price_per_night')} {room.get('currency')}/night | "
                        f"{room.get('available_rooms')} available"
                    )
            else:
                logger.warning("⚠️ No rooms available for selected dates")
            
            return rooms
            
        except Exception as e:
            logger.error(f"❌ Availability check failed: {e}")
            return []
    
    async def test_create_test_booking(self):
        """Test creating a booking (if safe to do so)."""
        logger.info("\n" + "=" * 60)
        logger.info("TESTING BOOKING CREATION")
        logger.info("=" * 60)
        
        logger.warning("⚠️ Skipping actual booking creation to avoid test data")
        logger.info("To test booking creation, implement with test guest data")
        
        # Example code (commented out):
        # check_in = date.today() + timedelta(days=7)
        # check_out = check_in + timedelta(days=2)
        # 
        # guest_info = {
        #     "first_name": "Test",
        #     "last_name": "Guest",
        #     "email": "test@example.com",
        #     "phone": "+1234567890"
        # }
        # 
        # booking = await self.client.create_booking(
        #     hotel_id=settings.pms_hotel_id,
        #     room_type_id=1,
        #     date_from=check_in,
        #     date_to=check_out,
        #     num_rooms=1,
        #     guest_info=guest_info
        # )
        
        return None
    
    async def run_all_tests(self):
        """Run all setup and test procedures."""
        logger.info("\n" + "=" * 70)
        logger.info("QLOAPPS PMS INTEGRATION - SETUP & TEST")
        logger.info("=" * 70)
        
        results = {
            "connection": False,
            "hotels": [],
            "room_types": [],
            "availability": []
        }
        
        try:
            # Test 1: Connection
            results["connection"] = await self.test_connection()
            
            if not results["connection"]:
                logger.error("\n❌ Cannot proceed without successful connection")
                return results
            
            # Test 2: List hotels
            results["hotels"] = await self.get_hotels()
            
            # Test 3: List room types
            results["room_types"] = await self.get_room_types()
            
            # Test 4: Check availability
            results["availability"] = await self.test_availability()
            
            # Test 5: Booking creation (commented out for safety)
            # await self.test_create_test_booking()
            
            # Summary
            logger.info("\n" + "=" * 70)
            logger.info("TEST SUMMARY")
            logger.info("=" * 70)
            logger.info(f"✅ Connection: {'OK' if results['connection'] else 'FAILED'}")
            logger.info(f"✅ Hotels: {len(results['hotels'])} found")
            logger.info(f"✅ Room Types: {len(results['room_types'])} found")
            logger.info(f"✅ Availability: {len(results['availability'])} rooms available")
            
            all_ok = (
                results['connection'] and 
                len(results['hotels']) > 0 and 
                len(results['room_types']) > 0
            )
            
            if all_ok:
                logger.info("\n🎉 QloApps integration is ready!")
            else:
                logger.warning("\n⚠️ Some tests failed. Check configuration.")
            
            return results
            
        except Exception as e:
            logger.error(f"\n❌ Test suite failed: {e}")
            return results
        
        finally:
            if self.client:
                await self.client.close()
    
    async def interactive_setup(self):
        """Interactive setup wizard."""
        logger.info("\n" + "=" * 70)
        logger.info("INTERACTIVE SETUP WIZARD")
        logger.info("=" * 70)
        
        logger.info("\nCurrent configuration:")
        logger.info(f"  PMS Type: {settings.pms_type}")
        logger.info(f"  Base URL: {settings.pms_base_url}")
        logger.info(f"  Hotel ID: {settings.pms_hotel_id}")
        
        logger.info("\nTo update configuration, set these environment variables:")
        logger.info("  export PMS_TYPE=qloapps")
        logger.info("  export PMS_BASE_URL=https://your-qloapps.com")
        logger.info("  export PMS_API_KEY=your_api_key_here")
        logger.info("  export PMS_HOTEL_ID=1")
        
        logger.info("\nOr update your .env file:")
        logger.info("  PMS_TYPE=qloapps")
        logger.info("  PMS_BASE_URL=https://your-qloapps.com")
        logger.info("  PMS_API_KEY=your_api_key_here")
        logger.info("  PMS_HOTEL_ID=1")


async def main():
    """Main entry point."""
    setup = QloAppsSetup()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "test":
            results = await setup.run_all_tests()
            sys.exit(0 if results["connection"] else 1)
        
        elif command == "setup":
            await setup.interactive_setup()
            sys.exit(0)
        
        elif command == "connection":
            success = await setup.test_connection()
            sys.exit(0 if success else 1)
        
        else:
            print(f"Unknown command: {command}")
            print("Usage: python setup_qloapps.py [test|setup|connection]")
            sys.exit(1)
    else:
        # Default: run all tests
        results = await setup.run_all_tests()
        sys.exit(0 if results["connection"] else 1)


if __name__ == "__main__":
    asyncio.run(main())
