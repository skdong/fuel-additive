import json
import os
import shutil
import signal
import sys
from io import open

import six
import yaml
from fuel_agent import errors
from fuel_agent import manager as manager
from fuel_agent.utils import build as bu
from fuel_agent.utils import fs as fu
from fuel_agent.utils import utils
from oslo_config import cfg
from oslo_log import log as logging


CONF = cfg.CONF
LOG = logging.getLogger(__name__)
PROJECT = 'fuel-agent'


class Provisoner(object):
    pass


def provision():
    load_opts()


def load_opts():
    logging.register_options(CONF)
    CONF(sys.argv[1:], project=PROJECT)
    logging.setup(CONF, PROJECT)


def preview():
    load_opts()
    print CONF.data_driver
    CONF.data_driver = 'nailgun_build_image'
    print CONF.data_driver


def main():
    build()


if __name__ == "__main__":
    main()