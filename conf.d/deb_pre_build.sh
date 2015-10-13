sed -i -e 's/httpredir.debian.org/mirror.yandex.ru/g' /etc/apt/sources.list
apt-get update && \
apt-get install -y git devscripts sudo
