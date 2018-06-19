import logging


class SetLogging(object):

  @staticmethod
  def setup_logging(): # pragma: no cover
    logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s',level=logging.INFO)
    logging.info("Begin Logging...")

