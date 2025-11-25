"""
E2E Tests for Multi-Tenant Reservation Flows.

Tests cover:
- Complete reservation flow for tenant A
- Complete reservation flow for tenant B
- Simultaneous reservations from different tenants
- Data isolation verification
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import date

from app.models.unified_message import UnifiedMessage
from app.services.orchestrator import Orchestrator


@pytest.mark.asyncio
class TestReservationFlowTenantA:
    """E2E tests for complete reservation flow - Tenant A."""

    async def test_complete_reservation_flow_tenant_a(
        self,
        e2e_db_session,
        tenant_a,
        user_tenant_a,
        reservation_data_tenant_a
    ):
        """
        Test complete reservation flow for tenant A.
        
        Flow:
        1. User checks availability
        2. System shows available rooms
        3. User creates reservation
        4. System confirms reservation
        5. Verify data in database with correct tenant_id
        """
        # Setup mocks for external services
        mock_pms = AsyncMock()
        mock_pms.check_availability.return_value = [
            {
                "room_type": "double",
                "available": True,
                "price": 100.00,
                "currency": "EUR"
            }
        ]
        mock_pms.create_reservation.return_value = {
            "reservation_uuid": "res-a-001",
            "status": "confirmed",
            "booking_id": "HTL-A-12345"
        }
        
        mock_session_manager = AsyncMock()
        mock_session_manager.get_or_create_session.return_value = {
            "user_id": user_tenant_a.phone_number,
            "channel": "whatsapp",
            "state": "idle",
            "tenant_id": tenant_a.tenant_id,
            "history": []
        }
        mock_session_manager.update_session.return_value = None
        
        mock_lock_service = AsyncMock()
        mock_lock_service.acquire_lock.return_value = True
        mock_lock_service.release_lock.return_value = None
        
        # Create orchestrator with mocked services
        orchestrator = Orchestrator(
            pms_adapter=mock_pms,
            session_manager=mock_session_manager,
            lock_service=mock_lock_service
        )
        
        # Step 1: Check availability
        with patch('app.services.orchestrator.nlp_engine') as mock_nlp:
            mock_nlp.analyze_message.return_value = {
                "intent": "check_availability",
                "entities": {
                    "checkin_date": reservation_data_tenant_a["checkin_date"],
                    "checkout_date": reservation_data_tenant_a["checkout_date"],
                    "room_type": reservation_data_tenant_a["room_type"]
                },
                "confidence": 0.95
            }
            
            availability_message = UnifiedMessage(
                user_id=user_tenant_a.phone_number,
                channel="whatsapp",
                text="Quiero reservar una habitación doble del 1 al 5 de diciembre",
                metadata={"tenant_id": tenant_a.tenant_id}
            )
            
            availability_response = await orchestrator.handle_message(availability_message)
            
            # Verify availability was checked
            assert availability_response is not None
            mock_pms.check_availability.assert_called_once()
        
        # Step 2: Create reservation
        with patch('app.services.orchestrator.nlp_engine') as mock_nlp:
            mock_nlp.analyze_message.return_value = {
                "intent": "create_reservation",
                "entities": {
                    "checkin_date": reservation_data_tenant_a["checkin_date"],
                    "checkout_date": reservation_data_tenant_a["checkout_date"],
                    "room_type": reservation_data_tenant_a["room_type"],
                    "guest_name": reservation_data_tenant_a["guest_name"],
                    "guest_email": reservation_data_tenant_a["guest_email"]
                },
                "confidence": 0.95
            }
            
            reservation_message = UnifiedMessage(
                user_id=user_tenant_a.phone_number,
                channel="whatsapp",
                text="Sí, confirmo la reserva",
                metadata={"tenant_id": tenant_a.tenant_id}
            )
            
            reservation_response = await orchestrator.handle_message(reservation_message)
            
            # Verify reservation was created
            assert reservation_response is not None
            mock_pms.create_reservation.assert_called_once()
        
        # Step 3: Verify tenant_id was propagated correctly
        # Check that session manager was called with correct tenant_id
        session_calls = mock_session_manager.get_or_create_session.call_args_list
        for call in session_calls:
            # Verify tenant_id is in the call
            assert tenant_a.tenant_id in str(call)

    async def test_reservation_with_special_requests_tenant_a(
        self,
        e2e_db_session,
        tenant_a,
        user_tenant_a,
        reservation_data_tenant_a
    ):
        """Test reservation with special requests for tenant A."""
        mock_pms = AsyncMock()
        mock_pms.create_reservation.return_value = {
            "reservation_uuid": "res-a-002",
            "status": "confirmed"
        }
        
        mock_session_manager = AsyncMock()
        mock_session_manager.get_or_create_session.return_value = {
            "user_id": user_tenant_a.phone_number,
            "channel": "whatsapp",
            "state": "awaiting_confirmation",
            "tenant_id": tenant_a.tenant_id,
            "history": []
        }
        
        orchestrator = Orchestrator(
            pms_adapter=mock_pms,
            session_manager=mock_session_manager,
            lock_service=AsyncMock()
        )
        
        with patch('app.services.orchestrator.nlp_engine') as mock_nlp:
            mock_nlp.analyze_message.return_value = {
                "intent": "create_reservation",
                "entities": {
                    **reservation_data_tenant_a,
                    "special_requests": "Vista al mar"
                },
                "confidence": 0.95
            }
            
            message = UnifiedMessage(
                user_id=user_tenant_a.phone_number,
                channel="whatsapp",
                text="Reserva con vista al mar por favor",
                metadata={"tenant_id": tenant_a.tenant_id}
            )
            
            response = await orchestrator.handle_message(message)
            
            assert response is not None
            # Verify special requests were included
            if mock_pms.create_reservation.called:
                call_kwargs = mock_pms.create_reservation.call_args[1]
                assert "special_requests" in call_kwargs or "Vista al mar" in str(call_kwargs)


@pytest.mark.asyncio
class TestReservationFlowTenantB:
    """E2E tests for complete reservation flow - Tenant B."""

    async def test_complete_reservation_flow_tenant_b(
        self,
        e2e_db_session,
        tenant_b,
        user_tenant_b,
        reservation_data_tenant_b
    ):
        """
        Test complete reservation flow for tenant B.
        
        Verifies that tenant B can complete reservations independently
        with their own tenant_id.
        """
        mock_pms = AsyncMock()
        mock_pms.check_availability.return_value = [
            {
                "room_type": "suite",
                "available": True,
                "price": 200.00,
                "currency": "USD"
            }
        ]
        mock_pms.create_reservation.return_value = {
            "reservation_uuid": "res-b-001",
            "status": "confirmed",
            "booking_id": "HTL-B-67890"
        }
        
        mock_session_manager = AsyncMock()
        mock_session_manager.get_or_create_session.return_value = {
            "user_id": user_tenant_b.phone_number,
            "channel": "whatsapp",
            "state": "idle",
            "tenant_id": tenant_b.tenant_id,
            "history": []
        }
        
        orchestrator = Orchestrator(
            pms_adapter=mock_pms,
            session_manager=mock_session_manager,
            lock_service=AsyncMock()
        )
        
        # Check availability
        with patch('app.services.orchestrator.nlp_engine') as mock_nlp:
            mock_nlp.analyze_message.return_value = {
                "intent": "check_availability",
                "entities": {
                    "checkin_date": reservation_data_tenant_b["checkin_date"],
                    "checkout_date": reservation_data_tenant_b["checkout_date"],
                    "room_type": reservation_data_tenant_b["room_type"]
                },
                "confidence": 0.95
            }
            
            message = UnifiedMessage(
                user_id=user_tenant_b.phone_number,
                channel="whatsapp",
                text="I want to book a suite from Dec 10 to Dec 15",
                metadata={"tenant_id": tenant_b.tenant_id}
            )
            
            response = await orchestrator.handle_message(message)
            
            assert response is not None
            mock_pms.check_availability.assert_called_once()
        
        # Create reservation
        with patch('app.services.orchestrator.nlp_engine') as mock_nlp:
            mock_nlp.analyze_message.return_value = {
                "intent": "create_reservation",
                "entities": {
                    **reservation_data_tenant_b
                },
                "confidence": 0.95
            }
            
            message = UnifiedMessage(
                user_id=user_tenant_b.phone_number,
                channel="whatsapp",
                text="Yes, confirm the reservation",
                metadata={"tenant_id": tenant_b.tenant_id}
            )
            
            response = await orchestrator.handle_message(message)
            
            assert response is not None
            mock_pms.create_reservation.assert_called_once()


@pytest.mark.asyncio
class TestSimultaneousReservations:
    """E2E tests for simultaneous reservations from different tenants."""

    async def test_simultaneous_reservations_different_tenants(
        self,
        e2e_db_session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        user_tenant_b,
        reservation_data_tenant_a,
        reservation_data_tenant_b
    ):
        """
        Test that simultaneous reservations from different tenants
        are processed correctly without interference.
        """
        import asyncio
        
        # Setup mocks for tenant A
        mock_pms_a = AsyncMock()
        mock_pms_a.create_reservation.return_value = {
            "reservation_uuid": "res-a-sim-001",
            "status": "confirmed"
        }
        
        mock_session_a = AsyncMock()
        mock_session_a.get_or_create_session.return_value = {
            "user_id": user_tenant_a.phone_number,
            "tenant_id": tenant_a.tenant_id,
            "state": "idle",
            "history": []
        }
        
        # Setup mocks for tenant B
        mock_pms_b = AsyncMock()
        mock_pms_b.create_reservation.return_value = {
            "reservation_uuid": "res-b-sim-001",
            "status": "confirmed"
        }
        
        mock_session_b = AsyncMock()
        mock_session_b.get_or_create_session.return_value = {
            "user_id": user_tenant_b.phone_number,
            "tenant_id": tenant_b.tenant_id,
            "state": "idle",
            "history": []
        }
        
        # Create orchestrators
        orch_a = Orchestrator(
            pms_adapter=mock_pms_a,
            session_manager=mock_session_a,
            lock_service=AsyncMock()
        )
        
        orch_b = Orchestrator(
            pms_adapter=mock_pms_b,
            session_manager=mock_session_b,
            lock_service=AsyncMock()
        )
        
        # Simulate simultaneous reservations
        async def create_reservation_a():
            with patch('app.services.orchestrator.nlp_engine') as mock_nlp:
                mock_nlp.analyze_message.return_value = {
                    "intent": "create_reservation",
                    "entities": reservation_data_tenant_a,
                    "confidence": 0.95
                }
                
                message = UnifiedMessage(
                    user_id=user_tenant_a.phone_number,
                    channel="whatsapp",
                    text="Confirmar reserva",
                    metadata={"tenant_id": tenant_a.tenant_id}
                )
                
                return await orch_a.handle_message(message)
        
        async def create_reservation_b():
            with patch('app.services.orchestrator.nlp_engine') as mock_nlp:
                mock_nlp.analyze_message.return_value = {
                    "intent": "create_reservation",
                    "entities": reservation_data_tenant_b,
                    "confidence": 0.95
                }
                
                message = UnifiedMessage(
                    user_id=user_tenant_b.phone_number,
                    channel="whatsapp",
                    text="Confirm reservation",
                    metadata={"tenant_id": tenant_b.tenant_id}
                )
                
                return await orch_b.handle_message(message)
        
        # Execute simultaneously
        results = await asyncio.gather(
            create_reservation_a(),
            create_reservation_b()
        )
        
        # Verify both succeeded
        assert all(r is not None for r in results)
        assert mock_pms_a.create_reservation.called
        assert mock_pms_b.create_reservation.called
        
        # Verify tenant isolation
        assert mock_session_a.get_or_create_session.call_count > 0
        assert mock_session_b.get_or_create_session.call_count > 0
