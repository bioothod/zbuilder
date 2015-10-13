apt-get update && \
apt-get install -y curl tzdata lsb-release && \
cp -f /usr/share/zoneinfo/posix/W-SU /etc/localtime && \
curl http://repo.reverbrain.com/REVERBRAIN.GPG | apt-key add - && \
echo "deb http://repo.reverbrain.com/`lsb_release -cs`/ current/amd64/" > /etc/apt/sources.list.d/reverbrain.list && \
echo "deb http://repo.reverbrain.com/`lsb_release -cs`/ current/all/" >> /etc/apt/sources.list.d/reverbrain.list && \
apt-get update
