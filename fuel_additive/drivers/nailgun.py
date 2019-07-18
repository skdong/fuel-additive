import six
from oslo_config import cfg

from fuel_agent.drivers.nailgun import NailgunBuildImage
from fuel_agent import objects

from fuel_additive.objects.repo import create_repo

CONF = cfg.CONF


class NailgunBuildCentOSImage(NailgunBuildImage):

    def parse_operating_system(self):
        packages = self.data.get('packages', self.DEFAULT_TRUSTY_PACKAGES)

        repos = []
        for repo in self.data['repos']:
            repos.append(create_repo(repo))

        proxies = objects.RepoProxies()

        proxy_dict = self.data.get('proxies', {})
        for protocol, uri in six.iteritems(proxy_dict.get('protocols', {})):
            proxies.add_proxy(protocol, uri)
        proxies.add_direct_repo_addrs(proxy_dict.get(
            'direct_repo_addr_list', []))

        os = objects.Centos(repos=repos, packages=packages, major=7, minor=6,
                            proxies=proxies)

        # add root account
        root_password = self.data.get('root_password')
        hashed_root_password = self.data.get('hashed_root_password')

        # for backward compatibily set default password is no password provided
        if root_password is None and hashed_root_password is None:
            root_password = CONF.default_root_password

        os.add_user_account(
            name='root',
            password=root_password,
            homedir='/root',
            hashed_password=hashed_root_password,
        )
        return os
