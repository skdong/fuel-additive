from fuel_additive.cmd import base
from fuel_additive.init.cobbler import set_cobbler


def init():
    base.load_config()
    set_cobbler()


def main():
    init()


if __name__ == '__main__':
    main()