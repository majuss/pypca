# import string
# import pickle
# import os
# import time
import logging
from serial import Serial
import sys
import re
import threading
import time


# from pathlib import Path

import pypca.constants as CONST

_LOGGER = logging.getLogger(__name__)
# home = str(Path.home())


class PCA():
    """Interface to the JeeLink."""

    sensors = {}
    _registry = {}
    _callback = None
    _serial = None
    _stopevent = None
    _thread = None

    def __init__(self, port, baud, timeout=2):
        """Initialize the pca device."""
        self._port = port
        self._baud = baud
        self._timeout = timeout
        self._serial = Serial()
        self._callback_data = None

    def open(self):
        """Open the device."""
        self._serial.port = self._port
        self._serial.baudrate = self._baud
        self._serial.timeout = self._timeout
        self._serial.open()
        self._serial.flushInput()
        self._serial.flushOutput()

    def start_scan(self):
        """Start scan task in background."""
        self._start_worker()

    def _start_worker(self):
        if self._thread is not None:
            return
        self._stopevent = threading.Event()
        self._thread = threading.Thread(target=self._refresh, args=())
        self._thread.daemon = True
        self._thread.start()

    def _refresh(self):
        """Background refreshing thread."""
        while not self._stopevent.isSet():
            line = self._serial.readline()
            print(line)
            #this is for python2/python3 compatibility. Is there a better way?
            try:
                line = line.encode().decode('utf-8')
            except AttributeError:
                line = line.decode('utf-8')
            # print(line)
            if PCASensor.re_reading.match(line):
                sensor = PCASensor(line)
                self.sensors[sensor.sensorid] = sensor

                # if self._callback:
                #     self._callback(sensor, self._callback_data)

                # if sensor.sensorid in self._registry:
                #     for cbs in self._registry[sensor.sensorid]:
                #         cbs[0](sensor, cbs[1])

class PCASensor(object):
    """The PCA Sensor class."""
    # OK 24 1 5 6 150 140 1 255 255 255 255
    re_reading = re.compile(r'OK (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)')

    def __init__(self, line=None):
        print("init the PCASensor")
        if line:
            self._parse(line)

    def _parse(self, line):
        match = self.re_reading.match(line)
        print(match)
        if match:
            print("matching {}", match)
            return
            data = [int(c) for c in match.group().split()[1:]]
            self.sensorid = data[1]
            self.sensortype = data[2] & 0x7f
            self.new_battery = True if data[2] & 0x80 else False
            self.temperature = float(data[3] * 256 + data[4] - 1000) / 10
            self.humidity = data[5] & 0x7f
            self.low_battery = True if data[5] & 0x80 else False
