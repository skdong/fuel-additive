import os

from oslo_log import log as logging
from oslo_config import cfg

from fuel_agent.utils import utils
from fuel_agent.errors import ProcessExecutionError

from fuel_additive import contants

LOG = logging.getLogger(__name__)

CONF = cfg.CONF

cli_opts = [
    cfg.StrOpt(name="docker_package",
               default="/opt/dire/packages/apps/docker-18.09.7.tgz",
               help="docker package path get from https://download.docker.com/linux/static/stable/x86_64/"
               ),
    cfg.StrOpt(name="docker_images",
               default="/opt/dire/packages/images/docker.tar.gz",
               help="build by dire/boot project"
               ),
]


CONF.register_cli_opts(cli_opts)


DOCKER_INIT_PATH = os.path.join(contants.RUN_PATH, "docker")


def _exists():
    return os.path.isfile("/usr/local/dockerd")


def _uninstall_docker():
    try:
        utils.execute("systemctl stop docker")
        utils.execute("yum erase docker")
    except ProcessExecutionError as err:
        LOG.warn(err)


def _uncompres_package():
    utils.execute("tar -zxvf", CONF.docker_pacakge, "-C /tmp")


def _move_binary():
    utils.execute("mv /tmp/docker/* /usr/local/sbin/docker")


def _set_config():
    # TODO set docker config
    pass


def _create_service():
    with open("/usr/lib/systemd/system/docker.service", 'w') as fp:
        fp.write(contants.DOCKER_SERVICE)


def _start_service():
    utils.execute("systemctl start docker")
    utils.execute("systemctl.enable docker")


def _enable_service():
    utils.execute("systemctl enable docker")


def _link_docker():
    utils.execute("ln -s /usr/local/sbin/docker /usr/sbin")


def _load_images():
    if os.path.isfile(CONF.docker_images):
        utils.execute("systemctl stop docker")
        utils.execute("rm -rf /var/lib/docker")
        utils.execute("tar -zxvf ", CONF.docker_images, "-C / ")
        utils.execute("systemctl start docker")
    else:
        LOG.warn("docker package %s is not exits", CONF.docker_images)


def init():
    if _exists():
        _uninstall_docker()
        _uncompres_package()
        _move_binary()
        _set_config()
        _create_service()
        _link_docker()
    _load_images()
