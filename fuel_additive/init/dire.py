import os
from oslo_config import cfg
from oslo_log import log as logging

from fuel_agent.utils import utils
from fuel_additive.init.astute import SETTINGS

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

cli_opts = [
    cfg.StrOpt(name="dire_boot_path",
               default="/opt/dire/boot",
               help="dire/boot project path")
]

CONF.register_cli_opts(cli_opts)


def _load_envs():
    envs = {"HOST":SETTINGS["ADMIN_NETWORK"]["ipaddress"],
            "DOMAIN":SETTINGS["DNS_DOMAIN"],
            "HOST_NAME": '.'.join([SETTINGS["HOSTNAME"], SETTINGS["DNS_DOMAIN"]])}
    for variate in envs:
        os.putenv(variate, envs[variate])


def _init_servers():
    utils.execute("bash", os.path.join(CONF.dire_boot_path, "boot/servers/sit.sh"))


def init():
    # TODO
    _load_envs()
    _init_servers()
