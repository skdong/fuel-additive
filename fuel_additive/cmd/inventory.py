import argparse

import yaml
import sys

from fuel_additive.utils.inventory import get_host_groups
from fuel_additive.utils.inventory import get_steam
from fuel_additive.utils.inventory import get_kubespray


def parse_args():
    parser = argparse.ArgumentParser(description='OpenStack Inventory Module')
    parser.add_argument('--list', action='store_true',
                        help='List active servers')
    parser.add_argument('--host', help='List details about the specific host')

    return parser.parse_args()


def get_host_var(inventory, host):
    host_vars = inventory["_meta"]["hostvars"][host]
    all_vars = inventory["all"]["vars"]
    return host_vars.update(all_vars)


def steam_inventory():
    args = parse_args()
    inventory = get_host_groups()
    all_vars = get_steam()
    inventory["all"]["vars"] = all_vars
    if args.list:
        yaml.safe_dump(inventory, sys.stdout)
    elif args.host:
        yaml.safe_dump(get_host_var(inventory, args.host),
                       sys.stdout)
    sys.exit(0)


def kubespray_inventory():
    args = parse_args()
    inventory = get_host_groups()
    all_vars = get_kubespray()
    inventory["all"]["vars"] = all_vars
    if args.list:
        yaml.safe_dump(inventory, sys.stdout)
    elif args.host:
        yaml.safe_dump(get_host_var(inventory, args.host),
                       sys.stdout)
    sys.exit(0)
