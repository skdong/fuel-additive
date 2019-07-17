# this scritp to build image for centos os install on host
# need run on fuel master because need fuel package
MODULE=$(dirname $(readlink -f $0))
docker build --network host -t sinovast/centos_image_template:latest  $MODULE
