import os

from oslo_log import log as logging
from fuel_agent.errors import ProcessExecutionError

from fuel_additive import contants

LOG = logging.getLogger(__name__)


class Init(object):
    name = "init"
    path = os.path.join(contants.RUN_PATH, name)
    stages = []

    def __init__(self, force=False):
        self.force = force
        self._init()

    def _init(self):
        if not os.path.isdir(self.path):
            os.makedirs(self.path)

    def _clean(self):
        os.removedirs(self.path)

    def reset_run_state(self):
        self._clean()
        self._init()

    def stage_path(self, stage):
        return os.path.join(self.path, stage+".over")

    def set_stage_over(self, stage):
        with open(self.stage_is_over(stage), "w") as fp:
            fp.write("yes")
        LOG.debug("stage %s is over", stage)

    def stage_is_over(self, stage):
        return os.path.isfile(self.stage_path(stage))

    def run_stage(self, stage, force=False):
        if self.stage_is_over(stage) and not force:
            try:
                getattr(self, stage)()
                self.set_stage_over(stage)
            except ProcessExecutionError as err:
                LOG.warn(err)
                raise
        else:
            LOG.debug("stage %s is alread over", stage)