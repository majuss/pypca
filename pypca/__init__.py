from __future__ import unicode_literals
from pathlib import Path
from time import time

import logging
import serial
import re
import threading
import pypca.constants as CONST
import pickle

home = str(Path.home())

_LOGGER = logging.getLogger(__name__)


# get ready-> get last line not second or something, or flush output after ready
class PCA:

    _serial = None
    _stopevent = None
    _thread = None
    _re_reading = re.compile(
        r"OK 24 (\d+) 4 (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)"
    )
    _re_devices = re.compile(
        r"L 24 (\d+) (\d+) : (\d+) 4 (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)"
    )

    def __init__(self, port, timeout=2):
        """Initialize the pca device."""
        self._devices = {}
        self._port = port
        self._baud = 57600
        self._timeout = timeout
        self._serial = serial.Serial(timeout=timeout)

        try:
            self._known_devices = pickle.load(open(home + "/.pca_devices", "rb"))
        except (OSError, IOError) as e:
            _LOGGER.debug("No known devices file found {}".format(e))
            self._known_devices = []
            pickle.dump(self._known_devices, open(home + "/.pca_devices", "wb"))

    def open(self):
        """Open the device."""
        self._serial.port = self._port
        self._serial.baudrate = self._baud
        self._serial.timeout = self._timeout
        self._serial.open()
        self._serial.flushInput()
        self._serial.flushOutput()
        self.get_ready()

    def close(self):
        """Close the device."""
        self._stop_worker()
        self._serial.close()

    def get_ready(self):
        """Wait til the device is ready"""
        line = self._serial.readline().decode("utf-8")
        start = time()
        timeout = 2
        while self._re_reading.match(line) is None and time() - start < timeout:
            line = self._serial.readline().decode("utf-8")
        return True
    
    def get_devices(self, fast=0):
        """Get all the devices with the help of the l switch"""  # When the EEPROM is fried this is basically useless
        _LOGGER.info("Please press the button on you PCA")
        line = []
        start = int(time())
        found = False
        if fast:
            CONST.DISCOVERY_TIME = 5
            CONST.DISCOVERY_TIMEOUT = 5
        for device in self._known_devices:
            self._devices[device] = {}
            self._devices[device]['state'] = 0
            self._devices[device]['consumption'] = 0
            self._devices[device]['power'] = 0

        while not (int(time()) - start > CONST.DISCOVERY_TIMEOUT) or not (int(time()) - start > CONST.DISCOVERY_TIME or found):
            line = self._serial.readline().decode("utf-8")
            if len(line) > 1:
                line = line.split(" ")
                if line[8] is not '170' or line[9] is not '170':
                    deviceId = str(line[4]).zfill(3) + str(line[5]).zfill(3) + str(line[6]).zfill(3)
                    self._devices[deviceId] = {}
                    self._devices[deviceId]["power"] = (
                        int(line[8]) * 256 + int(line[9])
                    ) / 10.0
                    self._devices[deviceId]["state"] = int(line[7])
                    self._devices[deviceId]["consumption"] = (
                        int(line[10]) * 256 + int(line[11])
                    ) / 100.0                
                    if deviceId in self._known_devices:
                        _LOGGER.info("Skip device with ID {}, because it's already known.".format(deviceId))
                    else:
                        _LOGGER.info("New device found will wait for another device for {} seconds...".format(CONST.DISCOVERY_TIME))
                        self._known_devices.append(deviceId)
                        found = True
                        start = time()
        pickle.dump(self._known_devices, open(home + "/.pca_devices", "wb"))
        return self._devices

    def get_current_power(self, deviceId):
        """Get current power usage of given DeviceID."""
        return self._devices[deviceId]["power"]

    def get_total_consumption(self, deviceId):
        """Get total power consumption of given DeviceID in KWh."""
        return self._devices[deviceId]["consumption"]

    def get_state(self, deviceId):
        """Get state of given DeviceID."""
        return self._devices[deviceId]["state"]

    def _stop_worker(self):
        if self._stopevent is not None:
            self._stopevent.set()
        if self._thread is not None:
            self._thread.join()

    def start_scan(self):
        """Start scan task in background."""
        self.get_devices(1)
        self._start_worker()

    def _write_cmd(self, cmd):
        """Write a cmd."""
        self._serial.write(cmd.encode())

    def _start_worker(self):
        """Start the scan worker."""
        if self._thread is not None:
            return
        self._stopevent = threading.Event()
        self._thread = threading.Thread(target=self._refresh, args=())
        self._thread.daemon = True
        self._thread.start()

    def turn_off(self, deviceId):
        """Turn off given DeviceID."""
        address = re.findall("...", deviceId)
        offCommand = "1,5,{},{},{},{},255,255,255,255{}".format(
            address[0].lstrip("0"),
            address[1].lstrip("0"),
            address[2].lstrip("0"),
            "0",
            CONST.SEND_SUFFIX,
        )
        self._write_cmd(offCommand)
        self._devices[deviceId]["state"] = 0
        return True

    def turn_on(self, deviceId):
        """Turn on given DeviceID."""
        address = re.findall("...", deviceId)
        onCommand = "1,5,{},{},{},{},255,255,255,255{}".format(
            address[0].lstrip("0"),
            address[1].lstrip("0"),
            address[2].lstrip("0"),
            "1",
            CONST.SEND_SUFFIX,
        )
        self._write_cmd(onCommand)
        self._devices[deviceId]["state"] = 1
        return True

    def _refresh(self):
        """Background refreshing thread."""
        while not self._stopevent.isSet():
            line = self._serial.readline()
            # this is for python2/python3 compatibility. Is there a better way?
            try:
                line = line.encode().decode("utf-8")
            except AttributeError:
                line = line.decode("utf-8")
            if self._re_reading.match(line):
                line = line.split(" ")
                deviceId = (
                    str(line[4]).zfill(3)
                    + str(line[5]).zfill(3)
                    + str(line[6]).zfill(3)
                )
                self._devices[deviceId]["power"] = (
                    int(line[8]) * 256 + int(line[9])
                ) / 10.0
                self._devices[deviceId]["state"] = int(line[7])
                self._devices[deviceId]["consumption"] = (
                    int(line[10]) * 256 + int(line[11])
                ) / 100.0
