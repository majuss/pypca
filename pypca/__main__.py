import pypca
import argparse
import logging
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
        help='Scan continously and update the devices cache',
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

    parser.add_argument(
        '--devices',
        help='Output all devices which are registred with the JeeLink',
        required=False, default=False, action="store_true")

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

    try:
        pca = pypca.PCA(args.port)
        pca.open()
        if args.scan:
            pca.start_scan()
            while True:
                time.sleep(1)

        for device_id in args.on or []:
            pca.get_devices()
            pca.turn_on(device_id)

        for device_id in args.off or []:
            pca.get_devices()
            pca.turn_off(device_id)

        if args.devices:
            devices = pca.get_devices()
            if devices:
                for device in devices:
                    _LOGGER.info("Found PCA 301 with ID: " + device)
            else:
                _LOGGER.info("No PCA devices found, please make sure you plug them in")

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
