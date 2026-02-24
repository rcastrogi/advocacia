"""
Petitio Assinador — Aplicativo de bandeja do sistema.

Gerencia o agente local que permite ao Petitio web acessar
o smart card (certificado A3) do advogado.

Funcionalidades:
- Ícone na bandeja do sistema (system tray)
- Menu: Status, Leitores, Sobre, Sair
- Inicia servidor HTTP automaticamente
- Notificações de inserção/remoção de cartão
"""

import logging
import os
import sys
import threading
import time
import webbrowser
from io import BytesIO

logger = logging.getLogger("petitio_assinador")

# Configurar logging
LOG_DIR = os.path.join(os.path.expanduser("~"), ".petitio_assinador")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(LOG_DIR, "petitio_assinador.log"),
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)

# Importações do agente
from api_server import AGENT_PORT, AGENT_VERSION, run_server
from smartcard_service import SmartCardService


def create_icon_image(color: str = "green"):
    """
    Cria imagem do ícone programaticamente (sem arquivo externo).
    Verde = cartão detectado, Vermelho = sem cartão, Amarelo = sem leitor.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    COLORS = {
        "green": (34, 139, 34),
        "red": (220, 53, 69),
        "yellow": (255, 193, 7),
        "blue": (0, 123, 255),
    }

    bg_color = COLORS.get(color, COLORS["green"])

    # Ícone 64x64
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fundo arredondado
    draw.rounded_rectangle(
        [(2, 2), (62, 62)],
        radius=12,
        fill=bg_color,
        outline=(255, 255, 255, 200),
        width=2,
    )

    # Letras "PA" (Petitio Assinador)
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except (OSError, IOError):
        font = ImageFont.load_default()

    draw.text(
        (32, 30),
        "PA",
        fill=(255, 255, 255),
        font=font,
        anchor="mm",
    )

    return img


def create_tray_app():
    """Cria e inicia a aplicação de bandeja do sistema."""
    try:
        import pystray
        from pystray import MenuItem as Item
    except ImportError:
        logger.error(
            "pystray não instalado. Execute: pip install pystray Pillow"
        )
        print("ERRO: pystray não instalado.")
        print("Execute: pip install pystray Pillow")
        sys.exit(1)

    # Instância do serviço de smart card
    sc = SmartCardService()

    # Estado do agente
    state = {
        "server_thread": None,
        "monitor_thread": None,
        "running": True,
        "last_card_status": None,
        "icon": None,
    }

    # ================================================================
    # CALLBACKS DO MENU
    # ================================================================

    def on_status(icon, item):
        """Mostra status do agente."""
        sc_status = sc.get_status()

        if sc_status.get("card_detected"):
            msg = (
                f"🟢 Petitio Assinador v{AGENT_VERSION}\n"
                f"Servidor: http://127.0.0.1:{AGENT_PORT}\n\n"
                f"Smart Card: Detectado\n"
                f"Leitor: {sc_status.get('readers', ['?'])[0]}\n"
                f"Biblioteca PKCS#11: {sc_status.get('pkcs11_library', 'N/A')}"
            )
        elif sc_status.get("readers"):
            msg = (
                f"🟡 Petitio Assinador v{AGENT_VERSION}\n"
                f"Servidor: http://127.0.0.1:{AGENT_PORT}\n\n"
                f"Leitor: {sc_status.get('readers', ['?'])[0]}\n"
                f"Cartão: Não inserido"
            )
        else:
            msg = (
                f"🔴 Petitio Assinador v{AGENT_VERSION}\n"
                f"Servidor: http://127.0.0.1:{AGENT_PORT}\n\n"
                f"Nenhum leitor de smart card detectado.\n"
                f"Conecte o leitor OmniKey e insira o cartão."
            )

        icon.notify(msg, "Petitio Assinador")

    def on_open_petitio(icon, item):
        """Abre o Petitio no navegador."""
        webbrowser.open("https://petitio.onrender.com")

    def on_open_logs(icon, item):
        """Abre pasta de logs."""
        log_file = os.path.join(LOG_DIR, "petitio_assinador.log")
        if sys.platform == "win32":
            os.startfile(log_file)
        else:
            webbrowser.open(f"file://{log_file}")

    def on_about(icon, item):
        """Mostra informações sobre o app."""
        icon.notify(
            f"Petitio Assinador v{AGENT_VERSION}\n"
            "Agente local para assinatura digital com certificado A3.\n\n"
            "© Petitio - Advocacia SaaS\n"
            "Suporta leitores OmniKey, SafeNet e compatíveis.",
            "Sobre",
        )

    def on_quit(icon, item):
        """Encerra o agente."""
        state["running"] = False
        icon.stop()
        logger.info("Petitio Assinador encerrado pelo usuário.")

    # ================================================================
    # MONITOR DE CARTÃO
    # ================================================================

    def monitor_card(icon):
        """Monitora inserção/remoção do cartão em background."""
        while state["running"]:
            try:
                sc_status = sc.get_status()
                card_detected = sc_status.get("card_detected", False)
                has_readers = bool(sc_status.get("readers"))

                # Atualizar ícone baseado no status
                if card_detected:
                    new_color = "green"
                elif has_readers:
                    new_color = "yellow"
                else:
                    new_color = "red"

                new_img = create_icon_image(new_color)
                if new_img and icon.icon != new_img:
                    icon.icon = new_img

                # Notificar mudanças de estado
                if state["last_card_status"] is not None:
                    if card_detected and not state["last_card_status"]:
                        icon.notify(
                            "Smart card detectado! Pronto para assinar.",
                            "Petitio Assinador",
                        )
                        logger.info("Smart card inserido.")
                    elif not card_detected and state["last_card_status"]:
                        icon.notify(
                            "Smart card removido.",
                            "Petitio Assinador",
                        )
                        logger.info("Smart card removido.")

                state["last_card_status"] = card_detected

            except Exception as e:
                logger.error(f"Erro no monitor de cartão: {e}")

            time.sleep(3)  # Verificar a cada 3 segundos

    # ================================================================
    # SETUP DO TRAY
    # ================================================================

    def setup(icon):
        """Callback de inicialização do ícone."""
        icon.visible = True

        # Iniciar servidor HTTP
        state["server_thread"] = run_server(AGENT_PORT)
        logger.info(f"Servidor iniciado na porta {AGENT_PORT}")

        # Iniciar monitor de cartão
        state["monitor_thread"] = threading.Thread(
            target=monitor_card, args=(icon,), daemon=True
        )
        state["monitor_thread"].start()

        # Notificação inicial
        icon.notify(
            f"Petitio Assinador v{AGENT_VERSION} iniciado!\n"
            f"Servidor: http://127.0.0.1:{AGENT_PORT}",
            "Petitio Assinador",
        )

    # Criar ícone
    icon_image = create_icon_image("blue")  # Azul = inicializando

    menu = pystray.Menu(
        Item("📊 Status", on_status, default=True),
        pystray.Menu.SEPARATOR,
        Item("🌐 Abrir Petitio", on_open_petitio),
        Item("📄 Ver Logs", on_open_logs),
        Item("ℹ️ Sobre", on_about),
        pystray.Menu.SEPARATOR,
        Item("❌ Sair", on_quit),
    )

    icon = pystray.Icon(
        name="petitio_assinador",
        icon=icon_image,
        title=f"Petitio Assinador v{AGENT_VERSION}",
        menu=menu,
    )

    state["icon"] = icon

    logger.info("Iniciando Petitio Assinador...")
    icon.run(setup)


def main():
    """Ponto de entrada principal."""
    # Verificar se já há uma instância rodando
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", AGENT_PORT))
        sock.close()
    except OSError:
        logger.warning(
            f"Porta {AGENT_PORT} já está em uso. "
            "Outra instância do Petitio Assinador pode estar rodando."
        )
        print(
            f"AVISO: Porta {AGENT_PORT} já em uso. "
            "Outra instância pode estar rodando."
        )
        sys.exit(1)

    create_tray_app()


if __name__ == "__main__":
    main()
