import json
import logging

logger = logging.getLogger("supplyrca")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())


def emit(event, **fields):
    logger.info(json.dumps({"event": event, **fields}, default=str))
