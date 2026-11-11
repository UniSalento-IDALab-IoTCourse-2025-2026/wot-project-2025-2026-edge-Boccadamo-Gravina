import sys
import json

# Definizione configurazione predefinita
CONFIG = {
    "SSID": "ssid",
    "PASSWORD": "password",
    "MQTT_BROKER": "localhost",
    "MQTT_PORT": 1883,
    "MQTT_USERNAME": None,
    "MQTT_PASSWORD": None,
    "MQTT_TOPIC_DATA": "telemetry/air_quality",
    "MQTT_TOPIC_STATUS": "telemetry/status",
    "DEVICE_ID": "smartbox-001",
    "DEBUG_DELTA_MEAN": 0,
    "INTERVAL_STATUS_SEC": 300,       # 5 minuti
    "INTERVAL_TELEMETRY_SEC": 3600   # 60 minuti
}

is_esp32 = sys.platform == "esp32"

if not is_esp32:
    #  Se siamo su PC (Docker), le variabili di ambiente overrideano il JSON
    import os
    CONFIG["MQTT_BROKER"] = os.getenv("MQTT_BROKER", CONFIG["MQTT_BROKER"])
    CONFIG["MQTT_PORT"] = int(os.getenv("MQTT_PORT", CONFIG["MQTT_PORT"]))
    CONFIG["MQTT_USERNAME"] = os.getenv("MQTT_USERNAME", CONFIG["MQTT_USERNAME"])
    CONFIG["MQTT_PASSWORD"] = os.getenv("MQTT_PASSWORD", CONFIG["MQTT_PASSWORD"])
    CONFIG["MQTT_TOPIC_DATA"] = os.getenv("MQTT_TOPIC", CONFIG["MQTT_TOPIC_DATA"])
    CONFIG["MQTT_TOPIC_STATUS"] = os.getenv("MQTT_TOPIC_STATUS", CONFIG["MQTT_TOPIC_STATUS"])
    CONFIG["DEVICE_ID"] = os.getenv("DEVICE_ID", CONFIG["DEVICE_ID"])
    CONFIG["DEBUG_DELTA_MEAN"] = float(os.getenv("DEBUG_DELTA_MEAN", CONFIG["DEBUG_DELTA_MEAN"]))
    CONFIG["INTERVAL_STATUS_SEC"] = int(os.getenv("INTERVAL_STATUS_SEC", CONFIG["INTERVAL_STATUS_SEC"]))
    CONFIG["INTERVAL_TELEMETRY_SEC"] = int(os.getenv("INTERVAL_TELEMETRY_SEC", CONFIG["INTERVAL_TELEMETRY_SEC"]))


else:
    # Tenta di caricare da file JSON (non c'è os.getenv su ESP32)
    try:
        with open("../.env.json", "r") as f:
            file_config = json.load(f)
            CONFIG.update(file_config)
    except Exception as e:
        print(f"Errore json: {e}")
        pass

POLLUTANT_CONFIG = {
    "no2": {"mean": 32.0 + CONFIG["DEBUG_DELTA_MEAN"], "std": 8.0},
    "pm25": {"mean": 18.0 + CONFIG["DEBUG_DELTA_MEAN"], "std": 5.0},
    "o3": {"mean": 55.0 + CONFIG["DEBUG_DELTA_MEAN"], "std": 12.0},
    "pah": {"mean": 0.75 + CONFIG["DEBUG_DELTA_MEAN"]/10, "std": 0.2}
}
