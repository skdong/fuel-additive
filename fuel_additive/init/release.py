import json
import os

import yaml
from fuel_agent import errors
from fuel_agent.utils import utils
from nailgun.db import db
from nailgun.db.sqlalchemy.models.deployment_sequence import DeploymentSequence
from nailgun.db.sqlalchemy.models.release import Release
from oslo_config import cfg
from oslo_log import log as logging

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

FUEL_PATH = u"/etc/fuel"
PATH = os.path.join(FUEL_PATH, u"additive")
METADATA_PATH = os.path.join(PATH, 'kubernetes_metadata')
NAME = "Kubernetes 1.14.3 on Centos 7"
VERSION = "kube-11.0"
DESCRIPTION = "install kubernetes"
OPERATING_SYSTEM = "Centos"
STATE = "available"
NETWORK_METADATE = None
ATTRIBUTES_METADATE = None

cli_opts = [
    cfg.StrOpt(name="kubernetes_release_name",
               default=NAME,
               help="the name of kubernetes release")
]
CONF.register_cli_opts(cli_opts)


def reload_release_graph(release_id):
    try:
        utils.execute(u'fuel2 graph delete', u'-r', str(release_id), u'-t provision')
    except errors.ProcessExecutionError as err:
        LOG.warn(err)
    utils.execute(u'fuel2 graph upload -r', str(release_id), '-d', os.path.join(PATH, 'graph', 'provision'),
                  u'-t provision')

    try:
        utils.execute(u'fuel2 graph delete', u'-r', str(release_id), u'-t deletion')
    except errors.ProcessExecutionError as err:
        LOG.warn(err)
    utils.execute(u'fuel2 graph upload -r', str(release_id), '-d', os.path.join(FUEL_PATH, 'graphs', 'deletion'),
                  u'-t deletion')

    try:
        utils.execute(u'fuel2 graph delete', u'-r', str(release_id), u'-t default')
    except errors.ProcessExecutionError as err:
        LOG.warn(err)
    utils.execute(u'fuel2 graph upload -r', str(release_id), '-d', os.path.join(PATH, 'graphs', 'default'),
                  u'-t default')


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
    sequence.graphs = [{"type": "provision"}, {"type": "default"}]
    session.add(sequence)
    session.commit()


def load_data(name, form="yml"):
    with open(os.path.join(METADATA_PATH, name + '.' + form)) as fp:
        if form in ["yaml", "yml"]:
            return yaml.safe_load(fp)
        elif form == "json":
            return json.load(fp)


def add_release():
    name = u"Kubernetes 1.14.3 on Centos 7"
    session = db()
    q = session.query(Release)
    release = q.filter(Release.name == name).first()
    if not release:
        release = Release()
    release.name = name
    release.version = u"fuel-11.0"
    release.description = u"This option will install the kubernetes 1.14.3 using a CentOS based operating system."
    release.operating_system = u"CentOS"
    release.state = u"available"
    release.modes_metadata = load_data("modes")
    release.networks_metadata = load_data("networks")
    release.attributes_metadata = load_data("attributes")
    release.roles_metadata = load_data("roles")
    release.modes = [u"ha_compact"]
    release.network_roles_metadata = load_data("network_roles")
    release.extensions = {u'volume_manager', u'network_manager'}
    release.components_metadata = load_data("components")
    release.node_attributes = {}
    release.nic_attributes = load_data("nic")
    release.bond_attributes = load_data("bond")
    release.tags_metadata = load_data("tags")
    release.required_component_types = ["hypervisor", "network"]
    release.volumes_metadata = load_data("volumes")
    session.add(release)
    session.commit()
    release_id = release.id
    session.close()
    return release_id


def init_release():
    release = add_release()
    reload_release_graph(release)
    show_release_metadata(release)
    add_deployment_sequences(release)
