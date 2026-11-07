import random
import time
from config import CONFIG, POLLUTANT_CONFIG, is_esp32


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
            val = random.gauss(params["mean"], params["std"])
            sensors[pollutant] = round(max(0.0, val), 2)

        return {
            "device_id": CONFIG["DEVICE_ID"],
            "timestamp": time.time(),
            "sensors": sensors
        }

    def read_health(self) -> dict:
        return {
            "device_id": CONFIG["DEVICE_ID"],
            "timestamp": time.time(),
            "status": "online",
            "battery_level": 98.5,
            "firmware_version": "v1.2.0-sim",
            "sensors_health": {p: "OK" for p in POLLUTANT_CONFIG}
        }


class ESP32HardwareSensorManager(BaseSensorManager):
    """Lettura reale dai sensori su ESP32"""

    def __init__(self):
        if is_esp32:
            import machine
            # Inizializzazione bus I2C/SPI fisici
            # self.i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21))
            pass

    def read_telemetry(self) -> dict:
        # Inserire le letture dei sensori reali
        return {
            "device_id": CONFIG["DEVICE_ID"],
            "timestamp": time.time(),
            "sensors": {"no2": 0.0, "pm25": 0.0, "o3": 0.0, "pah": 0.0}
        }

    def read_health(self) -> dict:
        return {
            "device_id": CONFIG["DEVICE_ID"],
            "timestamp": time.time(),
            "status": "online",
            "battery_level": 100.0,
            "firmware_version": "v1.2.0-hw",
            "sensors_health": {p: "OK" for p in POLLUTANT_CONFIG}
        }


def get_sensor_manager() -> BaseSensorManager:
    """Factory function: restituisce l'emulatore o l'hardware in base alla configurazione."""
    if not is_esp32:
        print("[SENSORS] Avvio in modalità SIMULATA")
        return SimulatedSensorManager()
    else:
        print("[SENSORS] Avvio in modalità HARDWARE REAL ESP32")
        return ESP32HardwareSensorManager()
