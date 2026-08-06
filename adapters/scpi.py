"""
Adapters communicating with device by SCPI commands.
Tested with OWON multimeters and programmable power supplies.
"""

import os
import sys

if __package__: sys.path.append(os.path.realpath(os.path.dirname(__file__)))

import time
import logging
from device import CDCMixin, Device

log = logging.getLogger('DEV')

class SCPIMixin(CDCMixin):
    """Base class for adapters using SCPI commands over CDC link"""
    def_read_tout = 1

    def __init__(self, dev, path):
        Device.__init__(self, path)
        self.dev = dev
        self.disconnected = False

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

    def close(self):
        """Closes device if its still open"""
        if self.dev is None:
            return
        self.dev.close()
        self.dev = None

class SCPIDmm(SCPIMixin, Device):
    """SCPI multimeter interface adapter. Tested with OWON XDM1241."""
    model_name  = 'SCPI-DMM'
    # CH340 USB-serial chip
    device_vid = 0x1a86
    device_pid = 0x7523

    no_value = b'NONe'
    def_mode = 'DUTY%'

    def __init__(self, dev, path):
        SCPIMixin.__init__(self, dev, path)
        self.channels = None
        self.modes = None

    def set_channels(self, cnt):
        """
        Set the number of channels we are going the read. Should be called before first query_raw call.
        """
        assert cnt in (1, 2)
        self.channels = cnt
        funcs = [self._call(b'FUNC%d?' % (i+1)) for i in range(cnt)]
        self.modes = [f.decode('ascii') if f and f != SCPIDmm.no_value else self.def_mode for f in funcs]

    def query_raw(self, tout=None, idle_sleep=time.sleep):
        """Queries raw data from device"""
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

class SCPIPowerSource(SCPIMixin, Device):
    """
    SCPI programmable power supplies interface adapter. Tested with OWON SPE3051.
    It always measures current in the main channel and voltage in the secondary one.
    """
    model_name  = 'SCPI-CV'
    # CH340 USB-serial chip
    device_vid = 0x1a86
    device_pid = 0x7523

    def __init__(self, dev, path):
        SCPIMixin.__init__(self, dev, path)
        self.channels = None

    def set_channels(self, cnt):
        """
        Set the number of channels we are going the read. Should be called before first query_raw call.
        """
        assert cnt in (1, 2)
        self.channels = cnt

    def query_raw(self, tout=None, idle_sleep=time.sleep):
        """Queries raw data from device"""
        if self.channels < 2:
            resp = self._call(b'MEAS:CURR?', tout, idle_sleep)
            return (self, (resp,)) if resp else None
        resp = self._call(b'MEAS:ALL?', tout, idle_sleep)
        if not resp:
            return None
        return (self, tuple(reversed(resp.split(b',')[:2])))

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
        return ('CURR', 'VOLT')[channel if channel is not None else 0]
