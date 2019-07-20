import os
import json

from oslo_config import cfg
from oslo_log import log as logging
from nailgun.db import db
from nailgun.db.sqlalchemy.models.release import Release

from fuel_agent import errors
from fuel_agent.utils import utils

from fuel_additive.cmd.base import load_config

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

PATH = "/etc/fuel/additive"
METADATA_PATH = os.path.join(PATH, 'kubernetes_metadata')
NAME = "Kubernetes on CentOS 7"
VERSION = "kube-11.0"
DESCRIPTION = "install kubernetes"
OPERATING_SYSTEM = "Centos"
STATE = "available"
NETWORK_METADATE = None
ATTRIBUTES_METADATE = None


def add_kubernetes_release():
    # TODO add release
    # TODO set attr
    # TODO add deployment sequence
    pass


def upload_release_graps():
    # TODO provision
    # TODO delete
    pass


def reload_release_graph(release_id):
    try:
        utils.execute('fuel2 graph delete', '-r', str(release_id), '-t provision')
    except errors.ProcessExecutionError as err:
        pass
    utils.execute('fuel2 graph upload -r', str(release_id), '-d', os.path.join(PATH, 'graph'), '-t provision')


def show_release_metadata(release_id):
    session = db()
    q = session.query(Release)
    release = q.get(release_id)
    LOG.debug("metadata")
    LOG.debug(json.dumps(release.attributes_metadata, indent=4))

    LOG.debug("roles")
    LOG.debug(json.dumps(release.roles_metadata, indent=4))
    session.close()


def reset_release(release_id):
    session = db()
    q = session.query(Release)
    release = q.get(release_id)

    with open(os.path.join(METADATA_PATH, 'attributes.json')) as fp:
        release.attributes_metadata = json.load(fp)

    with open(os.path.join(METADATA_PATH, 'roles.json')) as fp:
        release.roles_metadata = json.load(fp)

    with open(os.path.join(METADATA_PATH, 'tags.json')) as fp:
        release.tags_metadata = json.load(fp)

    session.add(release)
    session.commit()
    session.close()


def init_release():
    release = 5
    reload_release_graph(release)
    reset_release(release)
    show_release_metadata(release)