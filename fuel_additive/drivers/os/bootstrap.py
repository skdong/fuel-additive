import os
import shutil

from oslo_config import cfg
from oslo_log import log as logging

from fuel_agent import errors
from fuel_agent.utils import build as bu
from fuel_agent.utils import utils

from fuel_additive.drivers.os.image import Ubuntu

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class Bootstrap(Ubuntu):
    def __init__(self, chroot, container_dir, config):
        self.container_dir = container_dir
        super(Bootstrap,self).__init__(chroot, config)

    @classmethod
    def create(cls, config):
        chroot = bu.mkdtemp_smart(CONF.image_build_dir,
                                  CONF.image_build_suffix)
        container_dir = bu.mkdtemp_smart(
            CONF.image_build_dir,
            CONF.image_build_suffix + '_container')

        return cls(chroot, container_dir, config)

    @property
    def bs_scheme(self):
        return self.config.bootstrap_scheme

    @property
    def os_config(self):
        return self.config.operating_system

    def handle_certs(self):
        if hasattr(self.bs_scheme, 'certs') and self.bs_scheme.certs:
            bu.copy_update_certs(self.bs_scheme.certs, self.chroot)

    def handle_extra_files(self):
        if hasattr(self.bs_scheme, 'extra_files') and self.bs_scheme.extra_files:
            for extra in self.bs_scheme.extra_files:
                bu.rsync_inject(extra, self.chroot)

    def handle_ssh_file(self):
        if (hasattr(self.bs_scheme, 'root_ssh_authorized_file') and
                self.bs_scheme.root_ssh_authorized_file):
            LOG.debug('Put ssh auth file %s',
                        self.bs_scheme.root_ssh_authorized_file)
            auth_file = os.path.join(self.chroot, 'root/.ssh/authorized_keys')
            utils.makedirs_if_not_exists(os.path.dirname(
            auth_file), mode=0o700)
            shutil.copy(
                self.bs_scheme.root_ssh_authorized_file,
                auth_file)
            os.chmod(auth_file, 0o700)

    def handle_post_srcipt(self):
        if (hasattr(self.bs_scheme, 'post_script_file') and
                self.bs_scheme.post_script_file):
            bu.run_script_in_chroot(
                self.chroot, self.bs_scheme.post_script_file)

    def save_runtime_uuid(self):
        bu.dump_runtime_uuid(self.bs_scheme.uuid,
                             os.path.join(self.chroot, 'etc/nailgun-agent/config.yaml'))

    def disable_hosts_resolve(self):
        bu.propagate_host_resolv_conf(self.chroot)

    def override_lvm_config(self):
        bu.override_lvm_config(
            self.chroot,
            {'devices': {
                'preferred_names': CONF.mpath_lvm_preferred_names}},
            lvm_conf_path=CONF.lvm_conf_path)

    def ubuntu_post_install(self):
        root = self.config.get_user_by_name('root')
        bu.do_post_inst(self.chroot,
                        hashed_root_password=root.hashed_password,
                        allow_unsigned_file=CONF.allow_unsigned_file,
                        force_ipv4_file=CONF.force_ipv4_file)

    @property
    def initrd(self):
        return filter(lambda x: x.name == 'initrd', self.bs_scheme.modules)[0]

    @property
    def rootfs(self):
        return filter(lambda x: x.name == 'rootfs', self.bs_scheme.modules)[0]

    def compress_initramfs(self):
        bu.recompress_initramfs(
            self.chroot,
            compress=self.initrd.compress_format)
        bu.copy_kernel_initramfs(self.chroot, self.container_dir, clean=True)

    def get_metadata(self):
        metadata = dict()
        metadata['os'] = self.os_config.to_dict()
        metadata['packages'] = self.os_config.packages
        for repo in self.os_config.repos:
            metadata.setdefault('repos', []).append({
                'type': 'deb',
                'name': repo.name,
                'uri': repo.uri,
                'suite': repo.suite,
                'section': repo.section,
                'priority': repo.priority,
                'meta': repo.meta})
        metadata['all_packages'] = bu.get_installed_packages(self.chroot)
        return metadata

    def mksquashfs(self):
        bu.run_mksquashfs(
            self.chroot, os.path.join(self.container_dir,
                                      os.path.basename(self.rootfs.uri)),
            self.rootfs.compress_format)

    def post_install_os(self):
        LOG.debug('Post-install OS configuration')
        self.disable_hosts_resolve()
        self.handle_certs()
        self.handle_extra_files()
        self.handle_ssh_file()
        # Allow user to drop and run script inside chroot:
        self.handle_post_srcipt()
        # Save runtime_uuid into bootstrap
        self.save_runtime_uuid()
        self.override_lvm_config()

    def clean(self):
        LOG.info('Cleanup chroot')
        super(Bootstrap, self).clean()
        try:
            shutil.rmtree(self.container_dir)
        except OSError:
            LOG.debug('Finally: directory %s seems does not exist '
                      'or can not be removed', self.container_dir)

    def compress_bootstrap(self):
        self.compress_initramfs()
        self.stop_chroot_processes()
        self.mksquashfs()
        output = bu.save_bs_container(self.config.output, self.container_dir,
                                      self.bs_scheme.container.format)
        LOG.info('--- Building bootstrap image END (do_mkbootstrap) ---')
        return output

    def build(self):
        try:
            return self._build()
        except errors.ProcessExecutionError as err:
            LOG.erro(err)
        finally:
            self.clean()

    def _build(self):
        # TODO make work space
        self.make_work_space()
        # TODO setup work space
        self.setup_work_space()
        # TODO install base os
        self.install_base_os()
        # TODO post install base os
        self.post_install_os()
        # TODO compress bootstrap
        output = self.compress_bootstrap()
        return output