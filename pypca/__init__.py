from __future__ import unicode_literals
import logging
from serial import Serial
import sys
import pickle
import re
import threading
import time

from pathlib import Path

home = str(Path.home())

from pypca.exceptions import PCAException

import pypca.constants as CONST

_LOGGER = logging.getLogger(__name__)


class PCA():

    _registry = {}
    _callback = None
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
        self._callback_data = None

        # try:
        #     self.sensors = pickle.load(open(home + "/" + CONST.KNOWN_DEVICES_NAME, "rb"))
        # except (OSError, IOError) as e:
        #     _LOGGER.warning('Reading known devices cache failed: %s', e)
        #     pickle.dump(self.sensors, open(home + "/" + CONST.KNOWN_DEVICES_NAME, "wb"))

    def open(self):
        """Open the device."""
        self._serial.port = self._port
        self._serial.baudrate = self._baud
        self._serial.timeout = self._timeout
        self._serial.open()
        self._serial.flushInput()
        self._serial.flushOutput()

    def close(self):
        """Close the device."""
        self._stop_worker()
        self._serial.close()
    
    def get_ready(self):
        """Wait til the device is ready"""
        line = self._serial.readline().decode('utf-8')

        while self._re_reading.match(line) is None:
            line = self._serial.readline().decode('utf-8')
            time.sleep(0.1) #sleep here, otherwise the loop will lock the serial interface
        return True

    def get_devices(self):
        """Get all the devices with the help of the l switch"""
        self.get_ready()

        self._write_cmd('l')
        line = self._serial.readline().decode('utf-8')

        while self._re_devices.match(line) is not None:
            # add the line to devices dict
            deviceId = line.split(' ')
            deviceId = str(deviceId[7]).zfill(
                3) + str(deviceId[8]).zfill(3) + str(deviceId[9]).zfill(3)
            self._devices[deviceId] = {}
            line = self._serial.readline().decode('utf-8')
            time.sleep(0.1) #sleep here, otherwise the loop will lock the serial interface
        print(self._devices)
        return self._devices
    
    def get_current_power(self, deviceId):
        return self._devices[deviceId]['power']

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
        if self._thread is not None:
            return
        self._stopevent = threading.Event()
        self._thread = threading.Thread(target=self._refresh, args=())
        self._thread.daemon = True
        self._thread.start()

    def force(self, state):
        self.start_scan()
        while len(self._devices) == 0:
            time.sleep(1)
        for sensor in self._devices:
            address = self._devices[sensor].sensorid.split('-')
            onCommand = '1,5,{},{},{},{},255,255,255,255{}'.format(
                address[0], address[1], address[2], state, CONST.SEND_SUFFIX)
            self._write_cmd(onCommand)

    def turn_off(self, deviceId):
        # error catching deviceid too short
        address = re.findall('...', deviceId)
        offCommand = '1,5,{},{},{},{},255,255,255,255{}'.format(
            address[0].lstrip('0'), address[1].lstrip('0'), address[2].lstrip('0'), '0', CONST.SEND_SUFFIX)
        self._write_cmd(offCommand)
        print("try to turn of " + offCommand)
        return True

    def turn_on(self, deviceId):
        # error catching deviceid too short
        address = re.findall('...', deviceId)
        onCommand = '1,5,{},{},{},{},255,255,255,255{}'.format(
            address[0].lstrip('0'), address[1].lstrip('0'), address[2].lstrip('0'), '1', CONST.SEND_SUFFIX)
        # time.sleep(2)
        self._write_cmd(onCommand)
        # self._serial.write(onCommand.encode())
        print(onCommand)
        print("try to turn on")
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
                # sensor = PCASensor(line)
                # self._devices[sensor.sensorid] = sensor
                self._devices[deviceId]['power'] = (
                    int(line[8]) * 256 + int(line[9])) / 10.0
                self._devices[deviceId]['status'] = int(line[7])
                print(self._devices[deviceId]['power'])
                print(line)
                # if self._callback:
                #     self._callback(sensor, self._callback_data)

                # if sensor.sensorid in self._registry:
                #     for cbs in self._registry[sensor.sensorid]:
                #         cbs[0](sensor, cbs[1])


# class PCASensor(object):
#     """The PCA Sensor class."""
#     # OK 24 1 5 6 150 140 1 255 255 255 255
   

#     def __init__(self, line=None):
#         if line:
#             match = self.re_reading.match(line)
#             if match:
#                 data = [int(c) for c in match.group().split()[1:]]
#                 self.channel = data[1]
#                 self.sensorid = str(data[3]) + '-' + \
#                     str(data[4]) + '-' + str(data[5])
#                 self.state = data[6]
#                 self.power = (data[7] * 256 + data[8]) / 10.0
#                 self.consumption = (data[9] * 256 + data[10]) / 100.0
