import six
import os
import signal

from io import open

from oslo_log import log as logging
from oslo_config import cfg

from fuel_agent import errors
from fuel_agent.utils import build as bu
from fuel_agent.utils import fs as fu
from fuel_agent.utils import utils as fuel_utils

from fuel_additive.drivers.os import build


LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class Image(object):
    def __init__(self, chroot, config):
        self.chroot = chroot
        self.config = config

    def stop_chroot_processes(self, force=False):
        if not bu.stop_chrooted_processes(self.chroot, signal=signal.SIGTERM):
            if not bu.stop_chrooted_processes(
                    self.chroot, signal=signal.SIGKILL):
                if not force:
                    raise errors.UnexpectedProcessError(
                        'Stopping chrooted processes failed. '
                        'There are some processes running in chroot %s',
                        self.chroot)

    def make_temp_space(self):
        LOG.info('*** Preparing image space ***')
        for image in self.config.image_scheme.images:
            LOG.debug('Creating temporary sparsed file for the '
                      'image: %s', image.uri)
            img_tmp_file = bu.create_sparse_tmp_file(
                dir=CONF.image_build_dir, suffix=CONF.image_build_suffix,
                size=CONF.sparse_file_size)
            LOG.debug('Temporary file: %s', img_tmp_file)

            # we need to remember those files
            # to be able to shrink them and move in the end
            image.img_tmp_file = img_tmp_file

            image.target_device.name = \
                bu.attach_file_to_free_loop_device(
                    img_tmp_file,
                    max_loop_devices_count=CONF.max_loop_devices_count,
                    loop_device_major_number=CONF.loop_device_major_number,
                    max_attempts=CONF.max_allowed_attempts_attach_image)

            # find fs with the same loop device object
            # as image.target_device
            fs = self.config.partition_scheme.fs_by_device(
                image.target_device)

            LOG.debug('Creating file system on the image')
            fu.make_fs(
                fs_type=fs.type,
                fs_options=fs.options,
                fs_label=fs.label,
                dev=six.text_type(fs.device))
            if fs.type == 'ext4':
                LOG.debug('Trying to disable journaling for ext4 '
                          'in order to speed up the build')
                utils.execute('tune2fs', '-O', '^has_journal',
                              six.text_type(fs.device))

    def mount_target(self, chroot, treat_mtab=True, pseudo=True):
        """Mount a set of file systems into a chroot

        :param chroot: Directory where to mount file systems
        :param treat_mtab: If mtab needs to be actualized (Default: True)
        :param pseudo: If pseudo file systems
        need to be mounted (Default: True)
        """
        LOG.debug('Mounting target file systems: %s', chroot)
        # Here we are going to mount all file systems in partition scheme.
        for fs in self.config.partition_scheme.fs_sorted_by_depth():
            mount = chroot + fs.mount
            fuel_utils.makedirs_if_not_exists(mount)
            fu.mount_fs(fs.type, str(fs.device), mount)

        if pseudo:
            for path in ('/sys', '/dev', '/proc'):
                fuel_utils.makedirs_if_not_exists(chroot + path)
                fu.mount_bind(chroot, path)

        if treat_mtab:
            mtab = fuel_utils.execute(
                'chroot', chroot, 'grep', '-v', 'rootfs', '/proc/mounts')[0]
            mtab_path = chroot + '/etc/mtab'
            if os.path.islink(mtab_path):
                os.remove(mtab_path)
            with open(mtab_path, 'wt', encoding='utf-8') as f:
                f.write(six.text_type(mtab))

    def make_work_space(self):
        self.make_temp_space()

    def setup_work_space(self):
        self.mount_target(treat_mtab=False, pseudo=False)
        bu.suppress_services_start(self.chroot)

    def umount_target(self, pseudo=True):
        LOG.debug('Umounting target file systems: %s', self.chroot)
        if pseudo:
            for path in ('/proc', '/dev', '/sys'):
                fu.umount_fs(self.chroot + path)
        for fs in self.config.partition_scheme.fs_sorted_by_depth(
                reverse=True):
            fu.umount_fs(self.chroot + fs.mount)

    def detach_images(self):
        LOG.debug('Finally: umounting chroot tree %s', self.chroot)

        for image in self.config.image_scheme.images:
            if image.target_device.name:
                LOG.debug('Finally: detaching loop device: %s',
                          image.target_device.name)
                try:
                    bu.deattach_loop(image.target_device.name)
                except errors.ProcessExecutionError as e:
                    LOG.warning('Error occured while trying to detach '
                                'loop device %s. Error message: %s',
                                image.target_device.name, e)
            if image.img_tmp_file:
                LOG.debug('Finally: removing temporary file: %s',
                          image.img_tmp_file)
                try:
                    os.unlink(image.img_tmp_file)
                except OSError:
                    LOG.debug('Finally: file %s seems does not exist '
                              'or can not be removed', image.img_tmp_file)

    def post_install(self):
        build.set_root_password(
            self.chroot, self.config.operating_system.get_user_by_name('root'))
        build.set_cloud_init(self.chroot)
        #  set puppet
        build.set_puppet(self.chroot)
        #  set mcollective
        build.set_mcollective(self.chroot)
        #  set selinux
        build.set_selinux(self.chroot)
        # set policy
        build.set_policy(self.chroot)
        # set grub2
        build.set_grub2(self.chroot)
        # set hosts
        build.set_hosts(self.chroot)

    def mount_proc(self):
        # we need /proc to be mounted for apt-get success
        LOG.debug('Preventing services from being get started')
        bu.suppress_services_start(self.chroot)
        fuel_utils.makedirs_if_not_exists(os.path.join(self.chroot, 'proc'))

        # we need /proc to be mounted for apt-get success
        fu.mount_bind(self.chroot, '/proc')
        bu.populate_basic_dev(self.chroot)

    def clean(self):
        self.stop_chroot_processes(force=True)
        self.umount_target()
        self.detach_images()
        try:
            os.rmdir(self.chroot)
        except OSError:
            LOG.debug('Finally: directory %s seems does not exist '
                      'or can not be removed', self.chroot)


class Ubuntu(Image):

    @property
    def proxies(self):
        return self.config.operating_system.proxies

    def install_base_os(self):
        build.install_base_ubuntu(self.chroot)
        self.set_update_apt()
        bu.suppress_services_start(self.chroot)
        self.mount_proc()

    def set_update_apt(self):
        LOG.debug('Configuring apt inside chroot')
        LOG.debug('Setting environment variables')
        bu.set_apt_get_env()
        LOG.debug('Allowing unauthenticated repos')
        bu.pre_apt_get(self.chroot,
                       allow_unsigned_file=CONF.allow_unsigned_file,
                       force_ipv4_file=CONF.force_ipv4_file,
                       proxies=self.proxies.proxies,
                       direct_repo_addr=self.proxies.direct_repo_addr_list)

    @classmethod
    def create(cls):
        return cls()
