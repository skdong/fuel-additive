import sys

from oslo_config import cfg
from oslo_log import log as logging

CONF = cfg.CONF


def load_config(project=None):
    logging.register_options(CONF)
    CONF(sys.argv[1:], project=project)
    logging.setup(CONF, project)
