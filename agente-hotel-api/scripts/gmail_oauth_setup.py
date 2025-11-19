#!/usr/bin/env python3
"""
Gmail OAuth2 Setup Script
Ayuda a obtener el refresh_token para Gmail API.
"""

import argparse
import json
import webbrowser
from urllib.parse import urlencode, parse_qs, urlparse
import http.server
import socketserver
from pathlib import Path
import requests

# Colores
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """Handler para capturar el callback de OAuth2."""
    
    authorization_code = None
    
    def do_GET(self):
        """Captura el código de autorización del callback."""
        query = urlparse(self.path).query
        params = parse_qs(query)
        
        if 'code' in params:
            OAuthCallbackHandler.authorization_code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            success_html = """
            <html>
            <head><title>Autorización Exitosa</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: green;">✓ Autorización Exitosa</h1>
                <p>Puedes cerrar esta ventana y volver a la terminal.</p>
            </body>
            </html>
            """
            self.wfile.write(success_html.encode())
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            error_html = """
            <html>
            <head><title>Error de Autorización</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: red;">✗ Error de Autorización</h1>
                <p>No se recibió el código de autorización.</p>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode())
    
    def log_message(self, format, *args):
        """Silenciar logs del servidor."""
        pass


def start_callback_server(port=8002):
    """Inicia servidor HTTP para capturar callback."""
    print(f"{BLUE}Iniciando servidor de callback en puerto {port}...{RESET}")
    
    handler = OAuthCallbackHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"{GREEN}Servidor listo. Esperando autorización...{RESET}\n")
        
        # Procesar solo una request (el callback)
        httpd.handle_request()
        
        return handler.authorization_code


def get_authorization_url(client_id, redirect_uri, scopes):
    """Genera URL de autorización de Google OAuth2."""
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': ' '.join(scopes),
        'access_type': 'offline',
        'prompt': 'consent',  # Forzar mostrar pantalla de consentimiento
    }
    
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def exchange_code_for_tokens(client_id, client_secret, code, redirect_uri):
    """Intercambia código de autorización por tokens."""
    token_url = "https://oauth2.googleapis.com/token"
    
    data = {
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    }
    
    print(f"{BLUE}Intercambiando código por tokens...{RESET}")
    
    response = requests.post(token_url, data=data)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"{RED}Error al obtener tokens:{RESET}")
        print(response.text)
        return None


def save_credentials(refresh_token, client_id, client_secret, sender_email, env_file):
    """Guarda credenciales en archivo .env."""
    print(f"\n{BLUE}Guardando credenciales en {env_file}...{RESET}")
    
    credentials = f"""
# === Gmail OAuth2 Credentials (generadas automáticamente) ===
GMAIL_CLIENT_ID={client_id}
GMAIL_CLIENT_SECRET={client_secret}
GMAIL_REFRESH_TOKEN={refresh_token}
GMAIL_SENDER_EMAIL={sender_email}
"""
    
    env_path = Path(env_file)
    
    # Leer archivo existente
    if env_path.exists():
        with open(env_path, 'r') as f:
            content = f.read()
        
        # Verificar si ya hay credenciales Gmail
        if 'GMAIL_CLIENT_ID' in content:
            print(f"{YELLOW}⚠ Credenciales Gmail ya existen en {env_file}{RESET}")
            response = input("¿Sobrescribir? (s/n): ")
            if response.lower() != 's':
                print(f"{YELLOW}Operación cancelada{RESET}")
                return False
            
            # Remover credenciales antiguas
            lines = content.split('\n')
            new_lines = []
            skip_section = False
            
            for line in lines:
                if '=== Gmail OAuth2' in line:
                    skip_section = True
                elif skip_section and line.startswith('GMAIL_'):
                    continue
                elif skip_section and not line.strip():
                    skip_section = False
                else:
                    new_lines.append(line)
            
            content = '\n'.join(new_lines)
        
        # Agregar nuevas credenciales
        with open(env_path, 'w') as f:
            f.write(content.rstrip() + '\n' + credentials)
    else:
        # Crear archivo nuevo
        with open(env_path, 'w') as f:
            f.write(credentials)
    
    print(f"{GREEN}✓ Credenciales guardadas exitosamente{RESET}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Setup de Gmail OAuth2 para Agente Hotelero IA"
    )
    parser.add_argument(
        '--client-id',
        required=True,
        help='Client ID de Google Cloud Console'
    )
    parser.add_argument(
        '--client-secret',
        required=True,
        help='Client Secret de Google Cloud Console'
    )
    parser.add_argument(
        '--redirect-uri',
        default='http://localhost:8002/auth/gmail/callback',
        help='Redirect URI configurada en Google Cloud (default: http://localhost:8002/auth/gmail/callback)'
    )
    parser.add_argument(
        '--sender-email',
        help='Email remitente (default: se solicita interactivamente)'
    )
    parser.add_argument(
        '--env-file',
        default='.env',
        help='Archivo .env donde guardar credenciales (default: .env)'
    )
    parser.add_argument(
        '--force-reauth',
        action='store_true',
        help='Forzar re-autenticación aunque ya existan credenciales'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8002,
        help='Puerto para servidor de callback (default: 8002)'
    )
    
    args = parser.parse_args()
    
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}Gmail OAuth2 Setup - Agente Hotelero IA{RESET}")
    print(f"{BOLD}{'='*70}{RESET}\n")
    
    # Scopes necesarios
    scopes = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.readonly',
    ]
    
    # Generar URL de autorización
    auth_url = get_authorization_url(
        client_id=args.client_id,
        redirect_uri=args.redirect_uri,
        scopes=scopes
    )
    
    print(f"{BOLD}Paso 1: Autorizar aplicación{RESET}")
    print(f"Se abrirá tu navegador para autorizar la aplicación.")
    print(f"Si no se abre automáticamente, copia esta URL:\n")
    print(f"{BLUE}{auth_url}{RESET}\n")
    
    input("Presiona Enter para continuar...")
    
    # Abrir navegador
    webbrowser.open(auth_url)
    
    # Iniciar servidor de callback
    port = args.port
    code = start_callback_server(port)
    
    if not code:
        print(f"{RED}✗ No se recibió código de autorización{RESET}")
        return 1
    
    print(f"{GREEN}✓ Código de autorización recibido{RESET}")
    
    # Intercambiar código por tokens
    tokens = exchange_code_for_tokens(
        client_id=args.client_id,
        client_secret=args.client_secret,
        code=code,
        redirect_uri=args.redirect_uri
    )
    
    if not tokens:
        print(f"{RED}✗ Error al obtener tokens{RESET}")
        return 1
    
    refresh_token = tokens.get('refresh_token')
    
    if not refresh_token:
        print(f"{RED}✗ No se recibió refresh_token{RESET}")
        print(f"{YELLOW}Esto puede ocurrir si ya autorizaste la app antes.{RESET}")
        print(f"{YELLOW}Usa --force-reauth para forzar re-autorización.{RESET}")
        return 1
    
    print(f"{GREEN}✓ Tokens obtenidos exitosamente{RESET}")
    
    # Solicitar email remitente si no se proporcionó
    sender_email = args.sender_email
    if not sender_email:
        sender_email = input(f"\n{BOLD}Email remitente{RESET} (ej: reservas@hotel.com): ")
    
    # Guardar credenciales
    success = save_credentials(
        refresh_token=refresh_token,
        client_id=args.client_id,
        client_secret=args.client_secret,
        sender_email=sender_email,
        env_file=args.env_file
    )
    
    if success:
        print(f"\n{BOLD}{'='*70}{RESET}")
        print(f"{GREEN}{BOLD}✓ Setup completado exitosamente{RESET}")
        print(f"{BOLD}{'='*70}{RESET}\n")
        
        print(f"{BOLD}Próximos pasos:{RESET}")
        print(f"1. Verificar credenciales: python scripts/validate_credentials.py")
        print(f"2. Restart de servicios: docker compose restart agente-api")
        print(f"3. Test de envío: pytest tests/integration/test_gmail_integration.py -v\n")
        
        return 0
    else:
        return 1


if __name__ == '__main__':
    exit(main())
