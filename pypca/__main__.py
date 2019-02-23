import pypca
import argparse
import logging
import json
import time

from pypca.exceptions import PCAException

_LOGGER = logging.getLogger('pcacl')


def setup_logging(log_level=logging.INFO):
    """Set up the logging."""
    logging.basicConfig(level=log_level)
    fmt = ("%(asctime)s %(levelname)s (%(threadName)s) "
           "[%(name)s] %(message)s")
    colorfmt = "%(log_color)s{}%(reset)s".format(fmt)
    datefmt = '%Y-%m-%d %H:%M:%S'

    # Suppress overly verbose logs from libraries that aren't helpful
    logging.getLogger('requests').setLevel(logging.WARNING)

    try:
        from colorlog import ColoredFormatter
        logging.getLogger().handlers[0].setFormatter(ColoredFormatter(
            colorfmt,
            datefmt=datefmt,
            reset=True,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red',
            }
        ))
    except ImportError:
        pass

    logger = logging.getLogger('')
    logger.setLevel(log_level)


def get_arguments():
    """Get parsed arguments."""
    parser = argparse.ArgumentParser("pyPCA: Command Line Utility")

    parser.add_argument(
        '-p', '--port',
        help='Serial port',
        required=True,
        default='/dev/ttyUSB0')

    parser.add_argument(
        '--scan',
        help='Scan for available devices',
        required=False, default=False, action="store_true")

    parser.add_argument(
        '-f', '--force_on',
        help='Force on all Devices',
        required=False, default=False, action="store_true")

    parser.add_argument(
        '-o', '--force_off',
        help='Force of all Devices',
        required=False, default=False, action="store_true")

    parser.add_argument(
        '--on',
        metavar='device_id',
        help='Turn on the device with the given id',
        required=False, action='append')

    parser.add_argument(
        '--off',
        metavar='device_id',
        help='Turn off the device with the given id',
        required=False, action='append')

    # parser.add_argument(
    #     '--home',
    #     help='Set to home mode',
    #     required=False, default=False, action="store_true")

    parser.add_argument(
        '--devices',
        help='Output all devices',
        required=False, default=False, action="store_true")

    # parser.add_argument(
    #     '--history',
    #     help='Get the history',
    #     required=False, default=False, action="store_true")

    # parser.add_argument(
    #     '--status',
    #     help='Get the status of the panel',
    #     required=False, default=False, action="store_true")

    parser.add_argument(
        '--debug',
        help='Enable debug logging',
        required=False, default=False, action="store_true")

    parser.add_argument(
        '--quiet',
        help='Output only warnings and errors',
        required=False, default=False, action="store_true")

    return parser.parse_args()


def call():
    """Execute command line helper."""
    args = get_arguments()

    if args.debug:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.WARN
    else:
        log_level = logging.INFO

    setup_logging(log_level)

    pca = None

    # if not args.username or not args.password or not args.ip_address:
    #         raise Exception("Please supply a username, password and ip.")

    # def _devicePrint(dev, append=''):
    #     _LOGGER.info("%s%s", dev.desc, append)

    try:
        # if args.username and args.password and args.ip_address:
        pca = pypca.PCA(args.port)
        pca.open()
        pca.get_ready()
        # pca.open()

        if args.scan:
            pca.start_scan()
            while True:
                time.sleep(1)

            # if pca.start_scan():
            #     _LOGGER.info('Started the scanner')
            # else:
            #     _LOGGER.warning('Failed to start the scanner')

        # if args.force_on:
        #     pca.force(1)

        # if args.force_off:
        #     pca.force(0)

        for device_id in args.on or []:
            pca.turn_on(device_id)
        
        for device_id in args.off or []:
            pca.turn_off(device_id)
            # device = pypca.get_device(device_id)

            # if device:
            #     if device.switch_on():
            #         _LOGGER.info("Switched on device with id: %s", device_id)
            # else:
            #         _LOGGER.warning("Could not find device with id: %s", device_id)

        # if args.home:
        #     if lupusec.get_alarm().set_home():
        #         _LOGGER.info('Alarm mode changed to home')
        #     else:
        #         _LOGGER.warning('Failed to change alarm mode to home')

        # if args.history:
        #     _LOGGER.info(json.dumps(lupusec.get_history()['hisrows'], indent=4, sort_keys=True))

        # if args.status:
        #     _LOGGER.info('Mode of panel: %s', lupusec.get_alarm().mode)

        if args.devices:
            for device in pca.get_devices():
                _LOGGER.info("Found PCA 301 with ID: " + device)

            # for device in pca.get_devices():
            #     print(device)
                # _devicePrint(device)

    except pypca.PCAException as exc:
        _LOGGER.error(exc)
    finally:
        if pca is not None:
            pca.close()
            _LOGGER.info('--Finished running--')


def main():
    """Execute from command line."""
    call()


if __name__ == '__main__':
    main()
