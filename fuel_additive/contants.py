PROJECT = u"fuel_additive"

RUN_PATH = u"/var/fuel/additive"

DOCKER_SERVICE = u"""
[Unit]
Description=Docker Application Container Engine
Documentation=http://docs.docker.com
After=network.target

[Service]
Type=notify
NotifyAccess=main
Environment=GOTRACEBACK=crash
Environment=DOCKER_HTTP_HOST_COMPAT=1
Environment=PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin
ExecStart=/usr/local/sbin/dockerd
ExecReload=/bin/kill -s HUP $MAINPID
LimitNOFILE=1048576
LimitNPROC=1048576
LimitCORE=infinity
TimeoutStartSec=0
Restart=on-abnormal
KillMode=process

[Install]
WantedBy=multi-user.target

"""


DIRE_BOOTRC="""
export HOST='{ip}'
export DOMAIN='{domain}'
export HOST_NAME='{hostname}'
export KEYSTORE_PASS='nexus3'
"""