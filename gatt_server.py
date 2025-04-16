import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
import logging 

import array
from gi.repository import GObject, GLib
#import sys
#from random import randint


mainloop = None


logger = logging.getLogger(__name__)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logHandler = logging.StreamHandler()
filelogHandler = logging.FileHandler("dewarmteble.log")

logHandler.setFormatter(formatter)
filelogHandler.setFormatter(formatter)

logger.addHandler(logHandler)
logger.addHandler(filelogHandler)

logger.setLevel(logging.INFO)

bus = None
device_obj = None
dev_path = None

AGENT_PATH = "/org/bluez/dewarmteble/agent"


BLUEZ_SERVICE_NAME = 'org.bluez'

AGENT_IFACE = 'org.bluez.Agent1'

DEVICE_IFACE = 'org.bluez.Device1'
ADAPTER_IFACE = "org.bluez.Adapter1"

DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'


GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE =    'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE =    'org.bluez.GattDescriptor1'

LE_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'



class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.freedesktop.DBus.Error.InvalidArgs'

class NotSupportedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.freedesktop.DBus.Error.NotSupported'

class NotPermittedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.freedesktop.DBus.Error.NotPermitted'

class InvalidValueLengthException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.freedesktop.DBus.Error.InvalidValueLength'

class FailedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.freedesktop.DBus.Error.Failed'

class Rejected(dbus.DBusException):
    _dbus_error_name = "org.bluez.Error.Rejected"


class Application(dbus.service.Object):
    """
    GattApplication1 interface implementation
    """

    def __init__(self, bus):
        self.path = "/"
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)


    def get_path(self):
        return dbus.ObjectPath(self.path)
    
    def add_service(self, service):
        self.services.append(service)


    @dbus.service.method(DBUS_OM_IFACE, out_signature = 'a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response={}
        logger.info('GetManagerObjects')

        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()

        return response
    

class Service(dbus.service.Object):
    """
        GattService1 interface implementation
    """
    PATHBASE = '/org/bluez/dewarmteble/service'

    def __init__(self, bus, index, uuid, primary):
        self.path = self.PATHBASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_SERVICE_IFACE:{
                'UUID': self.uuid,
                'Primary': self.primary,
                'Characteristics': dbus.Array(
                    self.get_characteristics_paths(),
                    signature= 'o')
            }
        }
    
    def get_path(self):
        return dbus.ObjectPath(self.path)
    
    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)

    def get_characteristics_paths(self):
        result = []
        for chrc in self.characteristics:
            result.append(chrc.get_path())
        return result
    
    def get_characteristics(self):
        return self.characteristics
    
    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature = 'a{sv}')
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[GATT_SERVICE_IFACE]
    

class Characteristic(dbus.service.Object):
    """
    GattCharacteristic1 interface implementation
    """

    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path +'/char'+ str(index)
        self.service = service
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.descriptors = []
        dbus.service.Object.__init__(self, bus, self.path)


    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service,
                'UUID': self.uuid,
                'Flags': self.flags,
                'Descriptors': dbus.Array(
                    self.get_descriptors_paths(),
                    signature='o'
                )
            }
        }
    
    def get_path(self):
        return dbus.ObjectPath(self.path)
    
    def get_descriptors_paths(self):
        results = []
        for desc in self.descriptors:
            results.append(desc.get_path())
        return results
    
    def add_descriptor(self, descriptor):
        self.descriptors.append(descriptor)

    def get_descriptors(self):
        return self.descriptors
    
    @dbus.service.method(DBUS_PROP_IFACE, in_signature= 's', out_signature = 'a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[GATT_CHRC_IFACE]
    
    @dbus.service.method(GATT_CHRC_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options):
        logger.info('Default ReadValue called, returning error')
        raise NotSupportedException()
    
    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        logger.info('Default WriteValue called, returning error')
        raise NotSupportedException()
    
    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        logger.info('Default StartNotify called, returning error')
        raise NotSupportedException()
    
    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        logger.info('Default StopNotify called, returning error')
        raise NotSupportedException()
    
    @dbus.service.signal(DBUS_PROP_IFACE, signature = 'sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        pass


class Descriptor(dbus.service.Object):
    """
    GattDescriptor1 interface implementation
    """

    def __init__(self, bus, index, uuid, flags, characteristic):
        self.path = characteristic.path + '/desc' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.chrc = characteristic
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_DESC_IFACE:{
                'Characteristic': self.chrc.get_path(),
                'UUID': self.uuid,
                'Flags': self.flags
            }
        }
    
    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature = 's', out_signature ='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_DESC_IFACE:
            raise InvalidArgsException()
        
        return self.get_properties()[GATT_DESC_IFACE]
    
    @dbus.service.method(GATT_DESC_IFACE, in_signature = 'a{sv}', out_signature = 'ay')
    def ReadValue(self, options):
        logger.info('Default ReadValue called, returning error')
        raise NotSupportedException()
    
    @dbus.service.method(GATT_DESC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        logger.info('Default WriteValue called, returning error')
        raise NotSupportedException()
    

class Advertisement(dbus.service.Object):
    """
    GattAdvertisement1 interface implementation
    """
    PATH_BASE = '/org/bluez/dewarmteble/advertisement'

    def __init__(self, bus, index, advertising_type):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = advertising_type
        self.service_uuids = None
        self.manufacturer_data = None
        self.solicit_uuids = None
        self.service_data = None
        self.local_name = None 
        self.include_tx_power = False
        self.data = None
        dbus.service.Object.__init__(self, bus, self.path)


    def get_properties(self):
        properties = dict()
        properties['Type']= self.ad_type
        if self.service_uuids is not None:
            properties['ServiceUUIDs'] = dbus.Array(self.service_uuids, signature = 's')

        if self.solicit_uuids is not None:
            properties['SolicitUUIDs'] = dbus.Array(self.solicit_uuids, signature = 's')

        if self.manufacturer_data is not None:
            properties['ManufacturerData'] = dbus.Dictionary(self.manufacturer_data, signature = 'qv')
        if self.service_data is not None:
            properties['ServiceData'] = dbus.Dictionary(self.service_data, signature = 'sv')

        if self.local_name is not None:
            properties['LocalName'] = dbus.String(self.local_name)

        if self.include_tx_power:
            properties['Includes'] = dbus.Array(["tx-power"], signature='s')

        if self.data is not None:
            properties['Data'] = dbus.Dictionary(self.data, signature='yv')
        logger.info(f"properties: {properties}")
        return {
            LE_ADVERTISEMENT_IFACE: properties
        }
    
    def get_path(self):
        return dbus.ObjectPath(self.path)
    

    def add_service_uuid(self, uuid):
        if not self.service_uuids:
            self.service_uuids = []
        self.service_uuids.append(uuid)

    def add_solicit_uuid(self, uuid):
        if not self.solicit_uuids:
            self.solicit_uuids = []
        self.solicit_uuids.append(uuid)

    def add_manufacturer_data(self, manuf_code, data):
        if not self.manufacturer_data:
            self.manufacturer_data = dbus.Dictionary({}, signature='qv')
        self.manufacturer_data[manuf_code] = dbus.Array(data, signature='y')

    def add_service_data(self, uuid, data):
        if not self.service_data:
            self.service_data = dbus.Dictionary({}, signature='sv')
        self.service_data[uuid] = dbus.Array(data, signature='y')

    def add_local_name(self, name):
        if not self.local_name:
            self.local_name = ""
        self.local_name = dbus.String(name)

    def add_data(self, ad_type, data):
        if not self.data:
            self.data = dbus.Dictionary({}, signature='yv')
        self.data[ad_type] = dbus.Array(data, signature='y')

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        logger.info('GetAll')
        if interface != LE_ADVERTISEMENT_IFACE:
            raise InvalidArgsException()
        logger.info('returning props')
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]
    
    @dbus.service.method(LE_ADVERTISEMENT_IFACE,
                         in_signature='',
                         out_signature='')
    def Release(self):
        logger.info('%s: Released!' % self.path)




def question(prompt):
    return input(prompt)

def set_trusted(path):
    props = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, path),DBUS_PROP_IFACE) 
    props.Set(DEVICE_IFACE, 'Trusted', True)

def dev_connect(path):
    dev = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, path), DEVICE_IFACE)
    dev.Connect()

def pair_reply():
    logger.info("Device paired")
    set_trusted(dev_path)
    dev_connect(dev_path)
    mainloop.quit()

def pair_error(error):
    err_name = error.get_dbus_name()
    if err_name == "org.freedesktop.DBus.Error.NoReply" and device_obj:
        logger.info("Timed out. Cancelling pairing")
        device_obj.CancelPairing()
    else:
        logger.info("Creating device failed: %s" % (error))
    mainloop.quit()

def find_adapter(bus):
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'),
                               DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()

    for o, props in objects.items():
        if GATT_MANAGER_IFACE in props.keys():
            return o
    return None

def register_app_cb():
    logger.info('GATT application registered')


def register_app_error_cb(error):
    logger.critical('Failed to register application: ' + str(error))
    mainloop.quit()


def register_ad_cb():
    logger.info('Advertisement registered')


def register_ad_error_cb(error):
    logger.critical('Failed to register advertisement: ' + str(error))
    mainloop.quit()



class Agent(dbus.service.Object):
    """
    Agent1 interface manipulation
    """

    exit_on_release = True

    def set_exit_on_release(self, exit_on_release):
        self.exit_on_release = exit_on_release

    @dbus.service.method(AGENT_IFACE, in_signature = '',out_signature = '')
    def Release(self):
        logger.info("Release")
        if self.exit_on_release:
            mainloop.quit()

    @dbus.service.method(AGENT_IFACE, in_signature = 'os', out_signature = '')
    def AuthorizeService(self, device, uuid):
        logger.info( "AuthorizeService (%s,%s)" % (device, uuid))
        authorize = question("Authorize connection (yes/no): ")
        if authorize == "yes":
            return
        raise Rejected("Connection rejected by user")
    
    @dbus.service.method(AGENT_IFACE,in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        logger.info(f"RequestPinCode ({device})")
        set_trusted(device)
        return question('Enter PIN code: ' )
    
    @dbus.service.method(AGENT_IFACE,in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        logger.info("RequestPasskey (%s)" % (device))
        set_trusted(device)
        passkey = question("Enter passkey: ")
        return dbus.UInt32(passkey)

    @dbus.service.method(AGENT_IFACE, in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered):
        logger.info(f"DisplayPasskey ({device}, {passkey} entered {entered})")

    @dbus.service.method(AGENT_IFACE, in_signature="os", out_signature="")
    def DisplayPinCode(self, device, pincode):
        logger.info("DisplayPinCode (%s, %s)" % (device, pincode))

    @dbus.service.method(AGENT_IFACE, in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        logger.info("RequestConfirmation (%s, %06d)" % (device, passkey))
        confirm = question("Confirm passkey (yes/no): ")
        if (confirm == "yes"):
            set_trusted(device)
            return
        raise Rejected("Passkey doesn't match")

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        logger.info("RequestAuthorization (%s)" % (device))
        auth = question("Authorize? (yes/no): ")
        if (auth == "yes"):
            return
        raise Rejected("Pairing rejected")

    @dbus.service.method(AGENT_IFACE, in_signature="", out_signature="")
    def Cancel(self):
        logger.info("Cancel")


class CharacteristicUserDescriptionDescriptor(Descriptor):
    """
    Writable CUD descriptor.
    """
    CUD_UUID = '2901'

    def __init__(self, bus, index, characteristic):
        self.writable = 'writable-auxiliaries' in characteristic.flags
        self.value = array.array('B', b'Registers characteristic user description (CUD) descriptors for the application')
        self.value = self.value.tolist()
        Descriptor.__init__(
                self, bus, index,
                self.CUD_UUID,
                ['read', 'write'],
                characteristic)

    def ReadValue(self, options):
        return self.value

    def WriteValue(self, value, options):
        if not self.writable:
            raise NotPermittedException()
        self.value = value
    
