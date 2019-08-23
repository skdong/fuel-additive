import yaml
from oslo_config import cfg
from oslo_log import log as logging

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

cli_opts = [
    cfg.StrOpt(name="playbook_path",
               default="ansible/kubespray/cluster.yml",
               help="transform playbook path")
]

CONF.register_cli_opts(cli_opts)

def get_plays():
    with open(CONF.playbook_path) as fp:
        return yaml.load(fp)

def trans_form_palys():
    plays = get_plays()

    for play in plays:

def practic():
    pass


def main():
    practic()


if __name__ == "__main__":
    main()