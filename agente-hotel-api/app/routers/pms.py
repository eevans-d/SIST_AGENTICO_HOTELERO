"""
PMS Integration API Router
Complete API interface for Property Management System operations
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field, validator
import logging

from app.services.pms.enhanced_pms_service import (
    EnhancedPMSService, 
    Reservation, 
    Guest, 
    RoomType, 
    ReservationStatus,
    Availability,
    RateInfo,
    PMSError,
    PMSAuthError,
    PMSRateLimitError,
    PMSNotFoundError
)
from app.services.pms.intelligent_reservation_manager import (
    IntelligentReservationManager,
    ReservationWorkflow,
    ReservationWorkflowState,
    get_reservation_manager
)
from app.services.pms.booking_confirmation_service import (
    BookingConfirmationService,
    ConfirmationChannel,
    GuestPreferences,
    get_confirmation_service
)
from app.core.settings import get_settings
from app.core.middleware import limiter
from app.core.security import get_current_user
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/pms", tags=["PMS Integration"])

# Prometheus metrics
pms_api_requests_total = Counter(
    "pms_api_requests_total",
    "Total PMS API requests",
    ["endpoint", "method", "status"]
)

pms_api_duration_seconds = Histogram(
    "pms_api_duration_seconds",
    "PMS API request duration",
    ["endpoint", "method"]
)

# Request/Response Models
class AvailabilityRequest(BaseModel):
    """Availability check request"""
    checkin_date: date = Field(..., description="Check-in date")
    checkout_date: Optional[date] = Field(None, description="Check-out date (defaults to next day)")
    adults: int = Field(1, ge=1, le=6, description="Number of adults")
    children: int = Field(0, ge=0, le=4, description="Number of children")
    room_types: Optional[List[RoomType]] = Field(None, description="Specific room types to check")
    
    @validator('checkout_date', always=True)
    def validate_checkout_date(cls, v, values):
        if v is None and 'checkin_date' in values:
            from datetime import timedelta
            return values['checkin_date'] + timedelta(days=1)
        if v and 'checkin_date' in values and v <= values['checkin_date']:
            raise ValueError('Check-out date must be after check-in date')
        return v

class GuestRequest(BaseModel):
    """Guest information request"""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    phone: str = Field(..., min_length=10, max_length=20)
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = Field(None, max_length=3)
    id_number: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=500)

class ReservationRequest(BaseModel):
    """Reservation creation request"""
    guest: GuestRequest
    room_type: RoomType
    checkin_date: date
    checkout_date: date
    adults: int = Field(1, ge=1, le=6)
    children: int = Field(0, ge=0, le=4)
    special_requests: Optional[List[str]] = Field(default_factory=list)
    source: str = Field("api", max_length=50)
    
    @validator('checkout_date')
    def validate_checkout_date(cls, v, values):
        if 'checkin_date' in values and v <= values['checkin_date']:
            raise ValueError('Check-out date must be after check-in date')
        return v

class ReservationUpdateRequest(BaseModel):
    """Reservation update request"""
    room_type: Optional[RoomType] = None
    checkin_date: Optional[date] = None
    checkout_date: Optional[date] = None
    adults: Optional[int] = Field(None, ge=1, le=6)
    children: Optional[int] = Field(None, ge=0, le=4)
    special_requests: Optional[List[str]] = None
    status: Optional[ReservationStatus] = None

class WorkflowStartRequest(BaseModel):
    """Start reservation workflow request"""
    session_id: str = Field(..., min_length=1)
    initial_context: Dict[str, Any] = Field(default_factory=dict)

class WorkflowStepRequest(BaseModel):
    """Process workflow step request"""
    workflow_id: str = Field(..., min_length=1)
    context_update: Dict[str, Any] = Field(default_factory=dict)

class ConfirmationRequest(BaseModel):
    """Send confirmation request"""
    reservation_id: str = Field(..., min_length=1)
    channels: List[ConfirmationChannel]
    language: str = Field("en", max_length=2)
    timezone: str = Field("UTC", max_length=50)

# Dependency functions
def get_pms_service() -> EnhancedPMSService:
    """Get PMS service instance"""
    settings = get_settings()
    return EnhancedPMSService(pms_type=settings.pms_type)

def get_reservation_manager_dep() -> IntelligentReservationManager:
    """Get reservation manager dependency"""
    pms_service = get_pms_service()
    return get_reservation_manager(pms_service)

def get_confirmation_service_dep() -> BookingConfirmationService:
    """Get confirmation service dependency"""
    from app.services.template_service import get_template_service
    from app.services.whatsapp_client import get_whatsapp_client
    from app.services.gmail_client import get_gmail_client
    
    return get_confirmation_service(
        template_service=get_template_service(),
        whatsapp_client=get_whatsapp_client(),
        gmail_client=get_gmail_client()
    )

# Route handlers
@router.get("/health")
async def health_check():
    """PMS service health check"""
    try:
        pms_service = get_pms_service()
        health_status = await pms_service.health_check()
        
        return {
            "status": "healthy" if health_status["healthy"] else "unhealthy",
            "pms_type": health_status["pms_type"],
            "provider": health_status["provider"],
            "response_time_ms": health_status["response_time_ms"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"PMS health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"PMS service unavailable: {str(e)}")

@router.post("/availability/check")
@limiter.limit("60/minute")
async def check_availability(
    request: AvailabilityRequest,
    pms_service: EnhancedPMSService = Depends(get_pms_service)
):
    """Check room availability"""
    
    start_time = datetime.now()
    
    try:
        available_rooms = await pms_service.check_availability(
            checkin_date=request.checkin_date,
            checkout_date=request.checkout_date,
            adults=request.adults,
            children=request.children,
            room_types=request.room_types
        )
        
        # Update metrics
        duration = (datetime.now() - start_time).total_seconds()
        pms_api_duration_seconds.labels(
            endpoint="availability_check",
            method="POST"
        ).observe(duration)
        
        pms_api_requests_total.labels(
            endpoint="availability_check",
            method="POST",
            status="success"
        ).inc()
        
        return {
            "checkin_date": request.checkin_date.isoformat(),
            "checkout_date": request.checkout_date.isoformat(),
            "adults": request.adults,
            "children": request.children,
            "available_rooms": [
                {
                    "room_type": room.room_type.value,
                    "available_count": room.available_rooms,
                    "rates": [
                        {
                            "rate_plan": rate.rate_plan,
                            "base_rate": rate.base_rate,
                            "currency": rate.currency,
                            "includes_breakfast": rate.includes_breakfast,
                            "includes_wifi": rate.includes_wifi,
                            "cancellation_policy": rate.cancellation_policy
                        }
                        for rate in room.rates
                    ]
                }
                for room in available_rooms
            ],
            "query_time": duration
        }
        
    except PMSAuthError as e:
        pms_api_requests_total.labels(
            endpoint="availability_check",
            method="POST",
            status="auth_error"
        ).inc()
        raise HTTPException(status_code=401, detail=str(e))
    
    except PMSRateLimitError as e:
        pms_api_requests_total.labels(
            endpoint="availability_check",
            method="POST",
            status="rate_limit"
        ).inc()
        raise HTTPException(status_code=429, detail=str(e))
    
    except PMSError as e:
        pms_api_requests_total.labels(
            endpoint="availability_check",
            method="POST",
            status="pms_error"
        ).inc()
        raise HTTPException(status_code=502, detail=str(e))
    
    except Exception as e:
        logger.error(f"Availability check failed: {e}")
        pms_api_requests_total.labels(
            endpoint="availability_check",
            method="POST",
            status="error"
        ).inc()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/reservations")
@limiter.limit("30/minute")
async def create_reservation(
    request: ReservationRequest,
    background_tasks: BackgroundTasks,
    pms_service: EnhancedPMSService = Depends(get_pms_service),
    confirmation_service: BookingConfirmationService = Depends(get_confirmation_service_dep)
):
    """Create new reservation"""
    
    start_time = datetime.now()
    
    try:
        # Create guest object
        guest = Guest(
            first_name=request.guest.first_name,
            last_name=request.guest.last_name,
            email=request.guest.email,
            phone=request.guest.phone,
            date_of_birth=request.guest.date_of_birth,
            nationality=request.guest.nationality,
            id_number=request.guest.id_number,
            address=request.guest.address
        )
        
        # Create reservation object
        reservation = Reservation(
            guest=guest,
            room_type=request.room_type,
            checkin_date=request.checkin_date,
            checkout_date=request.checkout_date,
            adults=request.adults,
            children=request.children,
            special_requests=request.special_requests,
            source=request.source
        )
        
        # Create reservation in PMS
        created_reservation = await pms_service.create_reservation(reservation)
        
        # Schedule confirmation sending in background
        background_tasks.add_task(
            send_reservation_confirmation,
            created_reservation,
            confirmation_service,
            [ConfirmationChannel.EMAIL, ConfirmationChannel.WHATSAPP]
        )
        
        # Update metrics
        duration = (datetime.now() - start_time).total_seconds()
        pms_api_duration_seconds.labels(
            endpoint="create_reservation",
            method="POST"
        ).observe(duration)
        
        pms_api_requests_total.labels(
            endpoint="create_reservation",
            method="POST",
            status="success"
        ).inc()
        
        return {
            "reservation_id": created_reservation.reservation_id,
            "confirmation_number": created_reservation.confirmation_number,
            "status": created_reservation.status.value,
            "guest_name": f"{created_reservation.guest.first_name} {created_reservation.guest.last_name}",
            "room_type": created_reservation.room_type.value,
            "checkin_date": created_reservation.checkin_date.isoformat(),
            "checkout_date": created_reservation.checkout_date.isoformat(),
            "total_amount": created_reservation.total_amount,
            "currency": created_reservation.currency,
            "created_at": created_reservation.created_at.isoformat(),
            "confirmation_sending": True
        }
        
    except PMSError as e:
        pms_api_requests_total.labels(
            endpoint="create_reservation",
            method="POST",
            status="pms_error"
        ).inc()
        raise HTTPException(status_code=502, detail=str(e))
    
    except Exception as e:
        logger.error(f"Reservation creation failed: {e}")
        pms_api_requests_total.labels(
            endpoint="create_reservation",
            method="POST",
            status="error"
        ).inc()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/reservations/{reservation_id}")
async def get_reservation(
    reservation_id: str,
    pms_service: EnhancedPMSService = Depends(get_pms_service)
):
    """Get reservation by ID"""
    
    try:
        reservation = await pms_service.get_reservation(reservation_id)
        
        if not reservation:
            raise HTTPException(status_code=404, detail="Reservation not found")
        
        pms_api_requests_total.labels(
            endpoint="get_reservation",
            method="GET",
            status="success"
        ).inc()
        
        return {
            "reservation_id": reservation.reservation_id,
            "confirmation_number": reservation.confirmation_number,
            "status": reservation.status.value,
            "guest": {
                "first_name": reservation.guest.first_name,
                "last_name": reservation.guest.last_name,
                "email": reservation.guest.email,
                "phone": reservation.guest.phone
            },
            "room_type": reservation.room_type.value,
            "checkin_date": reservation.checkin_date.isoformat(),
            "checkout_date": reservation.checkout_date.isoformat(),
            "adults": reservation.adults,
            "children": reservation.children,
            "special_requests": reservation.special_requests,
            "total_amount": reservation.total_amount,
            "currency": reservation.currency,
            "created_at": reservation.created_at.isoformat(),
            "updated_at": reservation.updated_at.isoformat() if reservation.updated_at else None
        }
        
    except PMSNotFoundError:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    except PMSError as e:
        pms_api_requests_total.labels(
            endpoint="get_reservation",
            method="GET",
            status="pms_error"
        ).inc()
        raise HTTPException(status_code=502, detail=str(e))
    
    except Exception as e:
        logger.error(f"Get reservation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/reservations/{reservation_id}")
@limiter.limit("30/minute")
async def update_reservation(
    reservation_id: str,
    request: ReservationUpdateRequest,
    pms_service: EnhancedPMSService = Depends(get_pms_service)
):
    """Update existing reservation"""
    
    try:
        # Get current reservation
        current_reservation = await pms_service.get_reservation(reservation_id)
        if not current_reservation:
            raise HTTPException(status_code=404, detail="Reservation not found")
        
        # Prepare update data
        update_data = {}
        if request.room_type is not None:
            update_data['room_type'] = request.room_type
        if request.checkin_date is not None:
            update_data['checkin_date'] = request.checkin_date
        if request.checkout_date is not None:
            update_data['checkout_date'] = request.checkout_date
        if request.adults is not None:
            update_data['adults'] = request.adults
        if request.children is not None:
            update_data['children'] = request.children
        if request.special_requests is not None:
            update_data['special_requests'] = request.special_requests
        if request.status is not None:
            update_data['status'] = request.status
        
        # Update reservation
        updated_reservation = await pms_service.update_reservation(reservation_id, update_data)
        
        pms_api_requests_total.labels(
            endpoint="update_reservation",
            method="PUT",
            status="success"
        ).inc()
        
        return {
            "reservation_id": updated_reservation.reservation_id,
            "confirmation_number": updated_reservation.confirmation_number,
            "status": updated_reservation.status.value,
            "updated_at": updated_reservation.updated_at.isoformat()
        }
        
    except PMSNotFoundError:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    except PMSError as e:
        pms_api_requests_total.labels(
            endpoint="update_reservation",
            method="PUT",
            status="pms_error"
        ).inc()
        raise HTTPException(status_code=502, detail=str(e))
    
    except Exception as e:
        logger.error(f"Update reservation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/reservations/{reservation_id}")
@limiter.limit("20/minute")
async def cancel_reservation(
    reservation_id: str,
    reason: str = Query(default="user_cancelled", max_length=200),
    pms_service: EnhancedPMSService = Depends(get_pms_service)
):
    """Cancel reservation"""
    
    try:
        success = await pms_service.cancel_reservation(reservation_id, reason)
        
        if not success:
            raise HTTPException(status_code=404, detail="Reservation not found or cannot be cancelled")
        
        pms_api_requests_total.labels(
            endpoint="cancel_reservation",
            method="DELETE",
            status="success"
        ).inc()
        
        return {
            "reservation_id": reservation_id,
            "status": "cancelled",
            "reason": reason,
            "cancelled_at": datetime.now().isoformat()
        }
        
    except PMSError as e:
        pms_api_requests_total.labels(
            endpoint="cancel_reservation",
            method="DELETE",
            status="pms_error"
        ).inc()
        raise HTTPException(status_code=502, detail=str(e))
    
    except Exception as e:
        logger.error(f"Cancel reservation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Workflow Management Endpoints
@router.post("/workflows/start")
@limiter.limit("30/minute")
async def start_reservation_workflow(
    request: WorkflowStartRequest,
    reservation_manager: IntelligentReservationManager = Depends(get_reservation_manager_dep)
):
    """Start new reservation workflow"""
    
    try:
        from app.services.nlp.hotel_context_processor import ConversationContext
        
        # Create context from request
        context = ConversationContext(
            session_id=request.session_id,
            reservation_context=request.initial_context
        )
        
        workflow = await reservation_manager.start_reservation_workflow(
            request.session_id, context
        )
        
        return {
            "workflow_id": workflow.workflow_id,
            "session_id": workflow.session_id,
            "state": workflow.state.value,
            "created_at": workflow.created_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Start workflow failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/workflows/{workflow_id}/step")
@limiter.limit("60/minute")
async def process_workflow_step(
    workflow_id: str,
    request: WorkflowStepRequest,
    reservation_manager: IntelligentReservationManager = Depends(get_reservation_manager_dep)
):
    """Process next workflow step"""
    
    try:
        from app.services.nlp.hotel_context_processor import ConversationContext
        
        # Create context from request
        context = ConversationContext(
            session_id="", # Will be updated by workflow
            reservation_context=request.context_update
        )
        
        next_state, result_data = await reservation_manager.process_workflow_step(
            workflow_id, context
        )
        
        return {
            "workflow_id": workflow_id,
            "current_state": next_state.value,
            "result_data": result_data,
            "updated_at": datetime.now().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        logger.error(f"Process workflow step failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/workflows/{workflow_id}/status")
async def get_workflow_status(
    workflow_id: str,
    reservation_manager: IntelligentReservationManager = Depends(get_reservation_manager_dep)
):
    """Get workflow status"""
    
    try:
        status = await reservation_manager.get_workflow_status(workflow_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return status
        
    except Exception as e:
        logger.error(f"Get workflow status failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/workflows/{workflow_id}")
async def cancel_workflow(
    workflow_id: str,
    reason: str = Query(default="user_cancelled"),
    reservation_manager: IntelligentReservationManager = Depends(get_reservation_manager_dep)
):
    """Cancel workflow"""
    
    try:
        success = await reservation_manager.cancel_reservation(workflow_id, reason)
        
        if not success:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return {
            "workflow_id": workflow_id,
            "status": "cancelled",
            "reason": reason,
            "cancelled_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cancel workflow failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Confirmation Management Endpoints
@router.post("/confirmations/send")
@limiter.limit("20/minute")
async def send_confirmation(
    request: ConfirmationRequest,
    background_tasks: BackgroundTasks,
    pms_service: EnhancedPMSService = Depends(get_pms_service),
    confirmation_service: BookingConfirmationService = Depends(get_confirmation_service_dep)
):
    """Send reservation confirmation"""
    
    try:
        # Get reservation
        reservation = await pms_service.get_reservation(request.reservation_id)
        if not reservation:
            raise HTTPException(status_code=404, detail="Reservation not found")
        
        # Create guest preferences
        guest_preferences = GuestPreferences(
            preferred_language=request.language,
            preferred_channels=request.channels,
            timezone=request.timezone
        )
        
        # Send confirmation in background
        background_tasks.add_task(
            send_reservation_confirmation,
            reservation,
            confirmation_service,
            request.channels,
            guest_preferences
        )
        
        return {
            "reservation_id": request.reservation_id,
            "channels": [channel.value for channel in request.channels],
            "status": "sending",
            "initiated_at": datetime.now().isoformat()
        }
        
    except PMSNotFoundError:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    except Exception as e:
        logger.error(f"Send confirmation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/confirmations/{delivery_id}/status")
async def get_confirmation_status(
    delivery_id: str,
    confirmation_service: BookingConfirmationService = Depends(get_confirmation_service_dep)
):
    """Get confirmation delivery status"""
    
    try:
        status = await confirmation_service.get_delivery_status(delivery_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Delivery not found")
        
        return status
        
    except Exception as e:
        logger.error(f"Get confirmation status failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Background tasks
async def send_reservation_confirmation(
    reservation: Reservation,
    confirmation_service: BookingConfirmationService,
    channels: List[ConfirmationChannel],
    guest_preferences: Optional[GuestPreferences] = None
):
    """Background task to send reservation confirmation"""
    
    try:
        result = await confirmation_service.send_confirmation(
            reservation, channels, guest_preferences
        )
        logger.info(f"Confirmation sent for reservation {reservation.reservation_id}: {result}")
    except Exception as e:
        logger.error(f"Failed to send confirmation for reservation {reservation.reservation_id}: {e}")

# Add router to main app
def include_router(app):
    """Include PMS router in main app"""
    app.include_router(router)