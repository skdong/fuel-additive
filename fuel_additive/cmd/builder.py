import os
import signal
import sys
import shutil
import six
import yaml
import json

from oslo_config import cfg
from oslo_log import log as logging

from fuel_agent import manager as manager

from fuel_agent import errors
from fuel_agent.utils import build as bu
from fuel_agent.utils import fs as fu
from fuel_agent.utils import utils


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


opts = [
    cfg.StrOpt(
        "centos_docker_container",
        default="os-image",
        help="Centos Base Os Dcoker Container"
    )
]

CONF = cfg.CONF
LOG = logging.getLogger(__name__)
PROJECT = 'fuel-agent'


def list_opts():
    return [("CLI", cli_opts)]


def install_base_centos(target):
    cmd = ["docker", "cp", CONF.centos_docker_container,
           "/", target]
    utils.execute(*cmd)


def do_post_inst(chroot, hashed_root_password):
    # NOTE(agordeev): set up password for root
    utils.execute('sed', '-i',
                  's%root:[\*,\!]%root:' + hashed_root_password + '%',
                  os.path.join(chroot, 'etc/shadow'))
    # NOTE(agordeev): backport from bash-script:
    # in order to prevent the later puppet workflow outage, puppet service
    # should be disabled on a node startup.
    # Being enabled by default, sometimes it leads to puppet service hanging
    # and recognizing the deployment as failed.
    # TODO(agordeev): take care of puppet service for other distros, once
    # fuel-agent will be capable of building images for them too.
    if os.path.exists(os.path.join(chroot, 'etc/init.d/puppet')):
        utils.execute('chroot', chroot, 'update-rc.d', 'puppet', 'disable')
    # NOTE(agordeev): disable mcollective to be automatically started on boot
    # to prevent confusing messages in its log (regarding connection errors).
    with open(os.path.join(chroot, 'etc/init/mcollective.override'), 'w') as f:
        f.write("manual\n")
    service_link = os.path.join(
        chroot,
        'etc/systemd/system/multi-user.target.wants/mcollective.service')
    if os.path.exists(service_link):
        os.unlink(service_link)
    cloud_cfg = os.path.join(chroot, 'etc/cloud/cloud.cfg.d/')
    utils.makedirs_if_not_exists(os.path.dirname(cloud_cfg))
    with open(os.path.join(
            chroot,
            'etc/cloud/cloud.cfg.d/99-disable-network-config.cfg'), 'w') as cf:
        yaml.safe_dump({'network': {'config': 'disabled'}}, cf,
                       encoding='utf-8',
                       default_flow_style=False)
    cloud_init_conf = os.path.join(chroot, 'etc/cloud/cloud.cfg')
    if os.path.exists(cloud_init_conf):
        bu.fix_cloud_init_config(cloud_init_conf)
    # NOTE(agordeev): remove custom policy-rc.d which is needed to disable
    # execution of post/pre-install package hooks and start of services
    bu.remove_files(chroot, ['usr/sbin/policy-rc.d'])
    # enable mdadm (remove nomdadmddf nomdadmism options from cmdline)
    bu.remove_files(chroot, [bu.GRUB2_DMRAID_SETTINGS])
    utils.execute('chroot', chroot, 'yum', 'clean', 'all')



class Builder(object):
    def __init__(self, manager):
        super(Builder, self)
        self.manager = manager

    def make_temp_space(self, chroot):
        """Bootstrap a basic Linux system

        :param chroot directory where the installed OS can be found
        For now only Ubuntu is supported.
        Note: the data gets written to a different location (a set of
        ext4 images  located in the image_build_dir directory)
        Includes the following steps
        1) create temporary sparse files for all images (truncate)
        2) attach temporary files to loop devices (losetup)
        3) create file systems on these loop devices
        4) create temporary chroot directory
        5) mount loop devices into chroot directory
        """
        LOG.info('*** Preparing image space ***')
        for image in self.driver.image_scheme.images:
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
            fs = self.driver.partition_scheme.fs_by_device(
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

        # mounting all images into chroot tree
        self.manager.mount_target(chroot, treat_mtab=False, pseudo=False)
        LOG.info('Installing BASE operating system into image')
        # FIXME(kozhukalov): !!! we need this part to be OS agnostic

        # DEBOOTSTRAP
        # we need /proc to be mounted for apt-get success
        LOG.debug('Preventing services from being get started')
        bu.suppress_services_start(chroot)
        utils.makedirs_if_not_exists(os.path.join(chroot, 'proc'))

        # we need /proc to be mounted for apt-get success
        fu.mount_bind(chroot, '/proc')
        bu.populate_basic_dev(chroot)

    @property
    def driver(self):
        return self.manager.driver

    def build(self):
        global chroot
        LOG.info('--- Building image (do_build_image) ---')
        driver_os = self.driver.operating_system
        # as a pluggable data driver to avoid any fixed format.
        metadata = {}

        metadata['os'] = driver_os.to_dict()

        # we need to compare list of packages and repos
        LOG.info('*** Checking if image exists ***')
        if all([os.path.exists(img.uri.split('file://', 1)[1])
                for img in self.driver.image_scheme.images]):
            LOG.debug('All necessary images are available. '
                      'Nothing needs to be done.')
            return
        LOG.debug('At least one of the necessary images is unavailable. '
                  'Starting build process.')
        try:
            chroot = bu.mkdtemp_smart(
                CONF.image_build_dir, CONF.image_build_suffix)
            # TODO make tempspace
            self.make_temp_space(chroot)
            # TODO install centos base os
            install_base_centos(chroot)
            packages = driver_os.packages
            metadata['packages'] = packages

            # TODO generate centos repos

            # TODO install centos packages

            LOG.debug('Post-install OS configuration')
            root = driver_os.get_user_by_name('root')

            # TODO centos psot install
            do_post_inst(chroot, hashed_root_password=root.hashed_password)

            LOG.debug('Making sure there are no running processes '
                      'inside chroot before trying to umount chroot')
            if not bu.stop_chrooted_processes(chroot, signal=signal.SIGTERM):
                if not bu.stop_chrooted_processes(
                        chroot, signal=signal.SIGKILL):
                    raise errors.UnexpectedProcessError(
                        'Stopping chrooted processes failed. '
                        'There are some processes running in chroot %s',
                        chroot)

            LOG.info('*** Finalizing image space ***')
            fu.umount_fs(os.path.join(chroot, 'proc'))
            # umounting all loop devices
            self.manager.umount_target(chroot, pseudo=False)

            for image in self.driver.image_scheme.images:
                # find fs with the same loop device object
                # as image.target_device
                fs = self.driver.partition_scheme.fs_by_device(
                    image.target_device)

                if fs.type == 'ext4':
                    LOG.debug('Trying to re-enable journaling for ext4')
                    utils.execute('tune2fs', '-O', 'has_journal',
                                  str(fs.device))

                if image.target_device.name:
                    LOG.debug('Finally: detaching loop device: {0}'.format(
                        image.target_device.name))
                    try:
                        bu.deattach_loop(image.target_device.name)
                    except errors.ProcessExecutionError as e:
                        LOG.warning('Error occured while trying to detach '
                                    'loop device {0}. Error message: {1}'.
                                    format(image.target_device.name, e))

                LOG.debug('Shrinking temporary image file: %s',
                          image.img_tmp_file)
                bu.shrink_sparse_file(image.img_tmp_file)

                raw_size = os.path.getsize(image.img_tmp_file)
                raw_md5 = utils.calculate_md5(image.img_tmp_file, raw_size)

                LOG.debug('Containerizing temporary image file: %s',
                          image.img_tmp_file)
                img_tmp_containerized = bu.containerize(
                    image.img_tmp_file, image.container,
                    chunk_size=CONF.data_chunk_size)
                img_containerized = image.uri.split('file://', 1)[1]

                # NOTE(kozhukalov): implement abstract publisher
                LOG.debug('Moving image file to the final location: %s',
                          img_containerized)
                shutil.move(img_tmp_containerized, img_containerized)

                container_size = os.path.getsize(img_containerized)
                container_md5 = utils.calculate_md5(
                    img_containerized, container_size)

                metadata.setdefault('images', []).append({
                    'raw_md5': raw_md5,
                    'raw_size': raw_size,
                    'raw_name': None,
                    'container_name': os.path.basename(img_containerized),
                    'container_md5': container_md5,
                    'container_size': container_size,
                    'container': image.container,
                    'format': image.format})

            # NOTE(kozhukalov): implement abstract publisher
            LOG.debug('Image metadata: %s', metadata)
            with open(self.driver.metadata_uri.split('file://', 1)[1], ) as f:
                yaml.safe_dump(metadata, stream=f)
            LOG.info('--- Building image END (do_build_image) ---')
        except Exception as exc:
            LOG.error('Failed to build image: %s', exc)
            raise
        finally:
            LOG.info('Cleanup chroot')
            self.manager.destroy_chroot(chroot)

    @classmethod
    def factory(cls):
        with open(CONF.input_data_file) as fp:
            data = json.load(fp)
        return cls(manager.Manager(data))


def over_ride_opts():
    CONF.data_driver = 'nailgun_build_image'


def build():
    load_opts()
    over_ride_opts()
    builder = Builder.factory()
    builder.build()


def load_opts():
    logging.register_options(CONF)
    CONF.register_cli_opts(cli_opts)
    CONF.register_opts(opts)
    CONF(sys.argv[1:], project=PROJECT)
    logging.setup(CONF, PROJECT)


def preview():
    load_opts()
    print CONF.data_driver
    CONF.data_driver = 'nailgun_build_image'
    print CONF.data_driver


def main():
    preview()


if __name__ == "__main__":
    main()
