import sys
import select
import asyncio

from config import CONFIG, is_esp32
from sensors import get_sensor_manager
from mqtt_client import DynamicMQTTClient


# Inizializzazione moduli
sensor_mgr = get_sensor_manager()
mqtt_mgr = DynamicMQTTClient()

# Evento asincrono per coordinare l'arresto pulito dell'applicazione
stop_event = asyncio.Event()


async def task_status_heartbeat():
    """Invia lo stato diagnostico ogni N secondi (default 300s)."""
    interval = CONFIG["INTERVAL_STATUS_SEC"]
    while not stop_event.is_set():
        try:
            health_data = sensor_mgr.read_health()
            mqtt_mgr.publish(CONFIG["MQTT_TOPIC_STATUS"], health_data, retain=True)
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
        try:
            telemetry_data = sensor_mgr.read_telemetry()
            mqtt_mgr.publish(CONFIG["MQTT_TOPIC_DATA"], telemetry_data)
            print(f"[TELEMETRY] Dati inviati -> {telemetry_data['sensors']}")
        except Exception as e:
            print(f"[TELEMETRY] Errore invio: {e}")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass


# async def task_serial_input():
#     """Gestisce la shell interattiva da STDIN/Seriale in modo totalmente NON bloccante."""
#     print("[SHELL] Console attiva. Digita 'help' per i comandi.")

#     if is_esp32:
#         import uselect
#         spoll = uselect.poll()
#         spoll.register(sys.stdin, uselect.POLLIN)

#         while not stop_event.is_set():
#             if spoll.poll(0):
#                 cmd = sys.stdin.readline().strip().lower()
#                 _process_command(cmd)
#             await asyncio.sleep(0.2)
#     else:
#         # Se il terminale non è interattivo (es. container senza tty)
#         if not sys.stdin.isatty():
#             print("[SHELL] Terminale non interattivo. Shell disabilitata.")
#             return

#         # Lettura non bloccante nativa per Linux/Docker tramite select()
#         while not stop_event.is_set():
#             # Controlla se ci sono caratteri pronti su STDIN senza bloccare la CPU
#             rlist, _, _ = select.select([sys.stdin], [], [], 0)
#             if rlist:
#                 try:
#                     line = sys.stdin.readline()
#                     if not line:  # Rileva EOF (Ctrl+D)
#                         print("\n[SHELL] STDIN chiuso (EOF).")
#                         stop_event.set()
#                         break
#                     _process_command(line.strip().lower())
#                 except Exception as e:
#                     print(f"[SHELL] Errore input: {e}")

#             # Cede il controllo al loop di asyncio per 100ms
#             await asyncio.sleep(0.1)


# def _process_command(cmd: str):
#     if cmd in ("exit", "quit", "shutdown"):
#         print("[CMD] Arresto in corso...")
#         stop_event.set()  # Segnala a tutti i task di terminare
#     elif cmd == "status":
#         print("[CMD] Invio immediato dello stato...")
#         mqtt_mgr.publish(CONFIG["MQTT_TOPIC_STATUS"], sensor_mgr.read_health(), retain=True)
#     elif cmd == "read":
#         print("[CMD] Lettura sensori:", sensor_mgr.read_telemetry())
#     elif cmd == "help":
#         print("[CMD] Comandi disponibili: 'status', 'read', 'shutdown', 'exit', 'quit', 'help'")
#     elif cmd != "":
#         print(f"[CMD] Comando sconosciuto: '{cmd}'")


def shutdown_handler():
    """Invocato da segnali di sistema OS (SIGINT/SIGTERM)."""
    print("\n[MAIN] Segnale di arresto ricevuto dall'OS.")
    stop_event.set()


async def main():
    tasks = [
        asyncio.create_task(task_status_heartbeat()),
        asyncio.create_task(task_telemetry()),
        # asyncio.create_task(task_serial_input()),
    ]

    # Avvia il monitor Wi-Fi ed esegui la connessione iniziale solo se su ESP32
    if is_esp32:
        from my_network import monitora_wifi
        tasks.append(asyncio.create_task(monitora_wifi()))
        # Diamo un secondo al task Wi-Fi per avviare l'interfaccia
        await asyncio.sleep(1)

    mqtt_mgr.connect()
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
