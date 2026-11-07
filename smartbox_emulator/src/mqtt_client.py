import json
import time
from config import CONFIG, is_esp32



class DynamicMQTTClient:
    def __init__(self):
        self.device_id = CONFIG["DEVICE_ID"]
        self.broker = CONFIG["MQTT_BROKER"]
        self.port = CONFIG["MQTT_PORT"]
        self.user = CONFIG["MQTT_USERNAME"]
        self.password = CONFIG["MQTT_PASSWORD"]
        self.topic_status = CONFIG["MQTT_TOPIC_STATUS"]
        self.client = None

    def connect(self):
        print(f"[MQTT] Connessione a {self.broker}:{self.port}...")
        while True:
            try:
                if is_esp32:
                    from umqtt.simple import MQTTClient
                    self.client = MQTTClient(
                        client_id=self.device_id,
                        server=self.broker,
                        port=self.port,
                        user=self.user,
                        password=self.password,
                        keepalive=60
                    )
                    # Configurazione Last Will & Testament (LWT)
                    lwt_payload = json.dumps({
                        "device_id": self.device_id,
                        "timestamp": time.time(),
                        "status": "offline",
                        "reason": "unexpected_disconnection"
                    })
                    self.client.set_will(self.topic_status, lwt_payload, retain=True, qos=1)
                    self.client.connect()
                else:
                    import paho.mqtt.client as paho
                    self.client = paho.Client(paho.CallbackAPIVersion.VERSION2, client_id=self.device_id)
                    if self.user:
                        self.client.username_pw_set(self.user, self.password)

                    # Configurazione MQTT Last Will & Testament (LWT)
                    # Se il broker perde il contatto con la Smartbox, pubblicherà questo messaggio su MQTT_TOPIC_STATUS
                    lwt_payload = json.dumps({
                        "device_id": self.device_id,
                        "timestamp": time.time(),
                        "status": "offline",
                        "reason": "unexpected_disconnection"
                    })
                    self.client.will_set(self.topic_status, lwt_payload, qos=1, retain=True) # retain=True per conservare l'ultimo stato noto sul broker
                    self.client.connect(self.broker, self.port, keepalive=60)
                    self.client.loop_start()

                print("[MQTT] Connesso con successo.")
                break
            except Exception as e:
                print(f"[MQTT] Errore di connessione ({e}). Riprovo tra 5 secondi...")
                time.sleep(5)

    def publish(self, topic: str, payload: dict, retain: bool = False):
        msg = json.dumps(payload)
        if is_esp32:
            self.client.publish(topic.encode(), msg.encode(), retain=retain, qos=1)
        else:
            self.client.publish(topic, msg, retain=retain, qos=1)

    def disconnect(self):
        if self.client:
            offline_payload = {
                "device_id": self.device_id,
                "timestamp": time.time(),
                "status": "offline",
                "reason": "clean_shutdown"
            }
            self.publish(self.topic_status, offline_payload, retain=True)
            if is_esp32:
                # Disconnessione pulita del client umqtt.simple su ESP32
                try:
                    self.client.disconnect()
                except Exception as e:
                    print(f"[MQTT] Errore durante la disconnessione ESP32: {e}")
            else:
                # Gestione per Paho MQTT su PC
                self.client.loop_stop()
                self.client.disconnect()
