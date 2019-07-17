import os
import yaml

from fuel_agent.utils import build as bu
from fuel_agent.utils import utils


def install_base_centos(target):
    cmd = ["docker", "cp", CONF.centos_docker_container + ":/", target]
    utils.execute(*cmd)


def set_root_password(chroot, root):
    # NOTE(agordeev): set up password for root
    password = root.set_root_password
    utils.execute('sed', '-i',
                  's%root:[\*,\!]%root:' + password + '%',
                  os.path.join(chroot, 'etc/shadow'))

def set_puppet(chroot):
    # TODO(agordeev): take care of puppet service for other distros, once
    # fuel-agent will be capable of building images for them too.
    if os.path.exists(os.path.join(chroot, 'etc/init.d/puppet')):
        utils.execute('chroot', chroot, 'update-rc.d', 'puppet', 'disable')
    # NOTE(agordeev): disable mcollective to be automatically started on boot
    # to prevent confusing messages in its log (regarding connection errors).

def set_mcollective(chroot):
    service_link = os.path.join(
        chroot,
        'etc/systemd/system/multi-user.target.wants/mcollective.service')
    if os.path.exists(service_link):
        os.unlink(service_link)

def set_cloud_init(chroot)
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

def set_policy(chroot):
    # NOTE(agordeev): remove custom policy-rc.d which is needed to disable
    # execution of post/pre-install package hooks and start of services
    bu.remove_files(chroot, ['usr/sbin/policy-rc.d'])

def set_grub2(chroot):
    # enable mdadm (remove nomdadmddf nomdadmism options from cmdline)
    bu.remove_files(chroot, [bu.GRUB2_DMRAID_SETTINGS])

def set_selinux(chroot):
    # disable selinux
    with open(os.path.join(chroot, 'etc/selinux/config')) as cf:
        context = cf.read()
    context = context.replace('SELINUX=enforcing','SELINUX=permissive')
    with open(os.path.join(chroot, 'etc/selinux/config'), 'w') as cf:
        cf.write(context)


class RPMRepo(repo.Repo):
    template = u"[{name}]\nname={name}\nbaseurl={uri}\ngpgcheck={gpgcheck}"
    repo_path = u"etc/yum.repos.d/"
    def __init__(self, repo):
        super(RPMRepo, self).__init__(repo.get('name'),
                                      repo.get('uri'),
                                      repo.get('priority'))
        self.gpgcheck = '1' if repo.get("gpgcheck") else '0'
        self.type = repo.get('type')
    
    def inject_to_os(self, root='/'):

        path = os.path.join(root, repo_path, name+'repo')
        with open(path, 'w') as fp:
            fp.write(self.get_repo_raw())
    
    def get_repo_raw(self):
        return self.template.format(name=self.name,
        uri=self.uri, gpgcheck=self.gpgcheck)


def repo_factor(repo):
    repo_mapper = {"rpm": RPMRepo,
                   "deb": repo.DEBRepo}
    if repo.get('type') in repo_mapper:
        return repo_mapper.get(repo.get('type'))(repo)
    else
        raise ReopTypeError("type is %s not int mapper %s "%(
                            repo.get('type'), repo_mapper.keys()))


def set_repos(chroot, repos):
    for repo_raw in repos:
        repo = repo_factor(repo_raw)
        repo.inject_to_os(root)
