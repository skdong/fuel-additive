import collections
import json
import os
import sys

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
        return '\n'.join(self.context)


class Scripts(object):
    KEY_WORD = u"scriptlet"
    POST_TRANS = u"posttrans"

    def __init__(self, script_info):
        self.info = script_info
        self._scripts = collections.defaultdict(Script)
        self.parsed = False
        self._parse()

    def _parse(self):
        if self.parsed:
            return
        script = None
        for line in self.info.splitlines():
            if self.KEY_WORD in line:
                script = Script(line.split()[0])
                self._scripts[script.name] = script
            elif script:
                script.add(line)
        self.parsed = True

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
        cmd_path = os.path.join('tmp', 'posttrun.sh')
        scripts = Scripts(self._get_scripts())
        with open(os.path.join(self._chroot, cmd_path), 'w') as fp:
            fp.write(scripts.get_trans_post())
        os.chmod(os.path.join(self._chroot, cmd_path), 0o700)
        self.chroot_execute('sh', os.path.join('/', cmd_path))
        os.unlink(os.path.join(self._chroot, cmd_path))


class Provisioner(object):
    def __init__(self, manager):
        self.manager = manager
        super(Provisioner, self)

    def provision(self):
        LOG.debug('--- fix bug ---')
        chroot = '/tmp/target'
        try:
            self.manager.mount_target(chroot, treat_mtab=False)
            _relink_mtab(chroot)
            _rebuild_initramfs(chroot)
        except Exception as err:
            LOG.error(err)
            self.manager.umount_target(chroot)
            raise
        self.manager.umount_target(chroot)

    @classmethod
    def create(cls):
        with open(CONF.input_data_file) as fp:
            data = json.load(fp)
        return cls(manager.Manager(data))


def _relink_mtab(chroot):
    mtab_path = os.path.join(chroot,  'etc/mtab')
    os.remove(mtab_path)
    utils.execute('chroot', chroot,
                  'ln', '-s', '/proc/self/mounts', '/etc/mtab')


def _rebuild_initramfs(chroot):
    package = 'kernel'
    RPMManager(chroot, package).execute_post_trans()


def provision():
    load_opts()
    provisioner = Provisioner.create()
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
