"""
Intelligent Reservation Management System
Advanced reservation orchestration with business logic and workflow management
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
import uuid
from decimal import Decimal

from .enhanced_pms_service import EnhancedPMSService, Reservation, Guest, RoomType, Availability
from app.services.nlp.hotel_context_processor import ConversationContext
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# Prometheus metrics
reservation_operations_total = Counter(
    "reservation_operations_total", "Total reservation operations", ["operation", "status"]
)

reservation_processing_time = Histogram(
    "reservation_processing_time_seconds", "Reservation processing time", ["operation"]
)

reservation_success_rate = Gauge("reservation_success_rate", "Reservation success rate")

reservation_revenue_total = Counter("reservation_revenue_total", "Total reservation revenue", ["currency"])


class ReservationWorkflowState(Enum):
    """Reservation workflow states"""

    INQUIRY = "inquiry"
    INFORMATION_GATHERING = "information_gathering"
    AVAILABILITY_CHECK = "availability_check"
    SELECTION = "selection"
    GUEST_DETAILS = "guest_details"
    CONFIRMATION = "confirmation"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class BusinessRule(Enum):
    """Business rules for reservations"""

    MIN_ADVANCE_BOOKING = "min_advance_booking"
    MAX_ADVANCE_BOOKING = "max_advance_booking"
    MIN_STAY_NIGHTS = "min_stay_nights"
    MAX_STAY_NIGHTS = "max_stay_nights"
    MAX_GUESTS_PER_ROOM = "max_guests_per_room"
    BLACKOUT_DATES = "blackout_dates"
    CANCELLATION_POLICY = "cancellation_policy"


@dataclass
class ReservationWorkflow:
    """Tracks reservation workflow progress"""

    workflow_id: str
    session_id: str
    state: ReservationWorkflowState = ReservationWorkflowState.INQUIRY
    current_reservation: Optional[Reservation] = None
    available_options: List[Availability] = field(default_factory=list)
    selected_option: Optional[Availability] = None
    business_rule_violations: List[str] = field(default_factory=list)
    workflow_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class PricingCalculation:
    """Detailed pricing calculation"""

    base_rate: Decimal
    nights: int
    subtotal: Decimal
    taxes: Decimal = Decimal("0")
    fees: Decimal = Decimal("0")
    discounts: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    currency: str = "USD"
    breakdown: Dict[str, Decimal] = field(default_factory=dict)

    def __post_init__(self):
        self.total = self.subtotal + self.taxes + self.fees - self.discounts


class IntelligentReservationManager:
    """Advanced reservation management with intelligent workflows"""

    def __init__(self, pms_service: EnhancedPMSService):
        self.pms_service = pms_service
        self.active_workflows: Dict[str, ReservationWorkflow] = {}

        # Business rules configuration
        self.business_rules = {
            BusinessRule.MIN_ADVANCE_BOOKING: 2,  # hours
            BusinessRule.MAX_ADVANCE_BOOKING: 365,  # days
            BusinessRule.MIN_STAY_NIGHTS: 1,
            BusinessRule.MAX_STAY_NIGHTS: 30,
            BusinessRule.MAX_GUESTS_PER_ROOM: {
                RoomType.STANDARD_SINGLE: 1,
                RoomType.STANDARD_DOUBLE: 2,
                RoomType.DELUXE_DOUBLE: 2,
                RoomType.JUNIOR_SUITE: 4,
                RoomType.EXECUTIVE_SUITE: 4,
                RoomType.PRESIDENTIAL_SUITE: 6,
            },
        }

        # Pricing rules
        self.pricing_rules = {
            "tax_rate": Decimal("0.12"),  # 12% tax
            "service_fee": Decimal("10.00"),  # $10 service fee
            "weekend_markup": Decimal("1.2"),  # 20% weekend markup
            "peak_season_markup": Decimal("1.5"),  # 50% peak season markup
            "early_booking_discount": Decimal("0.9"),  # 10% early booking discount
        }

        # Blackout dates (high demand periods)
        self.blackout_dates = [
            (date(2024, 12, 20), date(2025, 1, 5)),  # Holiday season
            (date(2025, 7, 1), date(2025, 8, 31)),  # Summer peak
        ]

        logger.info("Intelligent Reservation Manager initialized")

    async def start_reservation_workflow(self, session_id: str, context: ConversationContext) -> ReservationWorkflow:
        """Start a new reservation workflow"""

        workflow_id = str(uuid.uuid4())

        workflow = ReservationWorkflow(
            workflow_id=workflow_id, session_id=session_id, state=ReservationWorkflowState.INQUIRY
        )

        # Extract initial data from conversation context
        if context.reservation_context:
            workflow.workflow_data = context.reservation_context.copy()

        self.active_workflows[workflow_id] = workflow

        logger.info(f"Started reservation workflow: {workflow_id}")
        return workflow

    async def process_workflow_step(
        self, workflow_id: str, context: ConversationContext
    ) -> Tuple[ReservationWorkflowState, Dict[str, Any]]:
        """Process next step in reservation workflow"""

        start_time = asyncio.get_event_loop().time()

        try:
            workflow = self.active_workflows.get(workflow_id)
            if not workflow:
                raise ValueError(f"Workflow {workflow_id} not found")

            # Update workflow data with latest context
            workflow.workflow_data.update(context.reservation_context)
            workflow.updated_at = datetime.now()

            # Determine next state based on current state and available data
            next_state, result_data = await self._determine_next_state(workflow, context)

            # Update workflow state
            workflow.state = next_state

            # Update metrics
            processing_time = asyncio.get_event_loop().time() - start_time
            reservation_processing_time.labels(operation="workflow_step").observe(processing_time)

            logger.info(f"Workflow {workflow_id} advanced to state: {next_state.value}")
            return next_state, result_data

        except Exception as e:
            logger.error(f"Error processing workflow step: {e}")
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id].state = ReservationWorkflowState.ERROR
                self.active_workflows[workflow_id].error_message = str(e)

            reservation_operations_total.labels(operation="workflow_step", status="error").inc()

            raise

    async def _determine_next_state(
        self, workflow: ReservationWorkflow, context: ConversationContext
    ) -> Tuple[ReservationWorkflowState, Dict[str, Any]]:
        """Determine next workflow state based on available data"""

        current_state = workflow.state
        data = workflow.workflow_data

        if current_state == ReservationWorkflowState.INQUIRY:
            # Check if we have enough info to check availability
            if self._has_minimum_availability_info(data):
                return ReservationWorkflowState.AVAILABILITY_CHECK, {}
            else:
                return ReservationWorkflowState.INFORMATION_GATHERING, {
                    "missing_fields": self._get_missing_availability_fields(data)
                }

        elif current_state == ReservationWorkflowState.INFORMATION_GATHERING:
            # Check again if we have enough info
            if self._has_minimum_availability_info(data):
                return ReservationWorkflowState.AVAILABILITY_CHECK, {}
            else:
                return ReservationWorkflowState.INFORMATION_GATHERING, {
                    "missing_fields": self._get_missing_availability_fields(data)
                }

        elif current_state == ReservationWorkflowState.AVAILABILITY_CHECK:
            # Perform availability check
            availability_result = await self._check_availability_with_business_rules(workflow)
            workflow.available_options = availability_result["available_options"]
            workflow.business_rule_violations = availability_result["violations"]

            if availability_result["violations"]:
                return ReservationWorkflowState.ERROR, {"violations": availability_result["violations"]}
            elif availability_result["available_options"]:
                return ReservationWorkflowState.SELECTION, {
                    "available_options": availability_result["available_options"]
                }
            else:
                return ReservationWorkflowState.ERROR, {"error": "No availability found for requested dates"}

        elif current_state == ReservationWorkflowState.SELECTION:
            # Check if user has selected an option
            if "selected_room_type" in data:
                selected_option = self._find_selected_option(workflow, data["selected_room_type"])
                if selected_option:
                    workflow.selected_option = selected_option
                    return ReservationWorkflowState.GUEST_DETAILS, {"selected_option": selected_option}

            return ReservationWorkflowState.SELECTION, {"available_options": workflow.available_options}

        elif current_state == ReservationWorkflowState.GUEST_DETAILS:
            # Check if we have complete guest information
            if self._has_complete_guest_info(data):
                return ReservationWorkflowState.CONFIRMATION, {
                    "reservation_summary": await self._generate_reservation_summary(workflow)
                }
            else:
                return ReservationWorkflowState.GUEST_DETAILS, {
                    "missing_guest_fields": self._get_missing_guest_fields(data)
                }

        elif current_state == ReservationWorkflowState.CONFIRMATION:
            # Check for confirmation
            if data.get("confirmed", False):
                return ReservationWorkflowState.PROCESSING, {}
            else:
                return ReservationWorkflowState.CONFIRMATION, {
                    "reservation_summary": await self._generate_reservation_summary(workflow)
                }

        elif current_state == ReservationWorkflowState.PROCESSING:
            # Process the reservation
            reservation_result = await self._process_reservation(workflow)
            workflow.current_reservation = reservation_result["reservation"]

            if reservation_result["success"]:
                workflow.completed_at = datetime.now()
                return ReservationWorkflowState.COMPLETED, {
                    "reservation": reservation_result["reservation"],
                    "confirmation_details": reservation_result["confirmation_details"],
                }
            else:
                return ReservationWorkflowState.ERROR, {"error": reservation_result["error"]}

        # Default: stay in current state
        return current_state, {}

    def _has_minimum_availability_info(self, data: Dict[str, Any]) -> bool:
        """Check if we have minimum info to check availability"""
        required_fields = ["checkin_date", "guest_count"]
        return all(field in data and data[field] for field in required_fields)

    def _get_missing_availability_fields(self, data: Dict[str, Any]) -> List[str]:
        """Get list of missing fields for availability check"""
        required_fields = {"checkin_date": "Check-in date", "guest_count": "Number of guests"}

        missing = []
        for field_name, description in required_fields.items():
            if field_name not in data or not data[field_name]:
                missing.append(description)

        return missing

    def _has_complete_guest_info(self, data: Dict[str, Any]) -> bool:
        """Check if we have complete guest information"""
        required_fields = ["guest_name"]
        return all(field in data and data[field] for field in required_fields)

    def _get_missing_guest_fields(self, data: Dict[str, Any]) -> List[str]:
        """Get list of missing guest information fields"""
        required_fields = {"guest_name": "Guest name", "guest_email": "Email address", "guest_phone": "Phone number"}

        missing = []
        for field_name, description in required_fields.items():
            if field_name not in data or not data[field_name]:
                missing.append(description)

        return missing

    async def _check_availability_with_business_rules(self, workflow: ReservationWorkflow) -> Dict[str, Any]:
        """Check availability and validate against business rules"""

        data = workflow.workflow_data
        violations = []

        # Extract dates
        checkin_date = data.get("checkin_date")
        checkout_date = data.get("checkout_date")

        # If no checkout date, assume 1 night
        if not checkout_date and checkin_date:
            if isinstance(checkin_date, str):
                checkin_date = datetime.fromisoformat(checkin_date).date()
            checkout_date = checkin_date + timedelta(days=1)

        # Convert to date objects if needed
        if isinstance(checkin_date, str):
            checkin_date = datetime.fromisoformat(checkin_date).date()
        if isinstance(checkout_date, str):
            checkout_date = datetime.fromisoformat(checkout_date).date()

        # Validate business rules
        violations.extend(self._validate_business_rules(checkin_date, checkout_date, data))

        if violations:
            return {"available_options": [], "violations": violations}

        # Check availability in PMS
        try:
            guest_count = int(data.get("guest_count", 1))
            adults = min(guest_count, 6)  # Cap adults
            children = max(0, guest_count - adults)

            available_options = await self.pms_service.check_availability(
                checkin_date=checkin_date, checkout_date=checkout_date, adults=adults, children=children
            )

            # Apply pricing calculations
            enhanced_options = []
            for option in available_options:
                if option.available_rooms > 0:
                    pricing = self._calculate_pricing(option, checkin_date, checkout_date)
                    option.rates[0].base_rate = float(pricing.total)
                    enhanced_options.append(option)

            reservation_operations_total.labels(operation="availability_check", status="success").inc()

            return {"available_options": enhanced_options, "violations": []}

        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            reservation_operations_total.labels(operation="availability_check", status="error").inc()

            return {"available_options": [], "violations": [f"Error checking availability: {str(e)}"]}

    def _validate_business_rules(self, checkin_date: date, checkout_date: date, data: Dict[str, Any]) -> List[str]:
        """Validate reservation against business rules"""
        violations = []

        # Check advance booking rules
        days_advance = (checkin_date - date.today()).days
        if days_advance < 0:
            violations.append("Cannot book for past dates")
        elif days_advance > self.business_rules[BusinessRule.MAX_ADVANCE_BOOKING]:
            violations.append(
                f"Cannot book more than {self.business_rules[BusinessRule.MAX_ADVANCE_BOOKING]} days in advance"
            )

        # Check stay duration
        nights = (checkout_date - checkin_date).days
        if nights < self.business_rules[BusinessRule.MIN_STAY_NIGHTS]:
            violations.append(f"Minimum stay is {self.business_rules[BusinessRule.MIN_STAY_NIGHTS]} night(s)")
        elif nights > self.business_rules[BusinessRule.MAX_STAY_NIGHTS]:
            violations.append(f"Maximum stay is {self.business_rules[BusinessRule.MAX_STAY_NIGHTS]} nights")

        # Check blackout dates
        for blackout_start, blackout_end in self.blackout_dates:
            if (checkin_date >= blackout_start and checkin_date <= blackout_end) or (
                checkout_date >= blackout_start and checkout_date <= blackout_end
            ):
                violations.append(f"Requested dates overlap with blackout period ({blackout_start} to {blackout_end})")

        return violations

    def _calculate_pricing(
        self, availability: Availability, checkin_date: date, checkout_date: date
    ) -> PricingCalculation:
        """Calculate detailed pricing for reservation"""

        nights = (checkout_date - checkin_date).days
        base_rate = Decimal(str(availability.rates[0].base_rate))

        # Calculate subtotal
        subtotal = base_rate * nights

        # Apply weekend markup
        weekend_nights = self._count_weekend_nights(checkin_date, checkout_date)
        if weekend_nights > 0:
            weekend_markup = subtotal * (self.pricing_rules["weekend_markup"] - 1) * (weekend_nights / nights)
            subtotal += weekend_markup

        # Apply peak season markup
        if self._is_peak_season(checkin_date):
            subtotal *= self.pricing_rules["peak_season_markup"]

        # Apply early booking discount
        days_advance = (checkin_date - date.today()).days
        if days_advance > 30:  # Book 30+ days in advance
            discount = subtotal * (1 - self.pricing_rules["early_booking_discount"])
        else:
            discount = Decimal("0")

        # Calculate taxes and fees
        taxes = subtotal * self.pricing_rules["tax_rate"]
        fees = self.pricing_rules["service_fee"]

        return PricingCalculation(
            base_rate=base_rate,
            nights=nights,
            subtotal=subtotal,
            taxes=taxes,
            fees=fees,
            discounts=discount,
            currency="USD",
            breakdown={
                "base_rate_per_night": base_rate,
                "nights": Decimal(str(nights)),
                "weekend_nights": Decimal(str(weekend_nights)),
                "tax_rate": self.pricing_rules["tax_rate"],
                "service_fee": fees,
            },
        )

    def _count_weekend_nights(self, checkin_date: date, checkout_date: date) -> int:
        """Count weekend nights in stay"""
        weekend_nights = 0
        current_date = checkin_date

        while current_date < checkout_date:
            if current_date.weekday() in [4, 5]:  # Friday, Saturday
                weekend_nights += 1
            current_date += timedelta(days=1)

        return weekend_nights

    def _is_peak_season(self, checkin_date: date) -> bool:
        """Check if date is in peak season"""
        # Summer peak: June-August
        if checkin_date.month in [6, 7, 8]:
            return True

        # Winter holidays: December 15 - January 15
        if (checkin_date.month == 12 and checkin_date.day >= 15) or (
            checkin_date.month == 1 and checkin_date.day <= 15
        ):
            return True

        return False

    def _find_selected_option(self, workflow: ReservationWorkflow, selected_room_type: str) -> Optional[Availability]:
        """Find selected availability option"""

        for option in workflow.available_options:
            if option.room_type.value == selected_room_type:
                return option

        return None

    async def _generate_reservation_summary(self, workflow: ReservationWorkflow) -> Dict[str, Any]:
        """Generate reservation summary for confirmation"""

        data = workflow.workflow_data
        selected_option = workflow.selected_option

        if not selected_option:
            return {}

        # Calculate final pricing
        checkin_date = data.get("checkin_date")
        checkout_date = data.get("checkout_date")

        if isinstance(checkin_date, str):
            checkin_date = datetime.fromisoformat(checkin_date).date()
        if isinstance(checkout_date, str):
            checkout_date = datetime.fromisoformat(checkout_date).date()

        pricing = self._calculate_pricing(selected_option, checkin_date, checkout_date)

        return {
            "guest_name": data.get("guest_name", ""),
            "room_type": selected_option.room_type.value,
            "checkin_date": checkin_date.isoformat(),
            "checkout_date": checkout_date.isoformat(),
            "nights": pricing.nights,
            "guests": data.get("guest_count", 1),
            "subtotal": float(pricing.subtotal),
            "taxes": float(pricing.taxes),
            "fees": float(pricing.fees),
            "discounts": float(pricing.discounts),
            "total_amount": float(pricing.total),
            "currency": pricing.currency,
        }

    async def _process_reservation(self, workflow: ReservationWorkflow) -> Dict[str, Any]:
        """Process the final reservation"""

        try:
            data = workflow.workflow_data
            selected_option = workflow.selected_option

            # Create guest object
            guest_name_parts = data.get("guest_name", "").split(" ", 1)
            guest = Guest(
                first_name=guest_name_parts[0] if guest_name_parts else "",
                last_name=guest_name_parts[1] if len(guest_name_parts) > 1 else "",
                email=data.get("guest_email", ""),
                phone=data.get("guest_phone", ""),
            )

            # Create reservation object
            reservation = Reservation(
                guest=guest,
                room_type=selected_option.room_type,
                checkin_date=datetime.fromisoformat(data["checkin_date"]).date(),
                checkout_date=datetime.fromisoformat(data["checkout_date"]).date(),
                adults=min(int(data.get("guest_count", 1)), 6),
                children=max(0, int(data.get("guest_count", 1)) - 6),
                special_requests=data.get("special_requests", []),
                source="agente_ia",
            )

            # Calculate final amount
            pricing = self._calculate_pricing(selected_option, reservation.checkin_date, reservation.checkout_date)
            reservation.total_amount = float(pricing.total)
            reservation.currency = pricing.currency

            # Create reservation in PMS
            created_reservation = await self.pms_service.create_reservation(reservation)

            # Update metrics
            reservation_operations_total.labels(operation="create_reservation", status="success").inc()

            reservation_revenue_total.labels(currency=created_reservation.currency).inc(
                created_reservation.total_amount
            )

            return {
                "success": True,
                "reservation": created_reservation,
                "confirmation_details": {
                    "confirmation_number": created_reservation.confirmation_number,
                    "reservation_id": created_reservation.reservation_id,
                    "total_amount": created_reservation.total_amount,
                    "currency": created_reservation.currency,
                },
            }

        except Exception as e:
            logger.error(f"Error processing reservation: {e}")
            reservation_operations_total.labels(operation="create_reservation", status="error").inc()

            return {"success": False, "error": str(e)}

    async def cancel_reservation(self, workflow_id: str, reason: str = "user_cancelled") -> bool:
        """Cancel an active reservation workflow"""

        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return False

        workflow.state = ReservationWorkflowState.CANCELLED
        workflow.workflow_data["cancellation_reason"] = reason
        workflow.completed_at = datetime.now()

        reservation_operations_total.labels(operation="cancel_workflow", status="success").inc()

        logger.info(f"Reservation workflow cancelled: {workflow_id}, reason: {reason}")
        return True

    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get current workflow status"""

        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return None

        return {
            "workflow_id": workflow.workflow_id,
            "session_id": workflow.session_id,
            "state": workflow.state.value,
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat(),
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            "has_available_options": len(workflow.available_options) > 0,
            "selected_option": workflow.selected_option.room_type.value if workflow.selected_option else None,
            "reservation_id": workflow.current_reservation.reservation_id if workflow.current_reservation else None,
            "error_message": workflow.error_message,
        }

    def cleanup_completed_workflows(self, max_age_hours: int = 24):
        """Clean up old completed workflows"""

        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        workflows_to_remove = []

        for workflow_id, workflow in self.active_workflows.items():
            if (
                workflow.state in [ReservationWorkflowState.COMPLETED, ReservationWorkflowState.CANCELLED]
                and workflow.completed_at
                and workflow.completed_at < cutoff_time
            ):
                workflows_to_remove.append(workflow_id)

        for workflow_id in workflows_to_remove:
            del self.active_workflows[workflow_id]

        logger.info(f"Cleaned up {len(workflows_to_remove)} completed workflows")


# Global instance
_reservation_manager = None


def get_reservation_manager(pms_service: EnhancedPMSService) -> IntelligentReservationManager:
    """Get global reservation manager instance"""
    global _reservation_manager
    if _reservation_manager is None:
        _reservation_manager = IntelligentReservationManager(pms_service)
    return _reservation_manager
