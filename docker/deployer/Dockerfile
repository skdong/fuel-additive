FROM centos:latest
RUN rm -f /etc/yum.repos.d/*
ADD ./config/* /tmp/config/
RUN mv /tmp/config/CentOS-Base.repo /etc/yum.repos.d/ ; \
    mv /tmp/config/Docker.repo /etc/yum.repos.d/ ; \
    mv /tmp/config/Epel.repo /etc/yum.repos.d/ 

RUN yum update -y && yum install -y $(cat /tmp/config/packages)
