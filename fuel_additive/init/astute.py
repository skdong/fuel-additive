import yaml


def get_settings():
    with open("/etc/fuel/astute.yaml") as fp:
        settings = yaml.load(fp)
        return settings


SETTINGS = get_settings()
