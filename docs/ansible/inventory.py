#!/usr/bin/env python
import yaml
import sys
import json

inventory = {"all": 
                {"hosts":{},
                 "children":{
                     "kube-master":{},
                     "etcd": {},
                     "kube-node":{},
                     "k8s-cluster":{
                        "children": {
                             "kube-node":{},
                             "kube-master":{}
                            }
                        },
                    }
                }
            }

with open('/tmp/provision.yaml') as fp:
    provision = yaml.load(fp)


nodes = provision['network_metadata']['nodes']
user = provision['operator_user']['name']
inventory['all']['hosts'] = { name: {"ansible_host": node['network_roles']['admin/pxe'], "ansible_user": user, "ansible_become":"True"} for name, node in nodes.items()}
inventory['all']['children']['kube-master']['hosts'] = { name: {} for name, node in nodes.items() if "kube-master" in node['node_roles'] }
inventory['all']['children']['kube-node']['hosts'] = { name: {} for name, node in nodes.items() if "kube-node" in node['node_roles'] }
inventory['all']['children']['etcd']['hosts'] = { name: {} for name, node in nodes.items() if "etcd" in node['node_roles'] }

json.dump(inventory, sys.stdout, indent=4)
