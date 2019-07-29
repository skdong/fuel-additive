class Resource(object):
    def __init__(self, resource):
        self._resource = resource

    def __getattr__(self, item):
        return getattr(self._resource, item)
