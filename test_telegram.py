from src.notifier import TelegramNotifier
from dotenv import load_dotenv
import os

def test_bot():
    load_dotenv()
    print("Iniciando prueba de Telegram...")
    
    # Reload from env as TelegramNotifier init does
    notifier = TelegramNotifier()
    
    if not notifier.enabled:
        print("❌ Error: TOKEN o CHAT_ID no configurados en .env")
        print(f"DEBUG: TOKEN={os.getenv('TELEGRAM_BOT_TOKEN')}")
        print(f"DEBUG: CHAT_ID={os.getenv('TELEGRAM_CHAT_ID')}")
        return

    print(f"✅ Configuración detectada. Enviando mensaje de prueba...")
    success = notifier.send_signal(
        symbol="MONSTRUO_TEST",
        signal="Green",
        price=123456.78,
        reasoning="¡Prueba de conexión exitosa! El Monstruo ya puede hablarte."
    )

    if success:
        print("\n🚀 ¡MENSAJE ENVIADO! Revisa tu Telegram.")
    else:
        print("\n❌ El envío falló.")
        print("IMPORTANTE: Debes entrar a t.me/MBursatil_bot y darle a 'START' (INICIAR) antes de que el bot pueda hablarte.")
        print("Si ya lo hiciste, revisa que el Token y el Id en el .env coincidan exactamente.")

if __name__ == "__main__":
    test_bot()
