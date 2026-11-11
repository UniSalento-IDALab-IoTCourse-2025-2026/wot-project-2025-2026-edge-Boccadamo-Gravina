import network
import uasyncio as asyncio

SSID = "Vodafone-C01900130"
PASSWORD = "KpbZa2psh9HpzKZY"

wlan = network.WLAN(network.STA_IF)
print("eseguito mynetwork")

async def monitora_wifi():
    """Task in background che mantiene attiva la connessione Wi-Fi."""
    print("task mynetwork")

    wlan.active(True)
    while True:
        if not wlan.isconnected():
            print("\n[Wi-Fi] Disconnesso. Tentativo di connessione...")
            wlan.connect(SSID, PASSWORD)
            
            # Attende fino a 10 secondi per la connessione
            for _ in range(10):
                if wlan.isconnected():
                    break
                await asyncio.sleep(1)
                
            if wlan.isconnected():
                print("[Wi-Fi] Connesso! IP:", wlan.ifconfig()[0])
            else:
                print("[Wi-Fi] Riconnessione fallita, ci riprovo a breve...")
                
        # Controlla lo stato ogni 5 secondi
        await asyncio.sleep(5)