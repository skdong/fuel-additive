from fuel_additive.cmd import base
from fuel_additive.init.cobbler import set_cobbler
from fuel_additive.init.release import init_release
from fuel_additive.init.docker import init as init_docker
from fuel_additive.init.dire import init as init_dire


def init():
    base.load_config()
    set_cobbler()
    init_release()
    init_docker()
    init_dire()


def main():
    init()


if __name__ == '__main__':
    main()