import os

import requests
from fuel_agent.utils import utils
from oslo_config import cfg
from oslo_log import log as logging

from fuel_additive.init.astute import SETTINGS

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

cli_opts = [
    cfg.StrOpt(name="dire_boot_path",
               default="/opt/dire/boot",
               help="dire/boot project path"),
    cfg.StrOpt(name="nexus_user",
               default="admin",
               help="nexus auth user"),
    cfg.StrOpt(name="nexus_password",
               default="admin123",
               help="nexus auth password")
]

CONF.register_cli_opts(cli_opts)

nexus_repositories = ["docker", "pypi"]


def _get_nexus_session():
    session = requests.Session()
    session.auth = (CONF.nexus_user, CONF.nexus_password)
    session.headers.update({'Content-Type': 'application/json'})
    return session


def _get_nexus_url():
    endpoint = u"service/extdirect"
    return "http://{host}/{endpoint}".format(host=SETTINGS["ADMIN_NETWORK"]["ipaddress"],
                                             endpoint=endpoint)


def _create_repositories():
    session = _get_nexus_session()

    for repository in nexus_repositories:
        with open(os.path.join("/etc/fuel/additvie/nexus", repository)) as fp:
            data = fp.read()
        session.post(_get_nexus_url(), data=data)


def _load_envs():
    envs = {"HOST": SETTINGS["ADMIN_NETWORK"]["ipaddress"],
            "DOMAIN": SETTINGS["DNS_DOMAIN"],
            "HOST_NAME": '.'.join([SETTINGS["HOSTNAME"], SETTINGS["DNS_DOMAIN"]])}
    texts = ["export {}={}".format(key, value) for key, value in envs.items()]
    with open(os.path.join(CONF.dire_boot_path, "tools", "bootrc"), "w") as fp:
        fp.write("\n".join(texts))


def _init_servers():
    utils.execute("bash", os.path.join(CONF.dire_boot_path, "tools/deploy.sh"), "serve")


def _upload_packages():
    utils.execute("bash", os.path.join(CONF.dire_boot_path, "tools/upload.sh"), "all")


def init():
    LOG.info("create bootrc")
    _load_envs()
    LOG.inof("start nexus")
    _init_servers()
    LOG.inof("create nexus repositories")
    _create_repositories()
    LOG.info("upload packages to nexus repositories")
    _upload_packages()
