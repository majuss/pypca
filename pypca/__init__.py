from __future__ import unicode_literals
import logging
from serial import Serial
import re
import threading
import time

from pypca.exceptions import PCAException
import pypca.constants as CONST

_LOGGER = logging.getLogger(__name__)

#get ready-> get last line not second or something, or flush output after ready
class PCA():

    _serial = None
    _stopevent = None
    _thread = None
    _re_reading = re.compile(
        r'OK 24 (\d+) 4 (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)')
    _re_devices = re.compile(
        r'L 24 (\d+) (\d+) : (\d+) 4 (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)')

    def __init__(self, port, timeout=2):
        """Initialize the pca device."""
        self._devices = {}
        self._port = port
        self._baud = 57600
        self._timeout = timeout
        self._serial = Serial(timeout=timeout)

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
        line = self._serial.readline().decode('utf-8')
        start = time.time()
        timeout = 5
        while self._re_reading.match(line) is None and time.time() - start < timeout:
            line = self._serial.readline().decode('utf-8')
        return True

    def get_devices(self):
        """Get all the devices with the help of the l switch"""
        self._write_cmd('l')
        line = self._serial.readline().decode('utf-8')
        while self._re_devices.match(line) is not None:
            # add the line to devices dict
            line = line.split(' ')
            deviceId = str(line[7]).zfill(
                3) + str(line[8]).zfill(3) + str(line[9]).zfill(3)
            self._devices[deviceId] = {}
            self._devices[deviceId]['state'] = line[10]
            self._devices[deviceId]['power'] = (
                int(line[11]) * 256 + int(line[12])) / 10.0
            self._devices[deviceId]['consumption'] = (
                int(line[13]) * 256+ int(line[14])) / 100.0
            line = self._serial.readline().decode('utf-8')
            time.sleep(0.05) #sleep here, otherwise the loop will lock the serial interface
        return self._devices
    
    def get_current_power(self, deviceId):
        """Get current power usage of given DeviceID."""
        return self._devices[deviceId]['power']

    def get_total_consumption(self, deviceId):
        """Get total power consumption of given DeviceID in KWh."""
        return self._devices[deviceId]['consumption']

    def get_state(self, deviceId):
        """Get state of given DeviceID."""
        return self._devices[deviceId]['state']

    def _stop_worker(self):
        if self._stopevent is not None:
            self._stopevent.set()
        if self._thread is not None:
            self._thread.join()

    def start_scan(self):
        """Start scan task in background."""
        self.get_devices()
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
        address = re.findall('...', deviceId)
        offCommand = '1,5,{},{},{},{},255,255,255,255{}'.format(
            address[0].lstrip('0'), address[1].lstrip('0'), address[2].lstrip('0'), '0', CONST.SEND_SUFFIX)
        self._write_cmd(offCommand)
        self._devices[deviceId]['state'] = 0
        return True

    def turn_on(self, deviceId):
        """Turn on given DeviceID."""
        address = re.findall('...', deviceId)
        onCommand = '1,5,{},{},{},{},255,255,255,255{}'.format(
            address[0].lstrip('0'), address[1].lstrip('0'), address[2].lstrip('0'), '1', CONST.SEND_SUFFIX)
        self._write_cmd(onCommand)
        self._devices[deviceId]['state'] = 1
        return True

    def _refresh(self):
        """Background refreshing thread."""

        while not self._stopevent.isSet():
            line = self._serial.readline()
            # this is for python2/python3 compatibility. Is there a better way?
            try:
                line = line.encode().decode('utf-8')
            except AttributeError:
                line = line.decode('utf-8')

            if self._re_reading.match(line):
                line = line.split(' ')
                deviceId = str(line[4]).zfill(
                    3) + str(line[5]).zfill(3) + str(line[6]).zfill(3)
                self._devices[deviceId]['power'] = (
                    int(line[8]) * 256 + int(line[9])) / 10.0
                self._devices[deviceId]['state'] = int(line[7])
                self._devices[deviceId]['consumption'] = (
                    int(line[10]) * 256+ int(line[11])) / 100.0
