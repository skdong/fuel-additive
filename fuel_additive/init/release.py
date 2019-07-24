import os
import json
import yaml

from oslo_config import cfg
from oslo_log import log as logging
from nailgun.db import db
from nailgun.db.sqlalchemy.models.release import Release
from nailgun.db.sqlalchemy.models.deployment_sequence import DeploymentSequence

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


def add_deployment_sequences(release_id):
    session = db()
    q = session.query(DeploymentSequence)
    sequence = q.filter(DeploymentSequence.release_id == release_id).first()
    if not sequence:
        sequence = DeploymentSequence()
    sequence.release_id = release_id
    sequence.name = "deploy-changes"
    sequence.graphs = '[{"type": "provision"}, {"type": "default"}]'
    session.add(sequence)
    session.commit()


def add_release():
    name = "Kubernetes 1.14.3 on Centos 7"
    session = db()
    q = session.query(Release)
    release = q.filter(Release.name == name).first()
    if not release:
        release = Release()
    release.name = name
    release.version = "fuel-11.0"
    release.description = "This option will install the kubernetes 1.14.3 using a CentOS based operating system."
    release.operating_system = "CentOs"
    release.state = "available"

    with open(os.path.join(METADATA_PATH, 'modes.yml')) as fp:
        release.modes_metadata = yaml.safe_load(fp)

    with open(os.path.join(METADATA_PATH, 'networks.yml')) as fp:
        release.networks_metadata = yaml.safe_load(fp)

    with open(os.path.join(METADATA_PATH, 'attributes.yml')) as fp:
        release.attributes_metadata = yaml.safe_load(fp)

    with open(os.path.join(METADATA_PATH, 'roles.yml')) as fp:
        release.roles_metadata = yaml.safe_load(fp)

    release.modes = '["ha_compact"]'

    with open(os.path.join(METADATA_PATH, 'network_roles.yml')) as fp:
        release.network_roles_metadata = yaml.safe_load(fp)

    release.extensions = '{volume_manager,network_manager}'

    with open(os.path.join(METADATA_PATH, 'components.yml')) as fp:
        release.components_metadata = yaml.safe_load(fp)

    release.node_attributes = "{}"

    with open(os.path.join(METADATA_PATH, 'nic.yml')) as fp:
        release.nic_attributes = yaml.safe_load(fp)

    with open(os.path.join(METADATA_PATH, 'bond.yml')) as fp:
        release.bond_attributes = yaml.safe_load(fp)

    with open(os.path.join(METADATA_PATH, 'tags.yml')) as fp:
        release.tags_metadata = yaml.safe_load(fp)

    release.required_component_types = '["hypervisor", "network"]'

    with open(os.path.join(METADATA_PATH, 'volumes.yml')) as fp:
        release.volumes_metadata = yaml.safe_load(fp)

    session.add(release)
    session.commit()
    session.close()
    return release.id


def init_release():
    release = add_release()
    reload_release_graph(release)
    show_release_metadata(release)
    add_deployment_sequences(release)
