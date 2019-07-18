from fuel_agent.objects import repo
from fuel_additive.errors import ReopTypeError


def create_repo(repo):
    repo_mapper = {"rpm": RPMRepo,
                   "deb": DEBRepo}
    if repo.get('type') in repo_mapper:
        return repo_mapper.get(repo.get('type'))(repo)
    else:
        raise ReopTypeError("type is %s not int mapper %s " % (
            repo.get('type'), repo_mapper.keys()))


class RPMRepo(repo.Repo):
    def __init__(self, repo):
        super(RPMRepo, self).__init__(repo.get('name'),
                                      repo.get('uri'),
                                      repo.get('priority'))
        self.gpgcheck = '1' if repo.get("gpgcheck") else '0'


class DEBRepo(repo.DEBRepo):
    def __init__(self, repo):
        super(DEBRepo, self).__init__(
            name=repo['name'],
            uri=repo['uri'],
            suite=repo['suite'],
            section=repo['section'],
            priority=repo['priority'])
