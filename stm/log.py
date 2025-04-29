import argparse
import logging
import sys


_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument("--log")
_args, sys.argv[1:] = _parser.parse_known_args()

if _args.log:
    numeric_log_level = getattr(logging, _args.log.upper(), None)
    logging.basicConfig(level=numeric_log_level)

logger = logging.getLogger(__name__)
