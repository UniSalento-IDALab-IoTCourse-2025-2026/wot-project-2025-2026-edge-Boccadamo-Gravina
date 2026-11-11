import sys
import json
import time

is_esp32 = sys.platform == "esp32"

# In MicroPython l'epoca parte dal 2000 anziché dal 1970 (differenza di 946.684.800 secondi)
MICROPYTHON_EPOCH_OFFSET = 946684800 if is_esp32 else 0

def get_unix_timestamp() -> float:
    """Restituisce sempre il timestamp Unix (secondi dal 1970-01-01)."""
    return time.time() + MICROPYTHON_EPOCH_OFFSET

def get_iso_timestamp() -> str:
    """Restituisce il timestamp formattato ISO 8601 UTC (es. 2026-11-11T10:57:00Z)."""
    if is_esp32:
        # time.gmtime() su MicroPython restituisce (anno, mese, mday, ora, min, sec, wday, yday)
        t = time.gmtime(time.time())
        return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
            t[0], t[1], t[2], t[3], t[4], t[5]
        )
    else:
        # Su CPython usiamo time.strftime
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        
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
    "DEVICE_ID": "smartbox-000",
    "DEBUG_DELTA_MEAN": 0,
    "INTERVAL_STATUS_SEC": 30,
    "INTERVAL_TELEMETRY_SEC": 4
}

def load_config():
    if is_esp32:
        try:
            with open(".env.json", "r") as f:
                CONFIG.update(json.load(f))
                print("[CONFIG] .env.json caricato correttamente")
        except Exception as e:
            print(f"[CONFIG] Impossibile caricare .env.json: {e}")
    else:
        import os
        for key in CONFIG:
            env_val = os.getenv(key)
            if env_val is not None:
                # Type casting automatico
                if isinstance(CONFIG[key], int):
                    CONFIG[key] = int(env_val)
                elif isinstance(CONFIG[key], float):
                    CONFIG[key] = float(env_val)
                else:
                    CONFIG[key] = env_val


load_config()

POLLUTANT_CONFIG = {
    "no2": {"mean": 32.0 + CONFIG["DEBUG_DELTA_MEAN"], "std": 8.0},
    "pm25": {"mean": 18.0 + CONFIG["DEBUG_DELTA_MEAN"], "std": 5.0},
    "o3": {"mean": 55.0 + CONFIG["DEBUG_DELTA_MEAN"], "std": 12.0},
    "pah": {"mean": 0.75 + (CONFIG["DEBUG_DELTA_MEAN"] / 10.0), "std": 0.2}
}