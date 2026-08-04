"""
Adapter communicating with multimeter by SCPI commands.
Tested with OWON XDM1241.
"""

import os
import sys

if __package__: sys.path.append(os.path.realpath(os.path.dirname(__file__)))

import time
import logging
from device import CDCMixin, Device

log = logging.getLogger('DEV')

class SCPIDevice(CDCMixin, Device):
    """OWON SCPI multimeter interface adapter"""
    model_name  = 'SCPI'
    # CH340 USB-serial chip
    device_vid = 0x1a86
    device_pid = 0x7523

    def_read_tout = 1
    no_value = b'NONe'

    def __init__(self, dev, path):
        Device.__init__(self, path)
        self.dev = dev
        self.disconnected = False
        self.channels = 1
        self.modes = None

    def set_channels(self, cnt):
        """
        Set the number of channels we are going the read. Should be called before first query_raw call.
        """
        self.channels = cnt
        assert cnt == 1 or cnt == 2
        funcs = [self._call(b'FUNC%d?' % (i+1)) for i in range(cnt)]
        self.modes = [f.decode('ascii') if f and f != SCPIDevice.no_value else '' for f in funcs]

    def is_connected(self):
        return self.dev and not self.disconnected

    def _call(self, cmd, tout=None, idle_sleep=time.sleep):
        wait = tout if tout is not None else self.def_read_tout
        wait_step = 0.01
        resp = bytes()
        try:
            self.dev.write(cmd + b'\r')
            while True:
                idle_sleep(wait_step)
                resp += self.dev.read(64)
                if resp and resp[-1:] == b'\n' or resp[-1:] == b'\r':
                    return resp.strip().strip(b'"')
                wait -= wait_step
                if wait <= 0:
                    return None
        except Exception as e:
            self.disconnected = True
            log.debug(e)
            return None

    def query_raw(self, tout=None, idle_sleep=time.sleep):
        """Queries raw data packet from HID device"""
        resp = self._call(b'MEAS?', tout, idle_sleep)
        if not resp:
            return None
        vals = resp.split(b',')
        if len(vals) < self.channels:
            if val2 := self._call(b'MEAS2?', tout, idle_sleep):
                vals.append(val2)
        return (self, vals)

    @staticmethod
    def get_channels(data):
        self, vals = data
        return min(self.channels, len(vals))

    @classmethod
    def get_value(cls, data, channel=None):
        _, vals = data
        try:
            return float(vals[channel if channel is not None else 0])
        except ValueError:
            return float('nan')

    @staticmethod
    def get_mode(data, channel=None):
        self, _ = data
        return self.modes[channel if channel is not None else 0]

    def close(self):
        """Closes device if its still open"""
        if self.dev is None:
            return
        self.dev.close()
        self.dev = None
