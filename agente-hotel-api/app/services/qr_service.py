"""
QR Code Service for Hotel Agent API.
Generates QR codes for booking confirmations, check-in, and other hotel services.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any
import qrcode

# Simplified imports - some advanced styling may not be available
try:
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
    from qrcode.image.styles.colorfills import SolidFillColorMask

    ADVANCED_QR_AVAILABLE = True
except ImportError:
    ADVANCED_QR_AVAILABLE = False

from PIL import Image, ImageDraw, ImageFont
import structlog

from app.core.settings import settings

logger = structlog.get_logger(__name__)


class QRService:
    """Service for generating QR codes for hotel bookings and services."""

    def __init__(self):
        # Intentar crear el directorio temporal para QR con tolerancia a fallos
        base_tmp = Path(tempfile.gettempdir())
        preferred = base_tmp / "qr_codes"
        self.temp_dir = preferred
        try:
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            # Fallback 1: directorio en el home del usuario
            logger.warning(
                "qr_service.temp_dir_init_failed_primary",
                temp_dir=str(self.temp_dir),
                error=str(e),
            )
            try:
                self.temp_dir = Path.home() / ".qr_codes"
                self.temp_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e2:
                # Fallback 2: directorio en el cwd del proceso
                logger.warning(
                    "qr_service.temp_dir_init_failed_home",
                    temp_dir=str(self.temp_dir),
                    error=str(e2),
                )
                self.temp_dir = Path.cwd() / "qr_codes"
                # Si esto falla, dejamos que la excepción suba (poco probable)
                self.temp_dir.mkdir(parents=True, exist_ok=True)

        # QR Code styling
        self.qr_config = {
            "version": 1,
            "error_correction": qrcode.constants.ERROR_CORRECT_M,
            "box_size": 10,
            "border": 4,
        }

    def generate_booking_qr(
        self,
        booking_id: str,
        guest_name: str,
        check_in_date: str,
        check_out_date: str,
        room_number: Optional[str] = None,
        hotel_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate QR code for booking confirmation.

        Args:
            booking_id: Unique booking identifier
            guest_name: Name of the guest
            check_in_date: Check-in date (YYYY-MM-DD format)
            check_out_date: Check-out date (YYYY-MM-DD format)
            room_number: Room number if available
            hotel_name: Hotel name for branding

        Returns:
            Dict with QR data and file path
        """
        try:
            # Create QR data payload
            qr_data = {
                "type": "booking_confirmation",
                "booking_id": booking_id,
                "guest_name": guest_name,
                "check_in": check_in_date,
                "check_out": check_out_date,
                "generated_at": datetime.now().isoformat(),
                "hotel": hotel_name or settings.hotel_name,
            }

            if room_number:
                qr_data["room_number"] = room_number

            # Generate QR code
            qr_code = qrcode.QRCode(**self.qr_config)
            qr_code.add_data(json.dumps(qr_data))
            qr_code.make(fit=True)

            # Create styled image - with fallback for basic QR
            if ADVANCED_QR_AVAILABLE:
                img = qr_code.make_image(
                    image_factory=StyledPilImage,
                    module_drawer=RoundedModuleDrawer(),
                    color_mask=SolidFillColorMask(
                        back_color=(255, 255, 255),  # White background
                        front_color=(41, 128, 185),  # Hotel blue
                    ),
                )
            else:
                # Basic QR code if advanced styling not available
                img = qr_code.make_image(fill_color="black", back_color="white")

            # Add hotel branding
            branded_img = self._add_branding(img, qr_data)

            # Save to temp file
            filename = f"booking_{booking_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            file_path = self.temp_dir / filename

            # Asegurar modo RGB/RGBA antes de guardar (algunos generadores devuelven modo '1')
            if getattr(branded_img, "mode", "RGB") not in ("RGB", "RGBA"):
                try:
                    branded_img = branded_img.convert("RGB")
                except Exception:
                    pass

            branded_img.save(file_path, "PNG")

            logger.info(
                "QR code generated successfully", booking_id=booking_id, guest_name=guest_name, file_path=str(file_path)
            )

            return {
                "success": True,
                "qr_data": qr_data,
                "file_path": str(file_path),
                "filename": filename,
                "size_bytes": file_path.stat().st_size,
            }

        except Exception as e:
            logger.error("Failed to generate QR code", booking_id=booking_id, error=str(e), exc_info=True)
            return {"success": False, "error": str(e), "qr_data": None, "file_path": None}

    def generate_checkin_qr(
        self, booking_id: str, room_number: str, access_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate QR code for mobile check-in.

        Args:
            booking_id: Booking identifier
            room_number: Assigned room number
            access_code: Digital access code if available

        Returns:
            Dict with QR data and file path
        """
        try:
            qr_data = {
                "type": "mobile_checkin",
                "booking_id": booking_id,
                "room_number": room_number,
                "generated_at": datetime.now().isoformat(),
                "hotel": settings.hotel_name,
            }

            if access_code:
                qr_data["access_code"] = access_code

            qr_code = qrcode.QRCode(**self.qr_config)
            qr_code.add_data(json.dumps(qr_data))
            qr_code.make(fit=True)

            if ADVANCED_QR_AVAILABLE:
                img = qr_code.make_image(
                    image_factory=StyledPilImage,
                    module_drawer=RoundedModuleDrawer(),
                    color_mask=SolidFillColorMask(
                        back_color=(255, 255, 255),
                        front_color=(46, 204, 113),  # Green for check-in
                    ),
                )
            else:
                img = qr_code.make_image(fill_color="green", back_color="white")

            branded_img = self._add_branding(img, qr_data)

            filename = f"checkin_{booking_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            file_path = self.temp_dir / filename

            # Garantizar modo apropiado
            if getattr(branded_img, "mode", "RGB") not in ("RGB", "RGBA"):
                try:
                    branded_img = branded_img.convert("RGB")
                except Exception:
                    pass

            branded_img.save(file_path, "PNG")

            logger.info(
                "Check-in QR code generated", booking_id=booking_id, room_number=room_number, file_path=str(file_path)
            )

            return {
                "success": True,
                "qr_data": qr_data,
                "file_path": str(file_path),
                "filename": filename,
                "size_bytes": file_path.stat().st_size,
            }

        except Exception as e:
            logger.error("Failed to generate check-in QR code", booking_id=booking_id, error=str(e), exc_info=True)
            return {"success": False, "error": str(e), "qr_data": None, "file_path": None}

    def generate_service_qr(self, service_type: str, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate QR code for hotel services (restaurant, spa, etc.).

        Args:
            service_type: Type of service (restaurant, spa, wifi, etc.)
            service_data: Service-specific data

        Returns:
            Dict with QR data and file path
        """
        try:
            qr_data = {
                "type": f"service_{service_type}",
                "service_data": service_data,
                "generated_at": datetime.now().isoformat(),
                "hotel": settings.hotel_name,
            }

            qr_code = qrcode.QRCode(**self.qr_config)
            qr_code.add_data(json.dumps(qr_data))
            qr_code.make(fit=True)

            # Different colors for different services
            service_colors = {
                "restaurant": (231, 76, 60),  # Red
                "spa": (155, 89, 182),  # Purple
                "wifi": (52, 152, 219),  # Blue
                "gym": (241, 196, 15),  # Yellow
                "concierge": (46, 204, 113),  # Green
            }

            color = service_colors.get(service_type, (52, 73, 94))  # Default gray

            if ADVANCED_QR_AVAILABLE:
                img = qr_code.make_image(
                    image_factory=StyledPilImage,
                    module_drawer=RoundedModuleDrawer(),
                    color_mask=SolidFillColorMask(back_color=(255, 255, 255), front_color=color),
                )
            else:
                img = qr_code.make_image(fill_color="black", back_color="white")

            branded_img = self._add_branding(img, qr_data)

            filename = f"service_{service_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            file_path = self.temp_dir / filename

            # Garantizar modo apropiado
            if getattr(branded_img, "mode", "RGB") not in ("RGB", "RGBA"):
                try:
                    branded_img = branded_img.convert("RGB")
                except Exception:
                    pass

            branded_img.save(file_path, "PNG")

            logger.info("Service QR code generated", service_type=service_type, file_path=str(file_path))

            return {
                "success": True,
                "qr_data": qr_data,
                "file_path": str(file_path),
                "filename": filename,
                "size_bytes": file_path.stat().st_size,
            }

        except Exception as e:
            logger.error("Failed to generate service QR code", service_type=service_type, error=str(e), exc_info=True)
            return {"success": False, "error": str(e), "qr_data": None, "file_path": None}

    def _add_branding(self, qr_img: Image.Image, qr_data: Dict) -> Image.Image:
        """
        Add hotel branding to QR code image.

        Args:
            qr_img: QR code image
            qr_data: QR data for context

        Returns:
            Branded QR code image
        """
        try:
            # Expand canvas for branding
            new_width = qr_img.width + 40
            new_height = qr_img.height + 80  # Space for text

            branded_img = Image.new("RGB", (new_width, new_height), "white")

            # Paste QR code centered
            qr_x = (new_width - qr_img.width) // 2
            qr_y = 40  # Leave space at top for hotel name
            branded_img.paste(qr_img, (qr_x, qr_y))

            # Add text
            draw = ImageDraw.Draw(branded_img)

            # Try to load a font, fallback to default
            try:
                title_font: Any = ImageFont.truetype("arial.ttf", 16)
                subtitle_font: Any = ImageFont.truetype("arial.ttf", 12)
            except OSError:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()

            # Hotel name at top
            hotel_name = qr_data.get("hotel", "Hotel")
            title_bbox = draw.textbbox((0, 0), hotel_name, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (new_width - title_width) // 2
            draw.text((title_x, 10), hotel_name, fill=(52, 73, 94), font=title_font)

            # QR type/purpose at bottom
            qr_type = qr_data.get("type", "").replace("_", " ").title()
            subtitle_bbox = draw.textbbox((0, 0), qr_type, font=subtitle_font)
            subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
            subtitle_x = (new_width - subtitle_width) // 2
            draw.text((subtitle_x, new_height - 25), qr_type, fill=(149, 165, 166), font=subtitle_font)

            return branded_img

        except Exception as e:
            logger.warning("Failed to add branding, returning plain QR", error=str(e))
            return qr_img

    def cleanup_old_qr_codes(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """
        Clean up old QR code files to free disk space.

        Args:
            max_age_hours: Maximum age of files to keep

        Returns:
            Cleanup statistics
        """
        try:
            from datetime import timedelta

            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

            deleted_count = 0
            deleted_size = 0

            for file_path in self.temp_dir.glob("*.png"):
                try:
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_mtime < cutoff_time:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        deleted_count += 1
                        deleted_size += file_size
                except Exception as e:
                    logger.warning("Failed to delete QR file", file_path=str(file_path), error=str(e))

            logger.info(
                "QR code cleanup completed",
                deleted_count=deleted_count,
                deleted_size_mb=round(deleted_size / (1024 * 1024), 2),
                max_age_hours=max_age_hours,
            )

            return {
                "success": True,
                "deleted_count": deleted_count,
                "deleted_size_bytes": deleted_size,
                "deleted_size_mb": round(deleted_size / (1024 * 1024), 2),
            }

        except Exception as e:
            logger.error("QR code cleanup failed", error=str(e), exc_info=True)
            return {"success": False, "error": str(e), "deleted_count": 0}

    def get_qr_stats(self) -> Dict[str, Any]:
        """
        Get statistics about QR code files.

        Returns:
            Statistics dictionary
        """
        try:
            files = list(self.temp_dir.glob("*.png"))
            total_size = sum(f.stat().st_size for f in files)

            # Group by type
            type_counts: Dict[str, int] = {}
            for file_path in files:
                filename = file_path.name
                if filename.startswith("booking_"):
                    type_counts["booking"] = type_counts.get("booking", 0) + 1
                elif filename.startswith("checkin_"):
                    type_counts["checkin"] = type_counts.get("checkin", 0) + 1
                elif filename.startswith("service_"):
                    type_counts["service"] = type_counts.get("service", 0) + 1
                else:
                    type_counts["other"] = type_counts.get("other", 0) + 1

            return {
                "total_files": len(files),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "by_type": type_counts,
                "temp_dir": str(self.temp_dir),
            }

        except Exception as e:
            logger.error("Failed to get QR stats", error=str(e))
            return {"total_files": 0, "total_size_bytes": 0, "error": str(e)}


# Singleton instance
_qr_service = None


def get_qr_service() -> QRService:
    """Get QR service singleton instance."""
    global _qr_service
    if _qr_service is None:
        _qr_service = QRService()
    return _qr_service
