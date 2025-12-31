import logging
LOG = logging.getLogger("ai_stock_agent")
if not LOG.handlers:
    h = logging.StreamHandler()
    fmt = "%(asctime)s %(levelname)s %(message)s"
    h.setFormatter(logging.Formatter(fmt))
    LOG.addHandler(h)
    LOG.setLevel(logging.INFO)
