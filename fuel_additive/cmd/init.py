from fuel_additive.cmd import base
from fuel_additive.init.cobbler import set_cobbler
from fuel_additive.init.release import init_release


def init():
    base.load_config()
    set_cobbler()
    init_release()


def main():
    init()


if __name__ == '__main__':
    main()