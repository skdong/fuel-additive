import copy

import yaml

STEAM = {'apt_repo_host': '{{deploy_host}}',
         'apt_sources_url': 'http://{{apt_repo_host}}/repository',
         'certs_repo_host': '{{deploy_host}}',
         'certs_repo_url': 'http://{{certs_repo_host}}/repository/certs',
         'cluster_domain': 'domain.tld',
         'deploy_host': 'fuel.{{cluster_domain}}',
         'deploy_ip': '2.6.1.2',
         'docker_common_options': {'auth_password': '{{ docker_registry_password }}',
                                   'auth_registry': '{{ docker_registry }}',
                                   'auth_username': '{{ docker_registry_username }}',
                                   'environment': {'KOLLA_CONFIG_STRATEGY': '{{ config_strategy }}'},
                                   'restart_policy': '{{ docker_restart_policy }}',
                                   'restart_retries': '{{ docker_restart_policy_retry }}'},
         'docker_registry': '{{deploy_host}}',
         'docker_registry_password': 'admin123',
         'docker_registry_username': 'admin',
         'pip_repo_host': '{{deploy_host}}',
         'pip_repo_url': 'http://{{pip_repo_host}}/repository/pypi/simple',
         'python_pkg_install': ['ansible', 'docker'],
         'timezone': 'Asia/Shanghai',
         'yum_repo_host': '{{deploy_host}}',
         'yum_repo_url': 'http://{{yum_repo_host}}/repository/yum'}

KUBESPRAY = {'calico_cni_image_repo': '{{ deploy_host }}/calico/cni',
             'calico_cni_version': 'v3.4.0',
             'calico_ctl_version': 'v3.4.4',
             'calico_node_image_repo': '{{ deploy_host }}/calico/node',
             'calico_policy_image_repo': '{{ deploy_host }}/calico/kube-controllers',
             'calico_policy_version': 'v3.4.0',
             'calico_version': 'v3.4.0',
             'calicoctl_download_url': 'http://{{ deploy_host }}/repository/files/{{ kube_version }}/calicoctl-linux-{{ image_arch }}',
             'cluster_domain': 'domain.tld',
             'cluster_name': '{{ cluster_domain }}',
             'helm_stable_repo_url': 'http://{{ deploy_host }}/repository/helm',
             'cni_binary_checksum': 'f04339a21b8edf76d415e7f17b620e63b8f37a76b2f706671587ab6464411f2d',
             'cni_download_url': 'http://{{ deploy_host }}/repository/files/{{ kube_version }}/cni-plugins-{{ image_arch }}-{{ cni_version }}.tgz',
             'cni_version': 'v0.6.0',
             'coredns_image_repo': '{{ deploy_host }}/coredns/coredns',
             'coredns_version': '1.5.0',
             'dashboard_image_repo': '{{ deploy_host }}/google_containers/kubernetes-dashboard-{{ image_arch }}',
             'deploy_container_engine': False,
             'deploy_host': 'fuel.{{cluster_domain}}',
             'dns_mode': 'coredns',
             'dnsautoscaler_image_repo': '{{ deploy_host }}/k8s/cluster-proportional-autoscaler-{{ image_arch }}',
             'dnsautoscaler_version': '1.4.0',
             'etcd_deployment_type': 'docker',
             'etcd_image_repo': '{{ deploy_host }}/coreos/etcd',
             'etcd_version': 'v3.2.26',
             'helm_deployment_type': 'host',
             'helm_enabled': True,
             'helm_image_repo': '{{ deploy_host }}/k8s/k8s-helm',
             'hyperkube_download_url': 'http://{{ deploy_host }}/repository/files/{{ kube_version }}/hyperkube',
             'kube_image_repo': '{{ deploy_host }}/google-containers',
             'kube_network_plugin': 'calico',
             'kube_pods_subnet': '10.233.64.0/18',
             'kube_service_addresses': '10.233.0.0/18',
             'kube_version': 'v1.14.3',
             'kubeadm_download_url': 'http://{{ deploy_host }}/repository/files/{{ kube_version }}/kubeadm',
             'kubeadm_version': '{{ kube_version }}',
             'kubelet_deployment_type': 'host',
             'local_volume_provisioner_enabled': False,
             'nginx_image_repo': '{{ deploy_host }}/hub/nginx',
             'nodelocaldns_image_repo': '{{ deploy_host }}/k8s/k8s-dns-node-cache',
             'pod_infra_image_repo': '{{ deploy_host }}/google_containers/pause-{{ image_arch }}',
             'tiller_image_repo': '{{ deploy_host }}/k8s/tiller'}

INVENTORY = {'_meta': {'hostvars': {}},
             'all': {'children': ['kube-master', 'etcd', 'kube-node', 'k8s-cluster']},
             'etcd': {'hosts': []},
             'k8s-cluster': {'children': ['kube-master', 'kube-node']},
             'kube-master': {'hosts': []},
             'kube-node': {'hosts': []}}


def get_host_groups():
    provision = get_provision()
    inventory = copy.deepcopy(INVENTORY)
    nodes = provision['network_metadata']['nodes']
    user = provision['operator_user']['name']
    inventory['_meta']['hostvars'] = {
        name: {"ansible_host": node['network_roles']['admin/pxe'], "ansible_user": user, "ansible_become": "True"} for
        name, node in nodes.items()}
    inventory['kube-master']['hosts'] = [name for name, node in nodes.items() if "kube-master" in node['node_roles']]
    inventory['kube-node']['hosts'] = [name for name, node in nodes.items() if "kube-node" in node['node_roles']]
    inventory['etcd']['hosts'] = [name for name, node in nodes.items() if "etcd" in node['node_roles']]
    return inventory


def get_provision():
    with open('/tmp/provision.yaml') as fp:
        return yaml.load(fp)


def get_nailgun():
    with open('/etc/nailgun/settings.yaml') as fp:
        return yaml.load(fp)


def get_steam():
    steam = copy.deepcopy(STEAM)
    provision = get_provision()

    steam["deploy_ip"] = provision["master_ip"]
    return steam


def get_kubespray():
    kubespray = copy.deepcopy(KUBESPRAY)
    nailgun = get_nailgun()
    kubespray['cluster_name'] = nailgun["DNS_DOMAIN"]
    return kubespray
