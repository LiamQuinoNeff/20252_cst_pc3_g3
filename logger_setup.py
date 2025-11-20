import logging
import logging.handlers
import os


def get_logger(name='spade_sim'):
    # asegurar que existe el directorio `report`
    base = os.path.dirname(__file__)
    report_dir = os.path.join(base, 'report')
    os.makedirs(report_dir, exist_ok=True)
    log_path = os.path.join(report_dir, 'run.log')

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # manejador de archivo (rotativo)
    fh = logging.handlers.RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3, encoding='utf-8')
    fh.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # añadir también un manejador a consola en nivel INFO
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # evitar duplicación de logs hacia handlers superiores
    logger.propagate = False
    return logger
