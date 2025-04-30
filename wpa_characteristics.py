import json
import sys
import array
import subprocess
import dbus
import socket
import time
from gi.repository import GLib
from gatt_server import (
    GATT_CHARACTERISTIC_IFACE, CUDDiscriptor, Characteristic, InvalidValueLengthException, 
    logger, InvalidArgsException, NotSupportedException, Advertisement, Service, Application, Agent, 
    AGENT_PATH, BLUEZ_SERVICE_NAME
)

mainloop = GLib.MainLoop()


class WiFiManager:
    def __init__(self, interface="wlan0"):
        self.interface = interface
        self.ssid = None
        self.psk = None

    def set_credentials(self, ssid, psk):
        if len(ssid) > 32:
            raise ValueError("SSID must be 32 characters or less")
        if not (8 <= len(psk) <= 63):
            raise ValueError("PSK must be between 8 and 63 characters")
        self.ssid = ssid
        self.psk = psk
        logger.info(f"WiFi credentials set: SSID={self.ssid}")

    def connect(self, retries=3, delay=5):
        if not self.ssid or not self.psk:
            raise ValueError("SSID and PSK must be set before connecting")

        last_error = "Unknown error"
        for attempt in range(1, retries + 1):
            cmd = [
                "nmcli", "device", "wifi", "connect", self.ssid,
                "password", self.psk,
                "ifname", self.interface
            ]

            logger.info(f"Attempt {attempt}: Running command: {' '.join(cmd)}")
            process = subprocess.run(cmd, capture_output=True, text=True)

            if process.returncode == 0:
                logger.info(f"Connected to Wi-Fi network {self.ssid}: {process.stdout}")
                return {"success": True, "message": "Connected successfully"}

            error_msg = process.stderr.strip()
            logger.warning(f"Failed to connect (attempt {attempt}): {error_msg}")
            last_error = error_msg

            if attempt < retries:
                time.sleep(delay)

        logger.error(f"All {retries} connection attempts failed.")
        return {"success": False, "message": last_error}

    def scan_wifi_networks(self):
        try:
            output = subprocess.check_output(
                ['nmcli', '-t', '-f', 'SSID', 'device', 'wifi'],
                text=True
            )
            ssids = list({line.strip() for line in output.splitlines() if line.strip()})
            logger.info(f"Available Wi-Fi networks: {ssids}")
            return ssids
        except subprocess.CalledProcessError as e:
            logger.error(f"Error scanning Wi-Fi networks: {e}")
            return []


class WPACharacteristic(Characteristic):
    WPA_CHAR_UUID = '00001801-0000-1000-6000-00805f9b34fb'
    WPA_CHAR_FLAGS = ['read', 'write', 'notify', 'secure-read', 'secure-write']

    def __init__(self, bus, index, service):
        super().__init__(bus, index, self.WPA_CHAR_UUID, self.WPA_CHAR_FLAGS, service)
        self.wifi_manager = WiFiManager()
        self.notifying = False
        self.add_descriptor(CUDDiscriptor(bus, 1, self))
        self.ip = self.get_local_ip()
        msg = json.dumps({"status": "idle", "ip": self.ip})
        self.value = [dbus.Byte(x) for x in msg.encode('utf-8')]
        self.last_activity = time.time()
        GLib.timeout_add_seconds(60, self.idle_timeout_check)

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except Exception:
            return "0.0.0.0"
        finally:
            s.close()

    def ReadValue(self, options):
        self.last_activity = time.time()
        wifi_list = self.wifi_manager.scan_wifi_networks()
        return array.array('B', '\n'.join(wifi_list).encode('utf-8'))

    def WriteValue(self, value, options):
        self.last_activity = time.time()
        try:
            config = json.loads(bytearray(value).decode('utf-8'))
            self.wifi_manager.set_credentials(config['ssid'], config['psk'])
            result = self.wifi_manager.connect()
            self.ip = self.get_local_ip()
            status = "connected" if result["success"] else "failed"

            self.value = [dbus.Byte(x) for x in json.dumps({
                "status": status,
                "reason": result["message"],
                "ip": self.ip
            }).encode('utf-8')]

            if self.notifying:
                self.PropertiesChanged(GATT_CHARACTERISTIC_IFACE, {'Value': dbus.Array(self.value, signature='y')}, [])

            if result["success"]:
                GLib.timeout_add_seconds(10, self.disconnect_client)
            else:
                GLib.timeout_add_seconds(10, self.service.application.restart_advertising)

        except Exception as e:
            logger.error(f"Error in WriteValue: {e}")

    def StartNotify(self):
        self.notifying = True
        self.notify()

    def StopNotify(self):
        self.notifying = False

    def notify(self):
        if self.notifying:
            self.PropertiesChanged(GATT_CHARACTERISTIC_IFACE, {'Value': dbus.Array(self.value, signature='y')}, [])
            GLib.timeout_add_seconds(2, self.notify)

    def idle_timeout_check(self):
        if time.time() - self.last_activity > 300:
            logger.info("Idle timeout reached. Disconnecting BLE client.")
            return self.disconnect_client()
        return True

    def disconnect_client(self):
        try:
            adapter = dbus.Interface(self.bus.get_object("org.bluez", "/org/bluez/hci0"), "org.bluez.Adapter1")
            for device_path in self.get_connected_devices():
                adapter.RemoveDevice(device_path)
                logger.info(f"Disconnected BLE client: {device_path}")
        except Exception as e:
            logger.error(f"Failed to disconnect client: {e}")
        return False

    def get_connected_devices(self):
        obj_manager = dbus.Interface(self.bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
        managed = obj_manager.GetManagedObjects()
        return [path for path, interfaces in managed.items() if 'org.bluez.Device1' in interfaces and interfaces['org.bluez.Device1'].get('Connected')]


class WPAService(Service):
    WPA_SERVICE_UUID = '00001801-0000-1000-9000-00805f9b34fb'
    def __init__(self, bus, index):
        super().__init__(bus, index, self.WPA_SERVICE_UUID, True)
        self.wpa_characteristic = WPACharacteristic(bus, 1, self)
        self.add_characteristic(self.wpa_characteristic)


class WPAAdvertisement(Advertisement):
    def __init__(self, bus, index, mainloop):
        super().__init__(bus, index, 'peripheral', mainloop)
        self.add_service_uuid(WPAService.WPA_SERVICE_UUID)
        self.add_local_name(socket.gethostname())
        self.include_tx_power = True
        self.set_adapter_property('Discoverable', dbus.Boolean(1))
        self.set_adapter_property('DiscoverableTimeout', dbus.UInt32(0))
        self.set_adapter_property('Pairable', dbus.Boolean(1))
        self.set_adapter_property('PairableTimeout', dbus.UInt32(0))


def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    agent = Agent(bus)
    agent.set_exit_on_release(False)
    agent_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, "/org/bluez"), "org.bluez.AgentManager1")
    agent_manager.RegisterAgent(AGENT_PATH, "KeyboardDisplay")
    agent_manager.RequestDefaultAgent(AGENT_PATH)
    logger.info("Agent registered for secure pairing")

    advertisement = WPAAdvertisement(bus, 0, mainloop)
    application = Application(bus, mainloop)
    wpa_service = WPAService(bus, 0)
    wpa_service.wpa_characteristic.service = wpa_service  # Inject for callbacks
    wpa_service.application = application                 # For restart access
    application.add_service(wpa_service)

    application.register_application()
    advertisement.start_advertisement()

    mainloop.run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Exiting application")
        mainloop.quit()
