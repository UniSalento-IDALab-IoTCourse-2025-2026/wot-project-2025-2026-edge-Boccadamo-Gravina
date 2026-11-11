import math
import random
from config import CONFIG, POLLUTANT_CONFIG, is_esp32, get_iso_timestamp

# Funzione helper globale: utilizzabile ovunque senza problemi
def gauss(mu=0.0, sigma=1.0):
    """Genera un numero con distribuzione gaussiana usando Box-Muller."""
    u1 = random.random()
    while u1 == 0:
        u1 = random.random()
    
    u2 = random.random()
    z0 = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    return mu + z0 * sigma

class BaseSensorManager:
    def read_telemetry(self) -> dict:
        raise NotImplementedError

    def read_health(self) -> dict:
        raise NotImplementedError


class SimulatedSensorManager(BaseSensorManager):
    """Generatore di dati simulati per test e ambiente emulato."""

    def read_telemetry(self) -> dict:
        sensors = {}
        for pollutant, params in POLLUTANT_CONFIG.items():
            val = gauss(params["mean"], params["std"])
            sensors[pollutant] = round(max(0.0, val), 2)

        # Valori simulati per temperatura e umidità
        sensors["temperature"] = round(gauss(22.5, 2.0), 1)
        sensors["humidity"] = round(gauss(50.0, 5.0), 1)

        return {
            "device_id": CONFIG["DEVICE_ID"],
            "timestamp": get_iso_timestamp(),
            "sensors": sensors
        }

    def read_health(self) -> dict:
        health = {p: "OK" for p in POLLUTANT_CONFIG}
        health["dht"] = "OK"

        return {
            "device_id": CONFIG["DEVICE_ID"],
            "timestamp": get_iso_timestamp(),
            "status": "online",
            "battery_level": 98.5,
            "firmware_version": "v1.2.0-sim",
            "sensors_health": health
        }


class ESP32HardwareSensorManager(BaseSensorManager):
    """Lettura reale di eventuali sensori su ESP32"""

    def __init__(self, dht_pin: int = 4):
        if is_esp32:
            import machine
            import dht
            self.dht_sensor = dht.DHT11(machine.Pin(dht_pin))
            self.dht_status = "ERROR"

    def read_telemetry(self) -> dict:
        # Inserire le letture dei sensori reali
        sensors = {}
        for pollutant, params in POLLUTANT_CONFIG.items():
            val = gauss(params["mean"], params["std"])
            sensors[pollutant] = round(max(0.0, val), 2)

        if self.dht_sensor is not None:
            try:
                self.dht_sensor.measure()
                sensors["temperature"] = self.dht_sensor.temperature()
                sensors["humidity"] = self.dht_sensor.humidity()
                self.dht_status = "OK"  # Lettura riuscita
            except Exception as e:
                print(f"[SENSORS] Errore lettura DHT: {e}")
                sensors["temperature"] = None
                sensors["humidity"] = None
                self.dht_status = "ERROR"  # Timeout / cavo staccato / errori
        else:
            sensors["temperature"] = None
            sensors["humidity"] = None
            self.dht_status = "ERROR"
            
        return {
            "device_id": CONFIG["DEVICE_ID"],
            "timestamp": get_iso_timestamp(),
            "sensors": sensors
        }

    def read_health(self) -> dict:
        health = {p: "OK" for p in POLLUTANT_CONFIG}
        health["dht"] = self.dht_status

        return {
            "device_id": CONFIG["DEVICE_ID"],
            "timestamp": get_iso_timestamp(),
            "status": "online",
            "battery_level": 100.0,
            "firmware_version": "v1.2.0-hw",
            "sensors_health": health
        }


def get_sensor_manager() -> BaseSensorManager:
    """Factory function: restituisce l'emulatore o l'hardware in base alla configurazione."""
    if not is_esp32:
        print("[SENSORS] Avvio in modalità SIMULATA")
        return SimulatedSensorManager()
    else:
        print("[SENSORS] Avvio in modalità HARDWARE REAL ESP32")
        return ESP32HardwareSensorManager()
