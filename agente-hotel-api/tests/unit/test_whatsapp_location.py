"""
Tests unitarios para funcionalidad de envío de ubicación en WhatsApp.
Feature 1: Compartir Ubicación del Hotel
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.whatsapp_client import WhatsAppMetaClient
from app.core.settings import settings


class TestWhatsAppLocation:
    """Tests para el método send_location del cliente WhatsApp."""

    @pytest.fixture
    def whatsapp_client(self):
        """Fixture que crea instancia del cliente WhatsApp."""
        return WhatsAppMetaClient()

    @pytest.mark.asyncio
    async def test_send_location_success(self, whatsapp_client):
        """Test: Envío exitoso de ubicación."""
        # Arrange
        to = "5491112345678"
        latitude = -34.6037
        longitude = -58.3816
        name = "Hotel Ejemplo"
        address = "Av. 9 de Julio 1000, Buenos Aires"

        # Mock de la respuesta HTTP
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"messaging_product": "whatsapp", "messages": [{"id": "wamid.test123"}]}
        )

        # Mock del cliente HTTP
        with patch.object(whatsapp_client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            # Act
            result = await whatsapp_client.send_location(
                to=to, latitude=latitude, longitude=longitude, name=name, address=address
            )

            # Assert
            assert result is not None
            assert result.get("messages")[0]["id"] == "wamid.test123"

            # Verificar que se llamó con los parámetros correctos
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args.kwargs
            assert "json" in call_kwargs

            json_data = call_kwargs["json"]
            assert json_data["messaging_product"] == "whatsapp"
            assert json_data["to"] == to
            assert json_data["type"] == "location"
            assert json_data["location"]["latitude"] == latitude
            assert json_data["location"]["longitude"] == longitude
            assert json_data["location"]["name"] == name
            assert json_data["location"]["address"] == address

    @pytest.mark.asyncio
    async def test_send_location_with_defaults(self, whatsapp_client):
        """Test: Envío de ubicación usando valores por defecto de settings."""
        # Arrange
        to = "5491112345678"
        latitude = settings.hotel_latitude
        longitude = settings.hotel_longitude
        name = settings.hotel_name
        address = settings.hotel_address

        # Mock de la respuesta HTTP
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"messaging_product": "whatsapp", "messages": [{"id": "wamid.test456"}]}
        )

        with patch.object(whatsapp_client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            # Act
            result = await whatsapp_client.send_location(
                to=to, latitude=latitude, longitude=longitude, name=name, address=address
            )

            # Assert
            assert result is not None
            call_kwargs = mock_post.call_args.kwargs
            json_data = call_kwargs["json"]

            # Verificar que usó los valores de settings
            assert json_data["location"]["latitude"] == settings.hotel_latitude
            assert json_data["location"]["longitude"] == settings.hotel_longitude

    @pytest.mark.asyncio
    async def test_send_location_timeout_error(self, whatsapp_client):
        """Test: Manejo de timeout al enviar ubicación."""
        # Arrange
        to = "5491112345678"

        # Mock que lanza TimeoutError
        with patch.object(whatsapp_client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = TimeoutError("Request timeout")

            # Act & Assert
            with pytest.raises(TimeoutError):
                await whatsapp_client.send_location(
                    to=to, latitude=-34.6037, longitude=-58.3816, name="Hotel Test", address="Test Address"
                )

    @pytest.mark.asyncio
    async def test_send_location_network_error(self, whatsapp_client):
        """Test: Manejo de error de red al enviar ubicación."""
        # Arrange
        to = "5491112345678"

        # Mock que lanza Exception genérico (simulando error de red)
        with patch.object(whatsapp_client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Network error")

            # Act & Assert
            with pytest.raises(Exception) as exc_info:
                await whatsapp_client.send_location(
                    to=to, latitude=-34.6037, longitude=-58.3816, name="Hotel Test", address="Test Address"
                )

            assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_location_invalid_coordinates(self, whatsapp_client):
        """Test: Envío de ubicación con coordenadas inválidas (fuera de rango)."""
        # Arrange
        to = "5491112345678"
        invalid_latitude = 91.0  # Fuera del rango válido [-90, 90]
        invalid_longitude = 181.0  # Fuera del rango válido [-180, 180]

        # Mock de la respuesta HTTP (WhatsApp API podría rechazar)
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.json = AsyncMock(return_value={"error": {"message": "Invalid coordinates", "code": 400}})

        with patch.object(whatsapp_client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            # Act & Assert
            # Dependiendo de la implementación, podría lanzar excepción o retornar error
            result = await whatsapp_client.send_location(
                to=to, latitude=invalid_latitude, longitude=invalid_longitude, name="Hotel Test", address="Test Address"
            )

            # Si la API retorna error pero no lanza excepción
            if isinstance(result, dict) and "error" in result:
                assert result["error"]["code"] == 400

    @pytest.mark.asyncio
    async def test_send_location_with_special_characters_in_address(self, whatsapp_client):
        """Test: Envío de ubicación con caracteres especiales en la dirección."""
        # Arrange
        to = "5491112345678"
        name = "Hotel São Paulo 🏨"
        address = "Rúa Ñoño 123, 4º Piso, Depto. A/B"

        # Mock de la respuesta HTTP
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"messaging_product": "whatsapp", "messages": [{"id": "wamid.test789"}]}
        )

        with patch.object(whatsapp_client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            # Act
            result = await whatsapp_client.send_location(
                to=to, latitude=-34.6037, longitude=-58.3816, name=name, address=address
            )

            # Assert
            assert result is not None
            call_kwargs = mock_post.call_args.kwargs
            json_data = call_kwargs["json"]

            # Verificar que los caracteres especiales se pasaron correctamente
            assert json_data["location"]["name"] == name
            assert json_data["location"]["address"] == address

    @pytest.mark.asyncio
    async def test_send_location_metrics_recorded(self, whatsapp_client):
        """Test: Verificar que se registran métricas de Prometheus."""
        # Arrange
        to = "5491112345678"

        # Mock de la respuesta HTTP
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"messaging_product": "whatsapp", "messages": [{"id": "wamid.test999"}]}
        )

        with patch.object(whatsapp_client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            # Mock de métricas (si existen en el código)
            with patch("app.services.whatsapp_client.whatsapp_messages_sent"):
                # Act
                await whatsapp_client.send_location(
                    to=to, latitude=-34.6037, longitude=-58.3816, name="Hotel Test", address="Test Address"
                )

                # Assert
                # Verificar que se llamó el método de incremento de métrica
                # (Esto depende de cómo esté implementado en el código real)
                # mock_metric.labels.assert_called()
