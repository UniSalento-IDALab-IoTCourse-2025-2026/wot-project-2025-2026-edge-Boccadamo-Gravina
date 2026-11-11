import json
import time
import asyncio
from config import CONFIG, is_esp32, get_iso_timestamp
from my_network import is_wifi_connected


class DynamicMQTTClient:
    def __init__(self):
        self.device_id = CONFIG["DEVICE_ID"]
        self.broker = CONFIG["MQTT_BROKER"]
        self.port = CONFIG["MQTT_PORT"]
        self.user = CONFIG["MQTT_USERNAME"]
        self.password = CONFIG["MQTT_PASSWORD"]
        self.topic_status = CONFIG["MQTT_TOPIC_STATUS"]
        self.client = None
        self._lock = asyncio.Lock() # Per gestire concorrenza dei task che richiedono connessione

    # Configurazione MQTT Last Will & Testament (LWT)
    # Se il broker perde il contatto con la Smartbox, pubblicherà questo messaggio su MQTT_TOPIC_STATUS
    def _get_lwt_payload(self) -> str:
        return json.dumps({
            "device_id": self.device_id,
            "timestamp": get_iso_timestamp(),
            "status": "offline",
            "reason": "unexpected_disconnection"
        })

    def _cleanup_client(self):
        """Pulisce le risorse del client senza sollevare eccezioni."""
        if self.client is not None:
            if not is_esp32:
                try:
                    self.client.loop_stop()
                    self.client.disconnect()
                except Exception as e:
                    print(f"[MQTT] Errore durante la disconnessione: {e}")
            else:
                try:
                    self.client.disconnect()
                except Exception as e:
                    print(f"[MQTT] Errore durante la disconnessione: {e}")
                    # Su MicroPython se la socket è morta disconnect() fallisce: forziamo la chiusura socket
                    try:
                        if hasattr(self.client, 'sock') and self.client.sock:
                            self.client.sock.close()
                    except Exception:
                        pass
            self.client = None

    async def connect(self):
        async with self._lock:
            if self.client is not None:
                return

            print(f"[MQTT] Connessione a {self.broker}:{self.port}...")
            lwt_payload = self._get_lwt_payload()

            while True:
                try:
                    if is_esp32:
                        if is_wifi_connected():
                            from umqtt.simple import MQTTClient
                            self.client = MQTTClient(
                                client_id=self.device_id,
                                server=self.broker,
                                port=self.port,
                                user=self.user,
                                password=self.password,
                                keepalive=60
                            )
                            self.client.set_last_will(
                                self.topic_status.encode('utf-8'),
                                lwt_payload.encode('utf-8'),
                                retain=True,
                                qos=1
                            )
                            self.client.connect(timeout=5)
                        else:
                            print("[MQTT] Wi-Fi non disponibile. In attesa della rete...")
                            await asyncio.sleep(5)
                            continue
                    else:
                        import paho.mqtt.client as paho
                        self.client = paho.Client(paho.CallbackAPIVersion.VERSION2, client_id=self.device_id)
                        if self.user:
                            self.client.username_pw_set(self.user, self.password)


                        self.client.will_set(self.topic_status, lwt_payload, qos=1, retain=True) # retain=True per conservare l'ultimo stato noto sul broker
                        self.client.connect(self.broker, self.port, keepalive=60)
                        self.client.loop_start()

                    print("[MQTT] Connesso con successo.")
                    break
                except Exception as e:
                    print(f"[MQTT] Errore di connessione ({e}). Riprovo tra 5 secondi...")
                    self._cleanup_client()
                
                await asyncio.sleep(5)

    def publish(self, topic: str, payload: dict, retain: bool = False) -> bool:
        if self.client is None:
            print(f"[MQTT] Impossibile pubblicare su '{topic}': client non ancora connesso.")
            return False
            
        msg = json.dumps(payload)
        try:
            if is_esp32:
                self.client.publish(topic.encode('utf-8'), msg.encode('utf-8'), retain=retain, qos=1)
            else:
                self.client.publish(topic, msg, retain=retain, qos=1)
            return True
        except Exception as e:
            print(f"[MQTT] Errore durante pubblicazione su '{topic}' ({e}). Client resettato.")
            # Resettando self.client a None, segnaliamo ai task nel main che bisogna riconnettersi
            self._cleanup_client()
            return False

    def disconnect(self):
        if self.client is not None:
            offline_payload = {
                "device_id": self.device_id,
                "timestamp": get_iso_timestamp(),
                "status": "offline",
                "reason": "clean_shutdown"
            }
            
            try:
                msg = json.dumps(offline_payload)
                if is_esp32:
                    self.client.publish(self.topic_status.encode('utf-8'), msg.encode('utf-8'), retain=True, qos=1)
                else:
                    self.client.publish(self.topic_status, msg, retain=True, qos=1)
                    # Diamo una frazione di secondo a Paho per mandare il messaggio prima di avviare la disconnessione
                    time.sleep(0.2)
            except Exception as e:
                print(f"[MQTT] Impossibile inviare stato offline in chiusura: {e}")

            self._cleanup_client()