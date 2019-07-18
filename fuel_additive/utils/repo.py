import os

from fuel_additive.objects import repo
from fuel_additive.errors import ReopTypeError


def create_repo(repo):
    repo_mapper = {"rpm": RPMRepo,
                   "deb": DEBRepo}
    if repo.get('type') in repo_mapper:
        return repo_mapper.get(repo.get('type'))(repo)
    else:
        raise ReopTypeError("type is %s not int mapper %s " % (
            repo.get('type'), repo_mapper.keys()))


class DEBRepo(repo.DEBRepo):
    pass


class RPMRepo(repo.RPMRepo):
    template = u"[{name}]\nname={name}\nbaseurl={uri}\ngpgcheck={gpgcheck}"
    repos_path = u"etc/yum.repos.d/"
    suffix = ".repo"

    def __init__(self, repo):
        super(RPMRepo, self).__init__(repo.get('name'),
                                      repo.get('uri'),
                                      repo.get('priority'))
        self.gpgcheck = '1' if repo.get("gpgcheck") else '0'
        self.type = repo.get('type')

    @property
    def repo_path(self):
        return os.path.join(self.repos_path, self.name, self.suffix)

    def inject_to_os(self, root='/'):
        path = os.path.join(root, self.repo_path)
        with open(path, 'w') as fp:
            fp.write(self.get_repo_raw())

    def get_repo_raw(self):
        """
        :rtype: basestring
        """
        return self.template.format(name=self.name,
                                    uri=self.uri, gpgcheck=self.gpgcheck)
