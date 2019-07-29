import os

from fuel_additive.os.resource import Resource


class DEBRepo(Resource):
    pass


class RPMRepo(Resource):
    template = u"[{name}]\nname={name}\nbaseurl={uri}\ngpgcheck={gpgcheck}"
    repos_path = u"etc/yum.repos.d/"
    suffix = ".repo"

    @property
    def repo_path(self):
        return os.path.join(self.repos_path, self.name+self.suffix)

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
