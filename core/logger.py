__all__ = ("logger",
           )

import logging

logger = logging.getLogger("repairnet")
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler("repairnet.log")
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

