"""
FNIRSI USB testers communication adapter
"""

import os
import sys
import time
import logging
import struct

if __package__: sys.path.append(os.path.realpath(os.path.dirname(__file__)))

from device import Device, HIDMixin

log = logging.getLogger('DEV')

class HIDDevice(HIDMixin, Device):
    """USB HID adapter for FNB48P, FNB58 USB testers"""
    device_vid = 0x2e3c

    CMD_INIT  = [0xaa, 0x81] + [0] * 61 + [0x8e]
    CMD_START = [0xaa, 0x82] + [0] * 61 + [0x96]
    CMD_POLL  = [0xaa, 0x83] + [0] * 61 + [0x9e]

    CMD_INTERVAL = 0.05
    IDLE_DELAY   = 0.05
    DEF_TOUT     = 4  # default timeout in seconds

    def __init__(self, dev, path):
        Device.__init__(self, path)
        self.dev = dev
        self.channels = None
        self.disconnected = False

    def is_connected(self):
        return self.dev and not self.disconnected

    def send_cmd(self, cmd):
        self.dev.write([0] + cmd)

    def set_channels(self, cnt):
        """
        Set the number of channels we are going the read. Should be called before first query_raw call.
        """
        self.channels = cnt
        try:
            self.send_cmd(self.CMD_INIT)
            time.sleep(self.CMD_INTERVAL)
            self.send_cmd(self.CMD_START)
            time.sleep(self.CMD_INTERVAL)
        except Exception as e:
            self.disconnected = True
            log.debug(e)

    def get_channels(self, data):
        """Get the number of channels contained in the raw data"""
        return self.channels

    def query_raw(self, tout=None, idle_sleep=time.sleep):
        """Queries raw data packet from HID device"""
        wait = tout if tout is not None else self.DEF_TOUT
        try:
            self.send_cmd(self.CMD_POLL)
            while True:
                idle_sleep(self.IDLE_DELAY)
                buf = self.dev.read(64)
                if buf and buf[0] == 0xaa and buf[1] == 4:
                    break
                wait -= self.IDLE_DELAY
                if wait <= 0:
                    return None
        except Exception as e:
            self.disconnected = True
            log.debug(e)
            return None
        return bytes(buf[2:])

    @staticmethod
    def get_samples_(data, group):
        return [struct.unpack_from('<I', data, 15*i + 4*group)[0] / 100000 for i in range(4)]

    def get_value(self, data, channel=0):
        """Converts raw data to the floating point value"""
        samples = self.get_samples_(data, (1, 0)[channel])
        return sum(samples) / len(samples)

    def get_mode(self, data, channel=0):
        """Returns measurement mode and units description string"""
        return ('A', 'V')[channel]

    def close(self):
        """Closes device if its still open"""
        if self.dev is None:
            return
        self.dev.close()
        self.dev = None

class FNB48PUsb(HIDDevice):
    device_pid = 0x0049
    model_name = 'FNB48P'

class FNB58Usb(HIDDevice):
    device_pid = 0x5558
    model_name = 'FNB58'

if __name__ == '__main__':
    dev = FNB48PUsb.open() if '-48' in sys.argv[1:] else FNB58Usb.open()
    if dev:
        print(dev)
        with dev:
            dev.set_channels(1)
            while dev.is_connected():
                data = dev.query_raw()
                print(dev.get_value(data, 0), dev.get_mode(data, 0), dev.get_value(data, 1), dev.get_mode(data, 1))

