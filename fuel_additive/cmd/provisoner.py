import collections
import json
import os
import sys
from io import open

from fuel_agent import manager as manager
from fuel_agent.utils import utils
from oslo_config import cfg
from oslo_log import log as logging

CONF = cfg.CONF
LOG = logging.getLogger(__name__)
PROJECT = 'fuel-additive'

cli_opts = [
    cfg.StrOpt(
        'input_data_file',
        default='/tmp/provision.json',
        help='Input data file'
    ),
    cfg.StrOpt(
        'input_data',
        default='',
        help='Input data (json string)'
    ),
]


class Script(object):
    def __init__(self, name=None):
        self.name = name
        self.context = list()

    def add(self, line):
        self.context.append(line)

    def generate(self):
        return ''.join(self.context)


class Scripts(object):
    KEY_WORD = u"scriptlet"
    POST_TRANS = u"posttrans"

    def __init__(self, script_info):
        self.info = script_info
        self._scripts = collections.defaultdict(Script)

    def add(self, line):
        script = Script(line.split()[0])
        self._scripts[script.name] = script

    def parser(self):
        script = None
        for line in self.info.split_lines():
            if self.KEY_WORD in line:
                self.add(line)
            elif script:
                script.add(line)

    def get_trans_post(self, ):
        return self._scripts.get(self.POST_TRANS).generate()


class RPMManager(object):
    def __init__(self, chroot, name):
        self._chroot = chroot
        self.name = name

    def _get_scripts(self):
        out, _ = self.chroot_execute('rpm', '-q', '--scripts', self.name)
        return out

    def chroot_execute(self, *args, **kwargs):
        return utils.execute('chroot', self._chroot, *args, **kwargs)

    def execute_post_trans(self):
        cmd_path = os.path.join('/', 'tmp', 'posttrun.sh')
        scripts = Scripts(self._get_scripts())
        scripts.parser()
        with open(os.path.join(self._chroot, cmd_path), 'w') as fp:
            fp.write(scripts.get_trans_post())
        os.chmod(os.path.join(self._chroot, cmd_path), 0700)
        self.chroot_execute('sh', cmd_path)
        os.unlink(os.path.join(self._chroot, cmd_path))


class Provisoner(object):
    def __init__(self, manager):
        self.manager = manager
        super(Provisoner, self)

    def provision(self):
        # TODO rebuild initramfs
        # TODO relink /etc/mtab
        LOG.debug('--- fix bug ---')
        chroot = '/tmp/target'
        self.manager.mount_target(chroot, treat_mtab=False)
        try:
            _relink_mtab(chroot)
            _rebuild_initramfs(chroot)
        except Exception as err:
            LOG.error(err)
            self.manager.umount_target()
        self.manager.umount_target()

    @classmethod
    def factory(cls):
        with open(CONF.input_data_file) as fp:
            data = json.load(fp)
        return cls(manager.Manager(data))


def _relink_mtab(chroot):
    mtab_path = os.path.join(chroot,  '/etc/mtab')
    if not os.path.islink(mtab_path):
        os.remove(mtab_path)
        utils.execute('chroot', chroot,
                      'ln', '-s', '/proc/self/mounts', '/etc/mtab')


def _rebuild_initramfs(chroot):
    package = 'kernel'
    RPMManager(chroot, package).execute_post_trans()


def provision():
    load_opts()
    provisioner = Provisoner.factory()
    provisioner.provision()


def load_opts():
    logging.register_options(CONF)
    CONF.register_cli_opts(cli_opts)
    CONF(sys.argv[1:], project=PROJECT)
    logging.setup(CONF, PROJECT)


def main():
    provision()


if __name__ == "__main__":
    main()
