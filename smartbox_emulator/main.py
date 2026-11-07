import json
import logging
import os
import random
import time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USERNAME = os.getenv('MQTT_USERNAME')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD')
MQTT_TOPIC_DATA = os.getenv("MQTT_TOPIC", "telemetry/air_quality")
MQTT_TOPIC_STATUS = os.getenv("MQTT_TOPIC_STATUS", "telemetry/status")
DEVICE_ID = os.getenv("DEVICE_ID", "smartbox-001")
INTERVAL_SECONDS = float(os.getenv("INTERVAL_SECONDS", 5))

POLLUTANT_CONFIG = {
    "no2": {"mean": 32.0, "std": 8.0},
    "pm25": {"mean": 18.0, "std": 5.0},
    "o3": {"mean": 55.0, "std": 12.0},
    "pah": {"mean": 0.75, "std": 0.2}
}

def generate_sensor_data() -> dict:
    sensors = {}
    for pollutant, params in POLLUTANT_CONFIG.items():
        val = random.gauss(params["mean"], params["std"])
        sensors[pollutant] = round(max(0.0, val), 2)

    return {
        "device_id": DEVICE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sensors": sensors
    }

"""
Se per test si vuole mandare misurazione anomala:
{
  "device_id": "smartbox-001",
  "timestamp": "2026-11-07T10:30:00.000000+00:00",
  "sensors": {
    "no2": 850.50,
    "pm25": 1240.80,
    "o3": 420.00,
    "pah": 45.30
  }
}
"""

def generate_health_status() -> dict:
    """Simula il report di diagnostica sullo stato dei singoli sensori."""
    return {
        "device_id": DEVICE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "online",
        "battery_level": 98.5,  # percentuale
        "firmware_version": "v1.2.0",
        "sensors_health": {
            "no2": "OK",
            "pm25": "OK",
            "o3": "OK",
            "pah": "OK"
        }
    }

def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=DEVICE_ID)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    # Configurazione MQTT Last Will & Testament (LWT)
    # Se il broker perde il contatto con la Smartbox, pubblicherà questo messaggio su MQTT_TOPIC_STATUS
    lwt_payload = json.dumps({
        "device_id": DEVICE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "offline",
        "reason": "unexpected_disconnection"
    })
    client.will_set(
        topic=MQTT_TOPIC_STATUS,
        payload=lwt_payload,
        qos=1,
        retain=True  # retain=True per conservare l'ultimo stato noto sul broker
    )

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            logging.info(f"Connesso al broker MQTT ({MQTT_BROKER}:{MQTT_PORT})")

            # Pubblica immediatamente lo stato "online" appena la connessione ha successo
            online_payload = json.dumps(generate_health_status())
            client.publish(MQTT_TOPIC_STATUS, online_payload, qos=1, retain=True)
            logging.info(f"Stato Online pubblicato su '{MQTT_TOPIC_STATUS}'")

        else:
            logging.error(f"Connessione fallita, codice: {rc}")

    client.on_connect = on_connect

    # Connessione con tentativi
    connected = False
    while not connected:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            client.loop_start()
            connected = True
        except Exception as e:
            logging.warning(f"Broker non disponibile ({e}). Riprovo tra 3 secondi...")
            time.sleep(3)

    loop_count = 0
    try:
        while True:
            # Invio dati telemetria (inquinanti)
            payload_data = generate_sensor_data()
            client.publish(MQTT_TOPIC_DATA, json.dumps(payload_data), qos=1)
            logging.info(f"Dati inviati -> {payload_data['sensors']}")

            # Invia lo stato di diagnostica ogni N cicli (es. ogni 5 invii di telemetria)
            loop_count += 1
            if loop_count % 5 == 0:
                payload_status = generate_health_status()
                client.publish(MQTT_TOPIC_STATUS, json.dumps(payload_status), qos=1, retain=True)
                logging.info(f"Heartbeat stato inviato -> {payload_status['sensors_health']}")

            time.sleep(INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logging.info("Arresto programmato emulatore...")
    finally:
        # Disconnessione pulita: aggiorna lo stato a offline prima di uscire
        offline_payload = json.dumps({
            "device_id": DEVICE_ID,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "offline",
            "reason": "clean_shutdown"
        })
        client.publish(MQTT_TOPIC_STATUS, offline_payload, qos=1, retain=True)
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
