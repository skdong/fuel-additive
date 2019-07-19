from fuel_agent.utils import utils


def restart_httpd():
    utils.execute("systemctl restart httpd")