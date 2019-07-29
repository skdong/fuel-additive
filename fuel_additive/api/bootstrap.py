from oslo_log import log as logging
from oslo_config import cfg

from fuel_agent.utils import utils
from fuel_additive.drivers.os.bootstrap import Bootstrap as Driver

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class Bootstrap(object):
    def __init__(self, data):
        self.config = utils.get_driver(CONF.data_driver)(data)

    def create(self):
        driver = Driver.create(self.config)
        driver.build()