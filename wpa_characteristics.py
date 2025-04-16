import os
import subprocess
import json
import dbus
import dbus.mainloop.glib
from gi.repository import GLib
import logging
from gatt_server import ( Service, Characteristic, CharacteristicUserDescriptionDescriptor, Advertisement, Application, Agent, 
                         ADAPTER_IFACE, BLUEZ_SERVICE_NAME, GATT_MANAGER_IFACE, LE_ADVERTISING_MANAGER_IFACE, AGENT_PATH, DBUS_PROP_IFACE,GATT_CHRC_IFACE,
                         find_adapter, register_ad_cb,register_ad_error_cb, register_app_cb, register_app_error_cb)



mainloop = GLib.MainLoop()
logger = logging.getLogger(__name__)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logHandler = logging.StreamHandler()
filelogHandler = logging.FileHandler("able.log")

logHandler.setFormatter(formatter)
filelogHandler.setFormatter(formatter)

logger.addHandler(logHandler)
logger.addHandler(filelogHandler)

logger.setLevel(logging.INFO)

WPA_SUPPLICANT_PATH = '/etc/wpa_supplicant/wpa_supplicant.conf'
WPA_COUNTRY_DEFAULT = 'NL'
WPA_SSID_DEFAULT = ''
WPA_SCAN_SSID_DEFAULT = 1
WPA_PSK_DEFAULT = ''
WPA_KEY_MGMT_DEFAULT = 'WPA-PSK'


def parser(file_path):
    allvars = dict()
    with open(file_path, 'r') as f :
        for line in f:
            name, value = line.partition("=")[::2]
            allvars[name.lower().strip()] = value 

    return allvars

class WPASupplicant:
    def __init__(self, file_path = WPA_SUPPLICANT_PATH):
        self.file_path = file_path
        self.params =  {
            'country': WPA_COUNTRY_DEFAULT,
            'ssid': WPA_SSID_DEFAULT,
            'scan_ssid': WPA_SCAN_SSID_DEFAULT,
            'psk': WPA_PSK_DEFAULT,
            'key_mgmt': WPA_KEY_MGMT_DEFAULT
        }

    def read(self):
        args = parser(self.file_path)
        for key, value in args.items():
            if key in self.params:
                self.params[key] = value
        return

    def write(self):
        with open(self.file_path, 'w') as f:
            f.write('ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n')
            f.write('update_config=1\n')
            f.write(f"country={self.params['country']}\n")
            f.write('network={\n')
            f.write(f"ssid=\"{self.params['ssid']}\"\n")
            f.write(f"scan_ssid={self.params['scan_ssid']}\n")
            f.write(f"psk=\"{self.params['psk']}\"\n")
            f.write(f"key_mgmt={self.params['key_mgmt']}\n")
            f.write('}')
        return
    
    def restart_wlan_interface(self):
        self.restart_process = subprocess.Popen(["sudo","systemctl","restart","wpa_supplicant"])

class WPAManageService(Service):
    """
    Service to manage the local WLAN adapter.
    Allows a user to configure the WLAN wpa_applicant service
    """

    WLANMANAGE_SVC_UUID = "54321d67-d578-4874-6e86-7d024ee09ba7"

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.WLANMANAGE_SVC_UUID, True)
        self.add_characteristic(WPAConfigureCharacteristic(bus, 0, self))
        


class WPAConfigureCharacteristic(Characteristic):
    uuid = "4321f8d2-9f96-4f58-a53d-fc7550e7c15e"
    description = b"Configure WLAN interface {read:cur_config, write:new_config}"

    def __init__(self, bus, index, service):
        super().__init__(bus, index, self.uuid, ["read","write", "notify"], service)
        self.notifying = False
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1,self))
        self.wpa = WPASupplicant()

    def ReadValue(self, options):
        try:
            logger.info('Reading current WLAN settings')
            self.wpa.read()
            ssid = self.wpa.params['ssid'] if self.wpa.params['ssid'] != '' else "Empty"
            logger.info(f"ssid: {ssid}")
            return bytearray(ssid,"utf-8")
        except Exception as e:
            logger.exception(f"Error in ReadValue: {e}")
            raise
    
    def WriteValue(self,value, options):
        try:
            logger.info('Writing new WLAN configuration')
            self.wpa.read()
            data = json.loads(bytearray(value).decode('utf-8'))
            logger.info(data)
            logger.info(f"params ssid: {self.wpa.params['ssid']}")
            for key, value in data:
                if key in self.wpa.params:
                    self.wpa.params[key] = data[key] 
            self.wpa.write()
            self.wpa.restart_wlan_interface()
            if self.notifying:
                msg = json.dumps({"status":"success"})
                self.PropertiesChanged(
                    GATT_CHRC_IFACE,
                    {"Value": dbus.ByteArray(msg.encode("utf-8"))},
                    [],
                )
        except Exception as e:
            logger.error(f"EXCEPTION: {e}")
            if self.notifying:
                msg = json.dumps({"status":f"error: {e}"})
                self.PropertiesChanged(
                    GATT_CHRC_IFACE,
                    {"Value":dbus.ByteArray(msg.encode("utf-8"))},
                    [],
                )
            raise
    
    def StartNotify(self):
        if self.notifying:
            return
        logger.info("Notifications started")
        self.notifying = True
    
    def StopNotify(self):
        if not self.notifying:
            return
        logger.info("Notifications Stopped")
        self.notifying = False


class WlanSetupAdvertisement(Advertisement):
    IFACE_BT_NAME = "Arbi"
    def __init__(self, bus, index):
        super().__init__(bus, index, "peripheral")
        self.add_local_name(self.IFACE_BT_NAME)
        self.include_local_name = True
        self.include_tx_power = True
        self.add_service_uuid(WPAManageService.WLANMANAGE_SVC_UUID)
        #self.add_manufacturer_data(0xFFFF, [0x70, 0x74],)

def power_up_ble_interface(adapter_props):
        # powered property on the controller to off
        adapter_props.Set(ADAPTER_IFACE, "Powered", dbus.Boolean(1))
        adapter_props.Set(ADAPTER_IFACE, "Discoverable", dbus.Boolean(1))
        adapter_props.Set(ADAPTER_IFACE, "Alias", "Arbi")
        adapter_props.Set(ADAPTER_IFACE, "Pairable", dbus.Boolean(0))

def power_down_ble_interface():
        # powered property on the controller to on
        os.system("bluetoothctl power on")

def main():

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()

    adapter = find_adapter(bus)
    if not adapter:
        logger.critical("GattManager1 interface not found")
        return

    adapter_obj = bus.get_object(BLUEZ_SERVICE_NAME, adapter)

    adapter_props = dbus.Interface(adapter_obj, DBUS_PROP_IFACE)

    power_up_ble_interface(adapter_props)
    
    # Get manager objs
    service_manager = dbus.Interface(adapter_obj, GATT_MANAGER_IFACE)
    ad_manager = dbus.Interface(adapter_obj, LE_ADVERTISING_MANAGER_IFACE)

    advertisement = WlanSetupAdvertisement(bus, 0)
    bluez_obj = bus.get_object(BLUEZ_SERVICE_NAME, "/org/bluez")

    #agent = Agent(bus, AGENT_PATH)

    app = Application(bus)
    app.add_service(WPAManageService(bus, 2))

    #agent_manager = dbus.Interface(bluez_obj, "org.bluez.AgentManager1")
    #agent_manager.RegisterAgent(AGENT_PATH, "NoInputNoOutput")

    ad_manager.RegisterAdvertisement(
        advertisement.get_path(),
        {},
        reply_handler=register_ad_cb,
        error_handler=register_ad_error_cb,
    )

    logger.info("Registering GATT application")

    service_manager.RegisterApplication(
        app.get_path(),
        {},
        reply_handler=register_app_cb,
        error_handler=register_app_error_cb,
    )

    #agent_manager.RequestDefaultAgent(AGENT_PATH)

    mainloop.run()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        power_down_ble_interface()
        logging.info("BLE proxy is closed...")