from oslo_config import cfg
from fuel_additive.init.httpd import restart_httpd

CONF = cfg.CONF

cli_opts = [
    cfg.StrOpt(
        'cobbler_http_port',
        default='9080',
        help='cobbler http port'
    ),
    cfg.StrOpt(
        'cobbler_https_port',
        default='9443',
        help='cobbler https port'
    ),
]


CONF.register_cli_opts(cli_opts)


def set_cobbler():
    _set_http_conf()
    _set_https_conf()
    _set_http_port()
    restart_httpd()
    _set_cobbler_settings()


def _set_http_port():
    conf_path = u"/etc/httpd/conf.ports.d/cobbler.conf"
    with open(conf_path) as fp:
        config_info = fp.read()
    config_info = config_info.replace("Listen 80", "Listen "+CONF.cobbler_http_port)
    config_info = config_info.replace("Listen 443", "Listen "+CONF.cobbler_https_port)
    with open(conf_path, "w") as fp:
        fp.write(config_info)


def _set_http_conf():
    conf_path = u"/etc/httpd/conf.d/25-cobbler_non-ssl.conf"
    with open(conf_path) as fp:
        config_info = fp.read()
    config_info = config_info.replace("<VirtualHost *:80", "<VirtualHost *" + CONF.cobbler_http_port)
    with open(conf_path, "w") as fp:
        fp.write(config_info)


def _set_https_conf():
    conf_path = u"/etc/httpd/conf.d/25-cobbler_ssl.conf"
    with open(conf_path) as fp:
        config_info = fp.read()
    config_info = config_info.replace("<VirtualHost *:443", "<VirtualHost *" + CONF.cobbler_https_port)
    with open(conf_path, "w") as fp:
        fp.write(config_info)


def _set_cobbler_settings():
    """for cobbler cli config"""
    config_info = u"/etc/cobbler/setttings"
    with open(config_info) as fp:
        config_info = fp.read()
    config_info = config_info.replace("http_port: 80", "http_port: "+CONF.cobbler_http_port)
    with open(config_info, 'w') as fp:
        fp.write(config_info)

