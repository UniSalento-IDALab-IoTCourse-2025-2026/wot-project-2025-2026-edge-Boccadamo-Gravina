import asyncio
from config import CONFIG, is_esp32

# ESP32 non ha batteria per mantenere attivo orologio interno, bisogna fare sincronizzazione all'inizio
def sincronizza_orologio_ntp():
    """Sincronizza l'RTC dell'ESP32 tramite NTP server (solo MicroPython)."""
    if not is_esp32:
        return

    import ntptime
    # Opzionale: puoi specificare un server NTP custom se necessario (default: pool.ntp.org)
    # ntptime.host = "pool.ntp.org"
    
    try:
        ntptime.settime()
        print("[NTP] Orologio sincronizzato con successo.")
    except Exception as e:
        print(f"[NTP] Errore sincronizzazione orario: {e}")

def is_wifi_connected() -> bool:
    """Restituisce True se la rete è disponibile (chiamata solo da esp32)."""
    import network
    wlan = network.WLAN(network.STA_IF)
    return wlan.isconnected()

async def assicura_wifi_connesso():
    """Attende la connessione Wi-Fi iniziale prima di proseguire."""
    if not is_esp32:
        return

    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("[Wi-Fi] Connessione in corso a", CONFIG["SSID"], "...")
        wlan.connect(CONFIG["SSID"], CONFIG["PASSWORD"])
        while not wlan.isconnected():
            await asyncio.sleep(0.5)

    print("[Wi-Fi] Connesso! IP:", wlan.ifconfig()[0])
    sincronizza_orologio_ntp()

async def monitora_wifi():
    """Task in background che ripristina il Wi-Fi se cade."""
    if not is_esp32:
        return

    import network
    wlan = network.WLAN(network.STA_IF)

    while True:
        if not wlan.isconnected():
            print("\n[Wi-Fi] Connessione persa! Ripristino in corso...")
            wlan.connect(CONFIG["SSID"], CONFIG["PASSWORD"])
            while not wlan.isconnected():
                await asyncio.sleep(1)
            print("[Wi-Fi] Riconnesso! IP:", wlan.ifconfig()[0])
            
        await asyncio.sleep(5)