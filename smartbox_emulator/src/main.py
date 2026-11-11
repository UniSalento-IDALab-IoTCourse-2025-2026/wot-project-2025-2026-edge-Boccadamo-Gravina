import sys
import asyncio

from config import CONFIG, is_esp32
from sensors import get_sensor_manager
from mqtt_client import DynamicMQTTClient
from my_network import assicura_wifi_connesso, monitora_wifi

# Inizializzazione moduli
sensor_mgr = get_sensor_manager()
mqtt_mgr = DynamicMQTTClient()

# Evento asincrono per coordinare l'arresto pulito dell'applicazione
stop_event = asyncio.Event()


async def task_status_heartbeat():
    """Invia lo stato diagnostico ogni N secondi (default 300s)."""
    interval = CONFIG["INTERVAL_STATUS_SEC"]
    while not stop_event.is_set():
        if mqtt_mgr.client is None:
            await mqtt_mgr.connect()

        try:
            health_data = sensor_mgr.read_health()
            success = mqtt_mgr.publish(CONFIG["MQTT_TOPIC_STATUS"], health_data, retain=True)
            if success:
                print("[STATUS] Heartbeat inviato")
        except Exception as e:
            print(f"[STATUS] Errore invio: {e}")

        # Attende l'intervallo o si sveglia subito se stop_event viene attivato
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass


async def task_telemetry():
    """Invia la telemetria dei sensori ogni N secondi (default 3600s)."""
    interval = CONFIG["INTERVAL_TELEMETRY_SEC"]
    while not stop_event.is_set():
        if mqtt_mgr.client is None:
            await mqtt_mgr.connect()
        
        try:
            telemetry_data = sensor_mgr.read_telemetry()
            success = mqtt_mgr.publish(CONFIG["MQTT_TOPIC_DATA"], telemetry_data)
            if success:
                print(f"[TELEMETRY] Dati inviati -> {telemetry_data['sensors']}")
        except Exception as e:
            print(f"[TELEMETRY] Errore invio: {e}")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass


def shutdown_handler():
    """Invocato da segnali di sistema OS (SIGINT/SIGTERM)."""
    print("\n[MAIN] Segnale di arresto ricevuto dall'OS.")
    stop_event.set()


async def main():
    await assicura_wifi_connesso()

    tasks = [
        asyncio.create_task(task_status_heartbeat()),
        asyncio.create_task(task_telemetry()),
        asyncio.create_task(monitora_wifi()),
    ]

    await mqtt_mgr.connect()
    mqtt_mgr.publish(CONFIG["MQTT_TOPIC_STATUS"], sensor_mgr.read_health(), retain=True)

    # Gestione segnali OS per Linux/Docker (Ctrl+C / docker stop)
    if not is_esp32:
        import signal
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, shutdown_handler)
            except NotImplementedError:
                pass


    # Il main rimane in attesa finché stop_event non viene attivato
    # La disconnessione pulita al momento può avvenire solo su PC, su ESP32 quando si stacca la corrente basta finisce tutto
    await stop_event.wait()

    print("[MAIN] Chiusura dei task asincroni...")
    for t in tasks:
        t.cancel()

    # Attendiamo la chiusura dei task asincroni (senza bloccarci su eventuali thread bloccati)
    await asyncio.gather(*tasks, return_exceptions=True)

    # Disconnessione MQTT finale
    mqtt_mgr.disconnect()
    print("[MAIN] Applicazione arrestata correttamente.")

    # Termina esplicitamente il processo Python per superare il thread pendente di input()
    if not is_esp32:
        sys.exit(0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
