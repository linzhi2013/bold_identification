import logging
import os
import sys

def get_logger(debug=False):
    # 级别排序:CRITICAL > ERROR > WARNING > INFO > DEBUG
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)  # must be DEBUG, then 'ch' below works.
    # logger.setFormatter(formatter)

    fh = logging.FileHandler(os.path.basename(sys.argv[0]) + '.log')
    if debug:
        fh.setLevel(logging.DEBUG)
    else:
        fh.setLevel(logging.INFO)  # INFO level goes to the log file
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    if debug:
        ch.setLevel(logging.DEBUG)
    else:
        ch.setLevel(logging.WARNING)  # only WARNING level will output on screen
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger