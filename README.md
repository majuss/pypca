# pypca

A python3 library to communicate with the ELV PCA 301 a smart plug which transmit the energy consumption.

## Disclaimer:

Published under the MIT license - See LICENSE file for more details.

## Installation

You can install the library with pip:
```
pip install pypca
```

## Usage

You can integrate the library into your own project, or simply use it in the command line. Please turn your PCAs on via the button to initially scan for devices, otherwise they cannot be identified.
```
pypca --devices
```
This will retrieve a simple list of all devices.

---
