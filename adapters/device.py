"""
Device adapters abstract base classes
"""

import os
import sys
import logging
from abc import ABC, abstractmethod

if __package__: sys.path.append(os.path.realpath(os.path.dirname(__file__)))

import bt_engine

log = logging.getLogger('DEV')

hid = None

def import_hid():
    global hid
    if hid is not None:
        return
    try:
        import hid as hid
    except:
        import hidapi as hid

class Device(ABC):
    """Base class for all device adapters"""

    # The following property should be redefined in subclasses
    model_name = None

    def __init__(self, path):
        self.path = path

    def get_model(self):
        """The implementation may redefine this method to return actual model name"""
        return self.model_name

    def is_connected(self):
        """Subclasses may redefine this method to indicate disconnection"""
        return True

    def set_channels(self, cnt):
        """
        Set the number of channels we are going the read. Should be called before first query_raw call.
        """
        pass

    @abstractmethod
    def query_raw(self, tout, idle_sleep):
        """Reads raw data packet from device and returns it"""
        pass

    def get_channels(self, data):
        """
        Get the number of channels contained in the raw data. In there there are more than 1 channel
        its index should be passed explicitly to get_value and get_mode method. Otherwise
        the channel number may be retrieved by get_channel method.
        """
        return 1

    def get_channel(self, data):
        """
        The UT61E+ can measure DC and AC voltage alternately in DC voltage dial position.
        This function returns 1 in such mode (25) if the data belongs to the alternative
        measuring channel, so it represents AC voltage. Otherwise it returns 0.
        """
        return 0

    @abstractmethod
    def get_value(self, data, channel=None):
        """
        Converts raw data to the floating point value. Here we don't
        care about units since the caller should be aware of them.
        It set mode dial manually after all. So in the mV mode the
        result is expressed in mV rather than volts.
        """
        pass

    @abstractmethod
    def get_mode(self, data, channel=None):
        """Returns measurement mode and units description string"""
        pass

    @abstractmethod
    def close(self):
        pass

    def __enter__(self):
        """Context manager protocol support"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Closes device on exiting 'with' block"""
        self.close()

class USBMixin(ABC):
    """Methods specific for USB devices"""
    isBT = False
    # The following properties should be redefined in subclasses
    device_vid = None
    device_pid = None

    @abstractmethod
    def __init__(self, dev, path):
        pass

    @classmethod
    @abstractmethod
    def list_paths(cls, vid=None, pid=None):
        """Returns the list of USB device paths"""
        pass

    @classmethod
    def open_path(cls, path):
        """Opens device given the path"""
        dev = cls._open_path(path)
        if dev is None:
            return None
        return cls(dev, path)

    @classmethod
    @abstractmethod
    def _open_path(cls, path):
        """Opens device given the path and returns it"""
        pass

    @classmethod
    def open(cls, vid=None, pid=None):
        """Opens device instance given its VID, PID and returns it"""
        if vid is None:
            vid = cls.device_vid
        if pid is None:
            pid = cls.device_pid
        paths = cls.list_paths(vid, pid)
        if not paths:
            log.error('not found')
            return None
        if len(paths) > 1:
            log.error('%d devices found', len(paths))
            return None
        return cls.open_path(paths[0])

class HIDMixin(USBMixin):
    """Methods specific for USB HID devices"""
    @classmethod
    def list_paths(cls, vid=None, pid=None):
        """Returns the list of HID device paths"""
        import_hid()
        if vid is None:
            vid = cls.device_vid
        if pid is None:
            pid = cls.device_pid
        return [dev['path'].decode('ascii') for dev in hid.enumerate(vid, pid)]

    @classmethod
    def _open_path(cls, path):
        """Opens hid device given the path and returns it"""
        import_hid()
        if isinstance(path, str):
            path = path.encode('ascii')
        dev = hid.device()
        try:
            dev.open_path(path)
        except:
            log.error('failed to open device %s', path)
            return None
        dev.set_nonblocking(True)
        return dev

class CDCMixin(USBMixin):
    """Methods specific for USB CDC devices"""
    # The following properties may be redefined in subclasses
    baud_rate = 115200
    write_timeout = .1

    @classmethod
    def list_paths(cls, vid=None, pid=None):
        """Returns the list of CDC device paths"""
        from serial.tools.list_ports import comports
        if vid is None:
            vid = cls.device_vid
        if pid is None:
            pid = cls.device_pid
        return [port.device for port in comports() if port.vid == vid and port.pid == pid]

    @classmethod
    def _open_path(cls, path):
        """Opens CDC device given the path and returns it"""
        import serial
        try:
            return serial.Serial(path, baudrate=cls.baud_rate, timeout=0, write_timeout=cls.write_timeout)
        except:
            log.error('failed to open device %s', path)
            return None

class BTMixin(ABC):
    """Methods specific for BT devices"""
    isBT = True
    # The following property should be redefined in subclasses
    device_name = None

    @classmethod
    def list_addrs(cls, name=None):
        """Returns the list of BT device addresses"""
        if name is None:
            name = cls.device_name
        return bt_engine.list_addrs(name)

    @classmethod
    @abstractmethod
    def open_addr(cls, addr):
        """Opens BT device instance given its mac address and returns it"""
        pass

    @classmethod
    def open(cls, name=None):
        """Opens BT device instance given its name and returns it"""
        if name is None:
            name = cls.device_name
        addrs = cls.list_addrs(name)
        if not addrs:
            log.error('not found')
            return None
        if len(addrs) > 1:
            log.error('%d devices found', len(addrs))
            return None
        return cls.open_addr(addrs[0])
