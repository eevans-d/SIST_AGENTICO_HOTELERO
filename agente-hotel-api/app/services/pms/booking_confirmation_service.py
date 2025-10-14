"""
Booking Confirmation and Guest Communication System
Advanced confirmation handling with multi-channel communication
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import qrcode
import io

from .enhanced_pms_service import Reservation
from app.services.template_service import TemplateService
from app.services.whatsapp_client import WhatsAppClient
from app.services.gmail_client import GmailClient
from app.core.retry import retry_with_backoff
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# Prometheus metrics
confirmation_operations_total = Counter(
    "confirmation_operations_total", "Total confirmation operations", ["operation", "channel", "status"]
)

confirmation_delivery_time = Histogram("confirmation_delivery_time_seconds", "Confirmation delivery time", ["channel"])

guest_satisfaction_score = Gauge("guest_satisfaction_score", "Guest satisfaction score", ["reservation_id"])


class ConfirmationChannel(Enum):
    """Confirmation delivery channels"""

    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SMS = "sms"
    VOICE_CALL = "voice_call"
    CHAT = "chat"


class ConfirmationStatus(Enum):
    """Confirmation delivery status"""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DocumentType(Enum):
    """Types of confirmation documents"""

    CONFIRMATION_LETTER = "confirmation_letter"
    RESERVATION_VOUCHER = "reservation_voucher"
    QR_CODE = "qr_code"
    INVOICE = "invoice"
    CHECK_IN_INSTRUCTIONS = "checkin_instructions"
    HOTEL_INFO = "hotel_info"


@dataclass
class ConfirmationDelivery:
    """Tracks confirmation delivery across channels"""

    delivery_id: str
    reservation_id: str
    channel: ConfirmationChannel
    status: ConfirmationStatus = ConfirmationStatus.PENDING
    recipient: str = ""
    message_content: str = ""
    attachments: List[str] = field(default_factory=list)
    delivery_attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_after: Optional[datetime] = None


@dataclass
class ConfirmationDocument:
    """Generated confirmation document"""

    document_id: str
    document_type: DocumentType
    content: Union[str, bytes]
    content_type: str
    filename: str
    size_bytes: int
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class GuestPreferences:
    """Guest communication preferences"""

    preferred_language: str = "en"
    preferred_channels: List[ConfirmationChannel] = field(default_factory=list)
    timezone: str = "UTC"
    communication_frequency: str = "normal"  # low, normal, high
    special_needs: List[str] = field(default_factory=list)


class BookingConfirmationService:
    """Advanced booking confirmation with multi-channel delivery"""

    def __init__(
        self,
        template_service: TemplateService,
        whatsapp_client: Optional[WhatsAppClient] = None,
        gmail_client: Optional[GmailClient] = None,
    ):
        self.template_service = template_service
        self.whatsapp_client = whatsapp_client
        self.gmail_client = gmail_client

        # Active confirmations tracking
        self.active_confirmations: Dict[str, List[ConfirmationDelivery]] = {}

        # Hotel information for confirmations
        self.hotel_info = {
            "name": "Hotel Agente IA",
            "address": "123 Main Street, City, Country",
            "phone": "+1-555-0123",
            "email": "info@hotelagenteia.com",
            "website": "https://hotelagenteia.com",
            "checkin_time": "15:00",
            "checkout_time": "11:00",
            "wifi_password": "WelcomeGuest2024",
            "policies": {
                "cancellation": "Free cancellation up to 24 hours before check-in",
                "pets": "Pet-friendly with additional fee",
                "smoking": "Non-smoking property",
                "children": "Children welcome, cribs available",
            },
        }

        # Confirmation templates by language
        self.confirmation_templates = {
            "en": {
                "subject": "Booking Confirmation - {hotel_name}",
                "greeting": "Dear {guest_name},",
                "confirmation_message": "Thank you for choosing {hotel_name}! Your reservation has been confirmed.",
                "details_header": "Reservation Details:",
                "checkin_instructions": "Check-in Instructions:",
                "contact_info": "Contact Information:",
                "footer": "We look forward to welcoming you!",
            },
            "es": {
                "subject": "Confirmación de Reserva - {hotel_name}",
                "greeting": "Estimado/a {guest_name},",
                "confirmation_message": "¡Gracias por elegir {hotel_name}! Su reserva ha sido confirmada.",
                "details_header": "Detalles de la Reserva:",
                "checkin_instructions": "Instrucciones de Check-in:",
                "contact_info": "Información de Contacto:",
                "footer": "¡Esperamos recibirle pronto!",
            },
        }

        logger.info("Booking Confirmation Service initialized")

    async def send_confirmation(
        self,
        reservation: Reservation,
        channels: List[ConfirmationChannel],
        guest_preferences: Optional[GuestPreferences] = None,
    ) -> Dict[str, Any]:
        """Send booking confirmation across multiple channels"""

        start_time = asyncio.get_event_loop().time()

        try:
            # Generate confirmation documents
            documents = await self._generate_confirmation_documents(reservation, guest_preferences)

            # Create delivery tasks for each channel
            deliveries = []

            for channel in channels:
                delivery = await self._create_confirmation_delivery(reservation, channel, documents, guest_preferences)
                deliveries.append(delivery)

            # Store active confirmations
            self.active_confirmations[reservation.reservation_id] = deliveries

            # Send confirmations in parallel
            delivery_tasks = []
            for delivery in deliveries:
                task = asyncio.create_task(self._send_confirmation_delivery(delivery))
                delivery_tasks.append(task)

            # Wait for all deliveries
            delivery_results = await asyncio.gather(*delivery_tasks, return_exceptions=True)

            # Process results
            successful_deliveries = 0
            failed_deliveries = 0

            for i, result in enumerate(delivery_results):
                if isinstance(result, Exception):
                    deliveries[i].status = ConfirmationStatus.FAILED
                    deliveries[i].error_message = str(result)
                    failed_deliveries += 1

                    confirmation_operations_total.labels(
                        operation="send_confirmation", channel=deliveries[i].channel.value, status="error"
                    ).inc()
                else:
                    successful_deliveries += 1

                    confirmation_operations_total.labels(
                        operation="send_confirmation", channel=deliveries[i].channel.value, status="success"
                    ).inc()

            # Update metrics
            processing_time = asyncio.get_event_loop().time() - start_time
            confirmation_delivery_time.labels(channel="all").observe(processing_time)

            logger.info(
                f"Confirmation sent for reservation {reservation.reservation_id}: "
                f"{successful_deliveries} successful, {failed_deliveries} failed"
            )

            return {
                "reservation_id": reservation.reservation_id,
                "total_deliveries": len(deliveries),
                "successful_deliveries": successful_deliveries,
                "failed_deliveries": failed_deliveries,
                "delivery_ids": [d.delivery_id for d in deliveries],
                "documents_generated": len(documents),
            }

        except Exception as e:
            logger.error(f"Error sending confirmation: {e}")
            raise

    async def _generate_confirmation_documents(
        self, reservation: Reservation, guest_preferences: Optional[GuestPreferences] = None
    ) -> List[ConfirmationDocument]:
        """Generate all confirmation documents"""

        documents = []
        language = guest_preferences.preferred_language if guest_preferences else "en"

        # Generate confirmation letter
        confirmation_letter = await self._generate_confirmation_letter(reservation, language)
        documents.append(confirmation_letter)

        # Generate QR code for mobile check-in
        qr_code_doc = await self._generate_qr_code(reservation)
        documents.append(qr_code_doc)

        # Generate check-in instructions
        checkin_instructions = await self._generate_checkin_instructions(reservation, language)
        documents.append(checkin_instructions)

        # Generate hotel information document
        hotel_info_doc = await self._generate_hotel_info(reservation, language)
        documents.append(hotel_info_doc)

        return documents

    async def _generate_confirmation_letter(
        self, reservation: Reservation, language: str = "en"
    ) -> ConfirmationDocument:
        """Generate HTML confirmation letter"""

        template = self.confirmation_templates.get(language, self.confirmation_templates["en"])

        # Calculate stay details
        nights = (reservation.checkout_date - reservation.checkin_date).days

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{template["subject"].format(hotel_name=self.hotel_info["name"])}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #1e3a8a; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .details {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .footer {{ background-color: #e5e7eb; padding: 15px; text-align: center; }}
                .qr-section {{ text-align: center; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{self.hotel_info["name"]}</h1>
                <h2>{template["subject"].format(hotel_name=self.hotel_info["name"])}</h2>
            </div>
            
            <div class="content">
                <p>{template["greeting"].format(guest_name=reservation.guest.first_name + " " + reservation.guest.last_name)}</p>
                
                <p>{template["confirmation_message"].format(hotel_name=self.hotel_info["name"])}</p>
                
                <div class="details">
                    <h3>{template["details_header"]}</h3>
                    <p><strong>Confirmation Number:</strong> {reservation.confirmation_number}</p>
                    <p><strong>Guest Name:</strong> {reservation.guest.first_name} {reservation.guest.last_name}</p>
                    <p><strong>Room Type:</strong> {reservation.room_type.value}</p>
                    <p><strong>Check-in Date:</strong> {reservation.checkin_date.strftime("%B %d, %Y")}</p>
                    <p><strong>Check-out Date:</strong> {reservation.checkout_date.strftime("%B %d, %Y")}</p>
                    <p><strong>Number of Nights:</strong> {nights}</p>
                    <p><strong>Guests:</strong> {reservation.adults} adults{", " + str(reservation.children) + " children" if reservation.children > 0 else ""}</p>
                    <p><strong>Total Amount:</strong> {reservation.currency} {reservation.total_amount:.2f}</p>
                </div>
                
                <div class="details">
                    <h3>{template["checkin_instructions"]}</h3>
                    <p><strong>Check-in Time:</strong> {self.hotel_info["checkin_time"]}</p>
                    <p><strong>Check-out Time:</strong> {self.hotel_info["checkout_time"]}</p>
                    <p><strong>Address:</strong> {self.hotel_info["address"]}</p>
                    <p><strong>WiFi Password:</strong> {self.hotel_info["wifi_password"]}</p>
                </div>
                
                <div class="details">
                    <h3>{template["contact_info"]}</h3>
                    <p><strong>Phone:</strong> {self.hotel_info["phone"]}</p>
                    <p><strong>Email:</strong> {self.hotel_info["email"]}</p>
                    <p><strong>Website:</strong> {self.hotel_info["website"]}</p>
                </div>
                
                {self._format_special_requests(reservation.special_requests, language) if reservation.special_requests else ""}
                
                <div class="qr-section">
                    <p><strong>Mobile Check-in QR Code</strong></p>
                    <p>Scan this code with your phone for quick check-in</p>
                    <!-- QR code will be embedded separately -->
                </div>
            </div>
            
            <div class="footer">
                <p>{template["footer"]}</p>
                <p><small>This is an automated confirmation. Please retain for your records.</small></p>
            </div>
        </body>
        </html>
        """

        return ConfirmationDocument(
            document_id=str(uuid.uuid4()),
            document_type=DocumentType.CONFIRMATION_LETTER,
            content=html_content,
            content_type="text/html",
            filename=f"confirmation_{reservation.confirmation_number}.html",
            size_bytes=len(html_content.encode("utf-8")),
        )

    async def _generate_qr_code(self, reservation: Reservation) -> ConfirmationDocument:
        """Generate QR code for mobile check-in"""

        # QR code data
        qr_data = {
            "type": "hotel_checkin",
            "confirmation_number": reservation.confirmation_number,
            "guest_name": f"{reservation.guest.first_name} {reservation.guest.last_name}",
            "checkin_date": reservation.checkin_date.isoformat(),
            "room_type": reservation.room_type.value,
            "hotel": self.hotel_info["name"],
        }

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )

        import json

        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)

        # Create image
        qr_image = qr.make_image(fill_color="black", back_color="white")

        # Convert to bytes
        img_buffer = io.BytesIO()
        qr_image.save(img_buffer, format="PNG")
        img_bytes = img_buffer.getvalue()

        return ConfirmationDocument(
            document_id=str(uuid.uuid4()),
            document_type=DocumentType.QR_CODE,
            content=img_bytes,
            content_type="image/png",
            filename=f"qr_checkin_{reservation.confirmation_number}.png",
            size_bytes=len(img_bytes),
        )

    async def _generate_checkin_instructions(
        self, reservation: Reservation, language: str = "en"
    ) -> ConfirmationDocument:
        """Generate detailed check-in instructions"""

        self.confirmation_templates.get(language, self.confirmation_templates["en"])

        instructions = f"""
        CHECK-IN INSTRUCTIONS
        {self.hotel_info["name"]}
        
        Confirmation Number: {reservation.confirmation_number}
        Guest: {reservation.guest.first_name} {reservation.guest.last_name}
        
        ARRIVAL INFORMATION:
        • Check-in time: {self.hotel_info["checkin_time"]} onwards
        • Address: {self.hotel_info["address"]}
        • Phone: {self.hotel_info["phone"]}
        
        WHAT TO BRING:
        • Government-issued photo ID
        • Credit card for incidentals
        • This confirmation
        
        MOBILE CHECK-IN:
        • Scan the QR code sent with your confirmation
        • Complete mobile check-in 2 hours before arrival
        • Go directly to your room using mobile key
        
        PARKING:
        • Complimentary self-parking available
        • Valet parking: $25/night
        
        AMENITIES:
        • WiFi Password: {self.hotel_info["wifi_password"]}
        • Fitness center: 24/7 access
        • Pool: 6:00 AM - 10:00 PM
        • Room service: 6:00 AM - 11:00 PM
        
        POLICIES:
        • {self.hotel_info["policies"]["cancellation"]}
        • {self.hotel_info["policies"]["pets"]}
        • {self.hotel_info["policies"]["smoking"]}
        
        NEED HELP?
        • Call/Text: {self.hotel_info["phone"]}
        • Email: {self.hotel_info["email"]}
        • Website: {self.hotel_info["website"]}
        
        We look forward to welcoming you!
        """

        return ConfirmationDocument(
            document_id=str(uuid.uuid4()),
            document_type=DocumentType.CHECK_IN_INSTRUCTIONS,
            content=instructions.strip(),
            content_type="text/plain",
            filename=f"checkin_instructions_{reservation.confirmation_number}.txt",
            size_bytes=len(instructions.encode("utf-8")),
        )

    async def _generate_hotel_info(self, reservation: Reservation, language: str = "en") -> ConfirmationDocument:
        """Generate hotel information document"""

        hotel_info_text = f"""
        {self.hotel_info["name"].upper()}
        Your Home Away From Home
        
        LOCATION & CONTACT:
        {self.hotel_info["address"]}
        Phone: {self.hotel_info["phone"]}
        Email: {self.hotel_info["email"]}
        Website: {self.hotel_info["website"]}
        
        HOTEL AMENITIES:
        • Free WiFi throughout the property
        • 24/7 front desk service
        • Fitness center and spa
        • Outdoor swimming pool
        • Business center
        • Restaurant and bar
        • Room service
        • Laundry service
        • Concierge service
        • Airport shuttle (on request)
        
        ROOM FEATURES:
        • Air conditioning
        • Flat-screen TV with cable
        • Mini-fridge
        • Coffee/tea maker
        • Hair dryer
        • Iron and ironing board
        • Safe deposit box
        • Complimentary toiletries
        
        LOCAL ATTRACTIONS:
        • Downtown area: 5 minutes walk
        • Museum district: 10 minutes drive
        • Shopping center: 15 minutes drive
        • Beach: 20 minutes drive
        • Airport: 30 minutes drive
        
        DINING OPTIONS:
        • Azure Restaurant: Fine dining (6:00 PM - 11:00 PM)
        • Casual Café: Light meals (6:00 AM - 2:00 PM)
        • Rooftop Bar: Cocktails and views (5:00 PM - 12:00 AM)
        • Room Service: Available 24/7
        
        BUSINESS SERVICES:
        • Meeting rooms (up to 100 people)
        • Audio/visual equipment
        • High-speed internet
        • Printing and copying
        • Administrative support
        
        POLICIES:
        Check-in: {self.hotel_info["checkin_time"]}
        Check-out: {self.hotel_info["checkout_time"]}
        Cancellation: {self.hotel_info["policies"]["cancellation"]}
        Pets: {self.hotel_info["policies"]["pets"]}
        Smoking: {self.hotel_info["policies"]["smoking"]}
        
        EMERGENCY INFORMATION:
        • Hotel Security: Ext. 911
        • Medical Emergency: Call 911
        • Fire Department: Call 911
        • Police: Call 911
        
        Thank you for choosing {self.hotel_info["name"]}!
        """

        return ConfirmationDocument(
            document_id=str(uuid.uuid4()),
            document_type=DocumentType.HOTEL_INFO,
            content=hotel_info_text.strip(),
            content_type="text/plain",
            filename=f"hotel_info_{self.hotel_info['name'].lower().replace(' ', '_')}.txt",
            size_bytes=len(hotel_info_text.encode("utf-8")),
        )

    def _format_special_requests(self, special_requests: List[str], language: str) -> str:
        """Format special requests section"""

        if not special_requests:
            return ""

        header = "Special Requests:" if language == "en" else "Solicitudes Especiales:"

        requests_html = f'<div class="details"><h3>{header}</h3><ul>'
        for request in special_requests:
            requests_html += f"<li>{request}</li>"
        requests_html += "</ul></div>"

        return requests_html

    async def _create_confirmation_delivery(
        self,
        reservation: Reservation,
        channel: ConfirmationChannel,
        documents: List[ConfirmationDocument],
        guest_preferences: Optional[GuestPreferences] = None,
    ) -> ConfirmationDelivery:
        """Create confirmation delivery for specific channel"""

        delivery_id = str(uuid.uuid4())

        # Determine recipient based on channel
        if channel == ConfirmationChannel.WHATSAPP:
            recipient = reservation.guest.phone
        elif channel == ConfirmationChannel.EMAIL:
            recipient = reservation.guest.email
        else:
            recipient = reservation.guest.phone  # Default to phone

        # Generate channel-specific message
        message_content = await self._generate_channel_message(reservation, channel, documents, guest_preferences)

        return ConfirmationDelivery(
            delivery_id=delivery_id,
            reservation_id=reservation.reservation_id,
            channel=channel,
            recipient=recipient,
            message_content=message_content,
            attachments=[doc.document_id for doc in documents],
        )

    async def _generate_channel_message(
        self,
        reservation: Reservation,
        channel: ConfirmationChannel,
        documents: List[ConfirmationDocument],
        guest_preferences: Optional[GuestPreferences] = None,
    ) -> str:
        """Generate message content for specific channel"""

        language = guest_preferences.preferred_language if guest_preferences else "en"
        template = self.confirmation_templates.get(language, self.confirmation_templates["en"])

        guest_name = f"{reservation.guest.first_name} {reservation.guest.last_name}"
        nights = (reservation.checkout_date - reservation.checkin_date).days

        if channel == ConfirmationChannel.WHATSAPP:
            return f"""🏨 *{template["subject"].format(hotel_name=self.hotel_info["name"])}*

{template["greeting"].format(guest_name=reservation.guest.first_name)}

✅ {template["confirmation_message"].format(hotel_name=self.hotel_info["name"])}

📋 *{template["details_header"]}*
• Confirmation: `{reservation.confirmation_number}`
• Guest: {guest_name}
• Room: {reservation.room_type.value}
• Check-in: {reservation.checkin_date.strftime("%B %d, %Y")}
• Check-out: {reservation.checkout_date.strftime("%B %d, %Y")}
• Nights: {nights}
• Total: {reservation.currency} {reservation.total_amount:.2f}

🔑 *Mobile Check-in Available*
Scan the QR code for quick check-in!

📞 *Contact Us*
{self.hotel_info["phone"]}
{self.hotel_info["email"]}

{template["footer"]} 🌟"""

        elif channel == ConfirmationChannel.EMAIL:
            return f"""Subject: {template["subject"].format(hotel_name=self.hotel_info["name"])}

{template["greeting"].format(guest_name=guest_name)}

{template["confirmation_message"].format(hotel_name=self.hotel_info["name"])}

RESERVATION DETAILS:
Confirmation Number: {reservation.confirmation_number}
Guest Name: {guest_name}
Room Type: {reservation.room_type.value}
Check-in: {reservation.checkin_date.strftime("%B %d, %Y")} at {self.hotel_info["checkin_time"]}
Check-out: {reservation.checkout_date.strftime("%B %d, %Y")} by {self.hotel_info["checkout_time"]}
Number of Nights: {nights}
Guests: {reservation.adults} adults{", " + str(reservation.children) + " children" if reservation.children > 0 else ""}
Total Amount: {reservation.currency} {reservation.total_amount:.2f}

Your confirmation documents are attached to this email.

{template["contact_info"]}
{self.hotel_info["phone"]}
{self.hotel_info["email"]}
{self.hotel_info["website"]}

{template["footer"]}

Best regards,
{self.hotel_info["name"]} Team"""

        else:
            # Default simple message for other channels
            return (
                f"Booking confirmed! Confirmation: {reservation.confirmation_number}. "
                f"Check-in: {reservation.checkin_date.strftime('%B %d, %Y')}. "
                f"Contact: {self.hotel_info['phone']}"
            )

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def _send_confirmation_delivery(self, delivery: ConfirmationDelivery) -> bool:
        """Send confirmation via specific channel"""

        start_time = asyncio.get_event_loop().time()

        try:
            delivery.delivery_attempts += 1

            if delivery.channel == ConfirmationChannel.WHATSAPP:
                if self.whatsapp_client:
                    success = await self._send_whatsapp_confirmation(delivery)
                else:
                    raise ValueError("WhatsApp client not configured")

            elif delivery.channel == ConfirmationChannel.EMAIL:
                if self.gmail_client:
                    success = await self._send_email_confirmation(delivery)
                else:
                    raise ValueError("Gmail client not configured")

            else:
                # Placeholder for other channels
                success = False
                raise ValueError(f"Channel {delivery.channel.value} not implemented")

            if success:
                delivery.status = ConfirmationStatus.SENT
                delivery.sent_at = datetime.now()

            # Update metrics
            processing_time = asyncio.get_event_loop().time() - start_time
            confirmation_delivery_time.labels(channel=delivery.channel.value).observe(processing_time)

            return success

        except Exception as e:
            delivery.status = ConfirmationStatus.FAILED
            delivery.error_message = str(e)

            # Set retry time if not max attempts
            if delivery.delivery_attempts < delivery.max_attempts:
                delivery.retry_after = datetime.now() + timedelta(minutes=5)

            logger.error(f"Failed to send confirmation via {delivery.channel.value}: {e}")
            raise

    async def _send_whatsapp_confirmation(self, delivery: ConfirmationDelivery) -> bool:
        """Send confirmation via WhatsApp"""

        try:
            # Send main message
            message_sent = await self.whatsapp_client.send_message(
                phone_number=delivery.recipient, message=delivery.message_content
            )

            if not message_sent:
                return False

            # Send QR code as attachment if available
            # This would require implementing media sending in WhatsApp client

            return True

        except Exception as e:
            logger.error(f"WhatsApp confirmation failed: {e}")
            return False

    async def _send_email_confirmation(self, delivery: ConfirmationDelivery) -> bool:
        """Send confirmation via email"""

        try:
            # Extract subject from message content
            lines = delivery.message_content.split("\n")
            subject = lines[0].replace("Subject: ", "") if lines[0].startswith("Subject: ") else "Booking Confirmation"
            body = "\n".join(lines[1:]) if lines[0].startswith("Subject: ") else delivery.message_content

            # Send email (would need to implement attachment handling)
            email_sent = await self.gmail_client.send_email(to_email=delivery.recipient, subject=subject, body=body)

            return email_sent

        except Exception as e:
            logger.error(f"Email confirmation failed: {e}")
            return False

    async def get_delivery_status(self, delivery_id: str) -> Optional[Dict[str, Any]]:
        """Get status of specific delivery"""

        for deliveries in self.active_confirmations.values():
            for delivery in deliveries:
                if delivery.delivery_id == delivery_id:
                    return {
                        "delivery_id": delivery.delivery_id,
                        "reservation_id": delivery.reservation_id,
                        "channel": delivery.channel.value,
                        "status": delivery.status.value,
                        "recipient": delivery.recipient,
                        "delivery_attempts": delivery.delivery_attempts,
                        "created_at": delivery.created_at.isoformat(),
                        "sent_at": delivery.sent_at.isoformat() if delivery.sent_at else None,
                        "delivered_at": delivery.delivered_at.isoformat() if delivery.delivered_at else None,
                        "error_message": delivery.error_message,
                    }

        return None

    async def retry_failed_deliveries(self) -> Dict[str, Any]:
        """Retry failed deliveries that are ready for retry"""

        retried_count = 0
        successful_retries = 0
        now = datetime.now()

        for deliveries in self.active_confirmations.values():
            for delivery in deliveries:
                if (
                    delivery.status == ConfirmationStatus.FAILED
                    and delivery.delivery_attempts < delivery.max_attempts
                    and delivery.retry_after
                    and delivery.retry_after <= now
                ):
                    try:
                        retried_count += 1
                        success = await self._send_confirmation_delivery(delivery)
                        if success:
                            successful_retries += 1
                    except Exception as e:
                        logger.error(f"Retry failed for delivery {delivery.delivery_id}: {e}")

        logger.info(f"Retried {retried_count} deliveries, {successful_retries} successful")

        return {
            "retried_count": retried_count,
            "successful_retries": successful_retries,
            "failed_retries": retried_count - successful_retries,
        }


# Global instance
_confirmation_service = None


def get_confirmation_service(
    template_service: TemplateService,
    whatsapp_client: Optional[WhatsAppClient] = None,
    gmail_client: Optional[GmailClient] = None,
) -> BookingConfirmationService:
    """Get global confirmation service instance"""
    global _confirmation_service
    if _confirmation_service is None:
        _confirmation_service = BookingConfirmationService(template_service, whatsapp_client, gmail_client)
    return _confirmation_service
