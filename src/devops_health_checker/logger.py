import logging


def setup_logger(level=logging.INFO):
    logger = logging.getLogger("devops-health-checker")

    if logger.handlers:
        return logger

    logger.setLevel(level)

    handler = logging.StreamHandler()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger