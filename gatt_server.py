import array
import json
import subprocess
import dbus
import dbus.mainloop.glib
import dbus.service
import dbus.exceptions
import logging  
import os
import sys
import time
from gi.repository import GLib
from gi.repository import GObject  




logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

loghandler = logging.StreamHandler()
loghandler.setFormatter(formatter)

loghandlerfile = logging.FileHandler('gatt_module.log')
loghandlerfile.setFormatter(formatter)

logger.addHandler(loghandler)
logger.addHandler(loghandlerfile)


mainloop = None
bus = None


# Interface UUIDs
BLUEZ_SERVICE_NAME = 'org.bluez'
BLUEZ_SERVICE_PATH = '/org/bluez'

GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHARACTERISTIC_IFACE = 'org.bluez.GattCharacteristic1'
GATT_DESCRIPTOR_IFACE = 'org.bluez.GattDescriptor1'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'

GATT_ADAPTER_IFACE = 'org.bluez.Adapter1'
GATT_DEVICE_IFACE = 'org.bluez.Device1'

GATT_AGENT_IFACE = 'org.bluez.Agent1'
AGENT_PATH = '/org/bluez/ble/agent'

DBUS_PROPERTIES_IFACE = 'org.freedesktop.DBus.Properties'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'

GATT_LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
GATT_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'



class InvalidArgsException(dbus.exceptions.DBusException):
    """
    Exception raised for invalid arguments.
    """
    _dbus_error_name = 'org.freedesktop.DBus.Error.InvalidArgs'

class NotSupportedException(dbus.exceptions.DBusException):
    """
    Exception raised for not supported operations.
    """
    _dbus_error_name = 'org.freedesktop.DBus.Error.NotSupported'

class NotPermittedException(dbus.exceptions.DBusException):
    """
    Exception raised for not permitted operations.
    """
    _dbus_error_name = 'org.freedesktop.DBus.Error.NotPermitted'

class NotAuthorizedException(dbus.exceptions.DBusException):
    """
    Exception raised for not authorized operations.
    """
    _dbus_error_name = 'org.freedesktop.DBus.Error.NotAuthorized'

class FailedException(dbus.exceptions.DBusException):
    """
    Exception raised for failed operations.
    """
    _dbus_error_name = 'org.freedesktop.DBus.Error.Failed'

class NotFoundException(dbus.exceptions.DBusException):
    """
    Exception raised for not found operations.
    """
    _dbus_error_name = 'org.freedesktop.DBus.Error.NotFound'

class RejectedException(dbus.exceptions.DBusException):
    """
    Exception raised for rejected operations.
    """
    _dbus_error_name = 'org.freedesktop.DBus.Error.Rejected'

class InvalidValueLengthException(dbus.exceptions.DBusException):
    """
    Exception raised for invalid value length.
    """
    _dbus_error_name = 'org.freedesktop.DBus.Error.InvalidValueLength'



class Application (dbus.service.Object):
    """
    GATT Application class that manages GATT services and characteristics.
    """
    def __init__(self, bus, mainloop):
        self.path ="/"
        self.mainloop = mainloop
        self.services = []
        self.bus = bus
        self.adapter = self.find_adapter()
        self.adapter_obj = self.bus.get_object(BLUEZ_SERVICE_NAME, self.adapter)
        dbus.service.Object.__init__(self, bus, self.path)

    def find_adapter(self):
        """
        Find the adapter for the application.
        """
        remote_om = dbus.Interface(self.bus.get_object(BLUEZ_SERVICE_NAME, "/"), DBUS_OM_IFACE)
        objects = remote_om.GetManagedObjects()
        adapter = None
        for path, ifaces in objects.items():
            if GATT_ADAPTER_IFACE in ifaces:
                adapter = path
                break
        return adapter

    def get_path(self):
        """
        Get the path of the application.
        """
        return dbus.ObjectPath(self.path)
    

    def add_service(self, service):
        """
        Add a GATT service to the application.
        """
        self.services.append(service)


    @dbus.service.method(DBUS_OM_IFACE, out_signature = 'a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        """
        Get all managed objects.
        """
        objects = {}
        for service in self.services:
            objects[service.get_path()] = service.get_properties()
            for characteristic in service.characteristics:
                objects[characteristic.get_path()] = characteristic.get_properties()
                for descriptor in characteristic.descriptors:
                    objects[descriptor.get_path()] = descriptor.get_properties()
        logger.debug(f"Managed objects tree: {json.dumps(str(objects), indent=2)}")
        return objects
    
    def register_application(self):
        """
        Register the application with the GATT manager.
        """
        logger.info("Registering application")
        gatt_manager = dbus.Interface(self.adapter_obj, GATT_MANAGER_IFACE)
        gatt_manager.RegisterApplication(self.path, {}, reply_handler=self.register_success, error_handler=self.register_error)
        logger.info("Application registered")

    def unregister_application(self):
        """
        Unregister the application from the GATT manager.
        """
        logger.info("Unregistering application")
        gatt_manager = dbus.Interface(self.adapter_obj, GATT_MANAGER_IFACE)
        gatt_manager.UnregisterApplication(self.path, reply_handler=self.unregister_success, error_handler=self.unregister_error)
        logger.info("Application unregistered")

    def unregister_error(self, error):
        """
        Unregister an error callback.
        """
        logger.error(f"Application unregistration error: {error}")
        self.mainloop.quit() 

    def unregister_success(self):
        """
        Unregister a success callback.
        """
        logger.info("Application unregistration successful")
        self.mainloop.quit()
    
    def register_error(self, error):
        """
        Register an error callback.
        """
        logger.error(f"Application registration error: {error}")
        self.mainloop.quit()
    
    def register_success(self):
        """
        Register a success callback.
        """
        logger.info("Application registration successful")
        pass
    

class Service (dbus.service.Object):
    """
    GATT Service class that represents a GATT service.
    """

    PATH_BASE = '/org/bluez/ble/service/'

    def __init__(self, bus, index, uuid, primary=True):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)


    def get_path(self):
        """
        Get the path of the service.
        """
        return dbus.ObjectPath(self.path)
    
    def add_characteristic(self, characteristic):
        """
        Add a GATT characteristic to the service.
        """
        self.characteristics.append(characteristic)

    def get_characteristics(self):
        """
        Get all characteristics of the service.
        """
        return self.characteristics

    def get_characteristic(self, uuid):
        """
        Get a GATT characteristic by UUID.
        """
        for characteristic in self.characteristics:
            if characteristic.uuid == uuid:
                return characteristic
        raise NotFoundException("Characteristic not found")

    def get_characteristics_path(self):
        """
        Get the paths of all characteristics.
        """
        result = []
        if not self.characteristics:
            raise NotFoundException("No characteristics found")
        for characteristic in self.characteristics:
            result.append(characteristic.get_path())
        return result
    
    def get_properties(self):
        """
        Get the properties of the service.
        """
        return {
            GATT_SERVICE_IFACE: {
                'UUID': self.uuid,
                'Primary': self.primary,
                'Characteristics': dbus.Array(self.get_characteristics_path(), signature='o')
            }
        }
    
    @dbus.service.method(DBUS_PROPERTIES_IFACE, in_signature='s',out_signature='a{sv}')
    def GEtAll(self,interface):
        """
        Get all properties of the service.
        """
        if interface != GATT_SERVICE_IFACE:
            raise InvalidArgsException("Invalid interface")
        return self.get_properties()[GATT_SERVICE_IFACE]
    

class Characteristic (dbus.service.Object):
    """
    GATT Characteristic class that represents a GATT characteristic.
    """
    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path +"/char" +str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.service = service
        self.descriptors = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        """
        Get the path of the characteristic.
        """
        return dbus.ObjectPath(self.path)
    
    def add_descriptor(self,descriptor):

        """
        Add a GATT descriptor to the characteristic.
        """
        self.descriptors.append(descriptor)

    def get_descriptor(self,uuid):
        """
        Get a GATT descriptor by UUID.
        """
        for descriptor in self.descriptors:
            if descriptor.uuid == uuid:
                return descriptor
        raise NotFoundException("Descriptor not found")

    def get_descriptors(self):
        """
        Get all descriptors of the characteristic.
        """
        return self.descriptors
    
    def get_descriptors_path(self):
        """
        Get the paths of all descriptors.
        """
        result = []
        if not self.descriptors:
            raise NotFoundException("No descriptors found")
        for descriptor in self.descriptors:
            result.append(descriptor.get_path())
        return result
    
    def get_properties(self):
        """
        Get the properties of the characteristic.
        """
        return {
            GATT_CHARACTERISTIC_IFACE: {
                'UUID': self.uuid,
                'Service': self.service.get_path(),
                'Flags': dbus.Array(self.flags, signature='s'),
                'Descriptors': dbus.Array(self.get_descriptors_path(), signature='o')
            }
        }
    
    @dbus.service.method(DBUS_PROPERTIES_IFACE, in_signature='s',out_signature='a{sv}')
    def GEtAll(self,interface):
        """
        Get all properties of the characteristic.
        """
        if interface != GATT_CHARACTERISTIC_IFACE:
            raise InvalidArgsException("Invalid interface")
        return self.get_properties()[GATT_CHARACTERISTIC_IFACE]
    

    @dbus.service.method(GATT_CHARACTERISTIC_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options):
        """
        Read the value of the characteristic.
        """
        logger.info("Default ReadValue called")
        raise NotSupportedException("Read not supported")
    
    @dbus.service.method(GATT_CHARACTERISTIC_IFACE, in_signature='aya{sv}', out_signature='')
    def WriteValue(self, value, options):
        """
        Write a value to the characteristic.
        """
        logger.info("Default WriteValue called")
        raise NotSupportedException("Write not supported")
    
    @dbus.service.method(GATT_CHARACTERISTIC_IFACE)
    def StartNotify(self):
        """
        Start notifications for the characteristic.
        """
        logger.info("Default StartNotify called")
        raise NotSupportedException("Notifications not supported")
    
    @dbus.service.method(GATT_CHARACTERISTIC_IFACE)
    def StopNotify(self):
        """
        Stop notifications for the characteristic.
        """
        logger.info("Default StopNotify called")
        raise NotSupportedException("Notifications not supported")
    
    @dbus.service.signal(DBUS_PROPERTIES_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        """
        Signal that properties have changed.
        """
        logger.info("PropertiesChanged signal emitted")
        pass

    def get_value(self):
        """
        Get the value of the characteristic.
        """
        return self.value
    
    def set_value(self, value):
        """
        Set the value of the characteristic.
        """
        self.value = value
        self.PropertiesChanged(GATT_CHARACTERISTIC_IFACE, {'Value': dbus.Array(value, signature='y')}, [])

    
class Descriptor (dbus.service.Object):
    """
    GATT Descriptor class that represents a GATT descriptor.
    """
    def __init__(self, bus, index, uuid, flags, characteristic):
        self.path = characteristic.path + "/descriptor" +str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.characteristic = characteristic
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        """
        Get the path of the descriptor.
        """
        return dbus.ObjectPath(self.path)
    
    def get_properties(self):
        """
        Get the properties of the descriptor.
        """
        return {
            GATT_DESCRIPTOR_IFACE: {
                'UUID': self.uuid,
                'Characteristic': self.characteristic.get_path(),
                'Flags': dbus.Array(self.flags, signature='s')
            }
        }
    
    @dbus.service.method(DBUS_PROPERTIES_IFACE, in_signature='s',out_signature='a{sv}')
    def GEtAll(self,interface):
        """
        Get all properties of the descriptor.
        """
        if interface != GATT_DESCRIPTOR_IFACE:
            raise InvalidArgsException("Invalid interface")
        return self.get_properties()[GATT_DESCRIPTOR_IFACE]
    
    @dbus.service.method(GATT_DESCRIPTOR_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options):
        """
        Read the value of the descriptor.
        """
        logger.info("Default ReadValue called")
        raise NotSupportedException("Read not supported")
    
    @dbus.service.method(GATT_DESCRIPTOR_IFACE, in_signature='aya{sv}', out_signature='')
    def WriteValue(self, value, options):
        """
        Write a value to the descriptor.
        """
        logger.info("Default WriteValue called")
        raise NotSupportedException("Write not supported")
    
    @dbus.service.signal(DBUS_PROPERTIES_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        """
        Signal that properties have changed.
        """
        logger.info("PropertiesChanged signal emitted")
        pass

    def get_value(self):
        """
        Get the value of the descriptor.
        """
        return self.value
    
    def set_value(self, value): 
        """
        Set the value of the descriptor.
        """
        self.value = value
        self.PropertiesChanged(GATT_DESCRIPTOR_IFACE, {'Value': dbus.Array(value, signature='y')}, [])


class Agent(dbus.service.Object):
    """
    GATT Agent class that handles agent operations.
    """
    def __init__(self, bus):
        self.bus = bus
        dbus.service.Object.__init__(self, bus, AGENT_PATH)
    exit_on_release = True
    def set_exit_on_release(self, exit_on_release):
        """
        Set whether to exit on release.
        """
        self.exit_on_release = exit_on_release
    
    def set_trusted(self,path):
        """
        Set the trusted path.
        """
        props = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, path), GATT_DEVICE_IFACE)
        props.set(GATT_DEVICE_IFACE, 'Trusted', dbus.Boolean(1))
        logger.info(f"Device {path} set as trusted")
    
    def question(self, prompt):
        return input(prompt)

    @dbus.service.method(GATT_AGENT_IFACE, in_signature='', out_signature='')
    def Release(self):
        """
        Release the agent.
        """
        logger.info("Agent released")
        if self.exit_on_release:
            logger.info("Exiting application")
            mainloop.quit()
        else:
            logger.info("Continuing application")

    @dbus.service.method(GATT_AGENT_IFACE, in_signature='o', out_signature='s')
    def RequestPinCode(self,device):
        """
        Request a PIN code from the agent.
        """
        logger.info(f"RequestPinCode called for device {device}")
        self.set_trusted(device)
        pincode = self.question("Enter PIN code: ")
        logger.info(f"PIN code entered: {pincode}")
        if not pincode:
            raise InvalidArgsException("Invalid PIN code")
        if len(pincode) < 4 or len(pincode) > 16:
            raise InvalidValueLengthException("PIN code length must be between 4 and 16 characters")
        if not pincode.isdigit():
            raise InvalidArgsException("PIN code must be numeric")
        if not pincode.isascii():
            raise InvalidArgsException("PIN code must be ASCII")
        if not pincode.isalnum():
            raise InvalidArgsException("PIN code must be alphanumeric")
        if not pincode.isprintable():
            raise InvalidArgsException("PIN code must be printable")
        return pincode.encode('utf-8')

    @dbus.service.method(GATT_AGENT_IFACE, in_signature='os', out_signature='')
    def DisplayPinCode(self, device, pincode):
        """
        Display the PIN code on the agent.
        """
        logger.info(f"DisplayPinCode called for device {device}, PIN code: {pincode}")

    @dbus.service.method(GATT_AGENT_IFACE, in_signature='o', out_signature='')
    def RequestAuthorization(self, device):
        """
        Request authorization from the agent.
        """
        logger.info(f"RequestAuthorization called for device {device}")
        authenticated = self.question("Authorize connection (y/n): ")
        if authenticated.lower() == 'y':
            logger.info("Device authorized")
            return
        elif authenticated.lower() == 'n':
            logger.info("Device not authorized")
            raise NotPermittedException("Device not permitted")
        elif authenticated.lower() == 'q':
            logger.info("Device not authorized")
            raise NotPermittedException("Device not permitted")
        raise RejectedException("Device rejected")
    
    @dbus.service.method(GATT_AGENT_IFACE, in_signature='os', out_signature='')
    def AuthorizeService(self, device, uuid):
        """
        Authorize a service from the agent.
        """
        logger.info(f"AuthorizeService called for device {device}, UUID: {uuid}")
        authenticated = self.question("Authorize service (y/n): ")
        if authenticated.lower() == 'y':
            logger.info("Service authorized")
            return
        elif authenticated.lower() == 'n':
            logger.info("Service not authorized")
            raise NotPermittedException("Service not permitted")
        elif authenticated.lower() == 'q':
            logger.info("Service not authorized")
            raise NotPermittedException("Service not permitted")
        raise RejectedException("Service rejected")

    @dbus.service.method(GATT_AGENT_IFACE, in_signature='', out_signature='')
    def Cancel(self):
        """
        Cancel the agent operation.
        """
        logger.info("Agent operation canceled")
        pass


    @dbus.service.method(GATT_AGENT_IFACE, in_signature='s', out_signature='')
    def Register(self, path):
        """
        Register the agent.
        """
        logger.info("Agent registered")
        pass

    @dbus.service.method(GATT_AGENT_IFACE, in_signature='', out_signature='')
    def Unregister(self):
        """
        Unregister the agent.
        """
        logger.info("Agent unregistered")
        pass


class CUDDiscriptor(Descriptor):
    """
    Custom descriptor class for CUD (Client Characteristic Configuration Descriptor).
    """
    CUD_UUID = '2901'
    CUD_FLAGS = ['read', 'write']
    def __init__(self, bus, index, characteristic):
        self.writable = 'write' in characteristic.flags
        self.readable = 'read' in characteristic.flags

        if not self.writable and not self.readable:
            raise NotSupportedException("CUD descriptor must be writable or readable")
        self.value = array.array('B', b'Registers CUD for application')
        self.value = self.value.tolist() 
        super().__init__(bus, index, self.CUD_UUID, self.CUD_FLAGS, characteristic)
        

    def ReadValue(self, options):
        """
        Read the value of the CUD descriptor.
        """
        if not self.readable:
            raise NotSupportedException("CUD descriptor not readable")
        logger.info("CUD descriptor read")
        return self.value
    

    def WriteValue(self, value, options):
        """
        Write a value to the CUD descriptor.
        """
        if not self.writable:
            raise NotSupportedException("CUD descriptor not writable")
        if len(value) != 2:
            raise InvalidValueLengthException("CUD descriptor value length must be 2 bytes")
        self.value = value
        logger.info(f"CUD descriptor written: {self.value}")


class Advertisement(dbus.service.Object):
    """
    GATT Advertisement class that represents a GATT advertisement.
    """

    PATH_BASE = '/org/bluez/ble/advertisement/'


    def __init__(self, bus, index, advertisement_type, mainloop):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.mainloop = mainloop
        self.advertisement_type = advertisement_type
        self.service_uuids = None
        self.manufacturer_data = None
        self.service_data = None
        self.local_name = None
        self.include_tx_power = False
        self.solicit_uuids = None
        self.data = None
        self.adapter = self.find_adapter()
        if self.adapter is None:
            raise NotFoundException("Adapter not found")
        self.adapter_obj = self.bus.get_object(BLUEZ_SERVICE_NAME, self.adapter)
        self.adapter_props = dbus.Interface(self.adapter_obj, DBUS_PROPERTIES_IFACE)
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        """
        Get the path of the advertisement.
        """
        return dbus.ObjectPath(self.path)
    
    def add_service_uuid(self, uuid):
        """
        Add a service UUID to the advertisement.
        """
        if self.service_uuids is None:
            self.service_uuids = []
        self.service_uuids.append(uuid)

    def add_solicit_uuid(self, uuid):
        """
        Add a solicit UUID to the advertisement.
        """
        if self.solicit_uuids is None:
            self.solicit_uuids = []
        self.solicit_uuids.append(uuid)

    def add_manufacturer_data(self, manufacturer_id, data):
        """
        Add manufacturer data to the advertisement.
        """
        if self.manufacturer_data is None:
            self.manufacturer_data = dbus.Dictionary({}, signature='qv')
        if not isinstance(manufacturer_id, int):
            raise InvalidArgsException("Manufacturer ID must be an integer")
        if not isinstance(data, (str, bytes)):
            raise InvalidArgsException("Data must be a string or bytes")
        if isinstance(data, str):
            data = data.encode('utf-8')
        if isinstance(data, bytes):
            data = array.array('B', data).tolist()
        if len(data) > 31:
            raise InvalidValueLengthException("Data length must be less than or equal to 31 bytes")
        self.manufacturer_data[manufacturer_id] = dbus.Array(data, signature='y')
        logger.info(f"Manufacturer data added: {manufacturer_id} - {data}")


    def add_service_data(self, uuid, data):
        """
        Add service data to the advertisement.
        """
        if self.service_data is None:
            self.service_data = dbus.Dictionary({}, signature='sv')
        if not isinstance(uuid, str):
            raise InvalidArgsException("UUID must be a string")
        if not isinstance(data, (str, bytes)):
            raise InvalidArgsException("Data must be a string or bytes")
        if isinstance(data, str):
            data = data.encode('utf-8')
        if isinstance(data, bytes):
            data = array.array('B', data).tolist()
        if len(data) > 31:
            raise InvalidValueLengthException("Data length must be less than or equal to 31 bytes")
        self.service_data[uuid] = dbus.Array(data, signature='y')

    def add_local_name(self, name):
        """
        Add a local name to the advertisement.
        """
        if not isinstance(name, str):
            raise InvalidArgsException("Name must be a string")
        if len(name) > 29:
            raise InvalidValueLengthException("Name length must be less than or equal to 29 characters")
        self.local_name = dbus.String(name)
        logger.info(f"Local name added: {name}")

    def add_data(self, data):
        """
        Add data to the advertisement.
        """
        if not isinstance(data, (str, bytes)):
            raise InvalidArgsException("Data must be a string or bytes")
        if isinstance(data, str):
            data = data.encode('utf-8')
        if isinstance(data, bytes):
            data = array.array('B', data).tolist()
        if len(data) > 31:
            raise InvalidValueLengthException("Data length must be less than or equal to 31 bytes")
        self.data = dbus.Array(data, signature='y')
        logger.info(f"Data added: {data}")

    
    def get_properties(self):
        """
        Get the properties of the advertisement.
        """
        return {
            GATT_ADVERTISEMENT_IFACE: {
                'Type': self.advertisement_type,
                'ServiceUUIDs': dbus.Array(self.service_uuids, signature='s'),
                'ManufacturerData': self.manufacturer_data,
                'ServiceData': self.service_data,
                'LocalName': self.local_name,
                'IncludeTxPower': dbus.Boolean(self.include_tx_power),
                'SolicitUUIDs': dbus.Array(self.solicit_uuids, signature='s'),
                'Data': self.data
            }
        }
    
    def set_adapter_property(self, name, value):
        """
        Set a property of the adapter.
        """
        self.adapter_props.Set(GATT_ADAPTER_IFACE, name, value)
        logger.info(f"Adapter property set: {name} - {value}")

    def get_adapter_properties(self):
        """
        Get the properties of the adapter.
        """
        return self.adapter_props.GetAll(GATT_ADAPTER_IFACE)

    def get_advertisement_type(self):
        """
        Get the advertisement type.
        """
        return self.advertisement_type
    
    def get_service_uuids(self):
        """
        Get the service UUIDs.
        """
        return self.service_uuids
    
    
    @dbus.service.method(DBUS_PROPERTIES_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        """
        Get all properties of the advertisement.
        """
        if interface != GATT_ADVERTISEMENT_IFACE:
            raise InvalidArgsException("Invalid interface")
        return self.get_properties()[GATT_ADVERTISEMENT_IFACE]
    
    @dbus.service.method(GATT_ADVERTISEMENT_IFACE, in_signature='', out_signature='')
    def Release(self):
        """
        Release the advertisement.
        """
        logger.info("Advertisement released")
        pass

    def find_adapter(self):
        """
        Find the adapter for the advertisement.
        """
        rempte_om = dbus.Interface(self.bus.get_object(BLUEZ_SERVICE_NAME, "/"), DBUS_OM_IFACE)
        objects = rempte_om.GetManagedObjects()
        adapter = None
        for path, ifaces in objects.items():
            if GATT_ADAPTER_IFACE in ifaces:
                adapter = path
                break
        logger.info(f"Adapter found: {adapter}")
        return adapter

    

    def register_advertisement(self):
        """
        Register the advertisement.
        """
        logger.info("Registering advertisement")
        adv_manager = dbus.Interface(self.adapter_obj, GATT_LE_ADVERTISING_MANAGER_IFACE)
        adv_manager.RegisterAdvertisement(self.path, {}, reply_handler=self.register_success, error_handler=self.register_error)
        logger.info("Advertisement registered")

    def unregister_advertisement(self):
        """
        Unregister the advertisement.
        """
        logger.info("Unregistering advertisement")
        adv_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, BLUEZ_SERVICE_PATH), GATT_LE_ADVERTISING_MANAGER_IFACE)
        adv_manager.UnregisterAdvertisement(self.path, reply_handler=self.unregister_success, error_handler=self.unregister_error)
        logger.info("Advertisement unregistered")

    def start_advertisement(self):
        """
        Start the advertisement.
        """
        self.register_advertisement()
        logger.info("Advertisement started")
        

    def stop_advertisement(self):
        """
        Stop the advertisement.
        """
        self.unregister_advertisement()
        logger.info("Advertisement stopped")
        

    def register_error(self, error):
        """
        Register an error callback.
        """
        logger.error(f"Advertisement registration error: {error}")
        self.mainloop.quit()
            

    def register_success(self):
        """
        Register a success callback.
        """
        logger.info("Advertisement registration successful")

    def unregister_error(self, error):
        """
        Unregister an error callback.
        """
        logger.error(f"Advertisement unregistration error: {error}")
        self.mainloop.quit()

    def unregister_success(self):
        """
        Unregister a success callback.
        """
        logger.info("Advertisement unregistration successful")
        self.mainloop.quit()

