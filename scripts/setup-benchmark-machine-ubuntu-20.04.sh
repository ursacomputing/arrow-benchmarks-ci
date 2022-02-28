#!/bin/bash

apt-get upgrade

echo "-------Installing C++ dependencies"
apt-get update -y -q && \
apt-get install -y -q --no-install-recommends \
    autoconf \
    ca-certificates \
    ccache \
    cmake \
    curl \
    g++ \
    gcc \
    gdb \
    git \
    libbenchmark-dev \
    libboost-filesystem-dev \
    libboost-regex-dev \
    libboost-system-dev \
    libbrotli-dev \
    libbz2-dev \
    libgflags-dev \
    libcurl4-openssl-dev \
    libgoogle-glog-dev \
    liblz4-dev \
    libprotobuf-dev \
    libprotoc-dev \
    libre2-dev \
    libsnappy-dev \
    libssl-dev \
    libthrift-dev \
    libutf8proc-dev \
    libzstd-dev \
    make \
    ninja-build \
    pkg-config \
    protobuf-compiler \
    rapidjson-dev \
    tzdata \
    wget && \
apt-get clean && \
rm -rf /var/lib/apt/lists*

echo "-------Installing Python dependencies"
apt-get update -y -q && \
apt-get install -y -q \
    python3 \
    python3-pip \
    python3-dev && \
apt-get clean && \
rm -rf /var/lib/apt/lists/*

echo "-------Installing R dependencies"
apt-get update -y -q && \
apt-get install -y -q --no-install-recommends r-base && \
apt-get clean && \
rm -rf /var/lib/apt/lists*

echo "-------Installing JavaScript dependencies"
apt-get update -y -q && \
wget -q -O - https://deb.nodesource.com/setup_14.x | bash - && \
apt-get install -y nodejs && \
apt-get clean && \
rm -rf /var/lib/apt/lists* && \
npm install -g yarn

echo "-------Installing Java dependencies"
apt-get update -y -q && \
apt-get install -y -q --no-install-recommends openjdk-8-jdk maven && \
apt-get clean && \
rm -rf /var/lib/apt/lists*
case $( uname -m ) in
  aarch64)
    java_alternative=java-1.8.0-openjdk-arm64;;
  *)
    java_alternative=java-1.8.0-openjdk-amd64;;
esac
update-java-alternatives -s $java_alternative

echo "-------Installing Buildkite Agent"
sh -c 'echo deb https://apt.buildkite.com/buildkite-agent stable main > /etc/apt/sources.list.d/buildkite-agent.list'
apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 32A37959C2FA5C3C99EFBC32A79206696452D198
apt-get update && sudo apt-get install -y buildkite-agent

echo "-------Setting up Buildkite agent config and hooks"
sed -i "s/xxx/$BUILDKITE_AGENT_TOKEN/g" /etc/buildkite-agent/buildkite-agent.cfg
echo "tags=\"queue=$BUILDKITE_QUEUE\"" >>/etc/buildkite-agent/buildkite-agent.cfg

touch /etc/buildkite-agent/hooks/environment
{
  echo "export ARROW_BCI_URL=$ARROW_BCI_URL"
  echo "export ARROW_BCI_API_ACCESS_TOKEN=$ARROW_BCI_API_ACCESS_TOKEN"
  echo "export CONBENCH_EMAIL=$CONBENCH_EMAIL"
  echo "export CONBENCH_PASSWORD=$CONBENCH_PASSWORD"
  echo "export CONBENCH_URL=$CONBENCH_URL"
  echo "export MACHINE=$MACHINE"
  echo "export GITHUB_PAT=$GITHUB_PAT"
} >> /etc/buildkite-agent/hooks/environment

cp /etc/buildkite-agent/hooks/pre-command.sample /etc/buildkite-agent/hooks/pre-command
echo "source /var/lib/buildkite-agent/.bashrc" >> /etc/buildkite-agent/hooks/pre-command

echo "-------Setting NOPASSWD for buildkite-agent user"
echo "buildkite-agent ALL=(ALL) NOPASSWD:ALL" | sudo tee -a /etc/sudoers
echo "Done"

echo "-------Installing conda"
case $( uname -m ) in
  aarch64)
    conda_installer=Miniconda3-latest-Linux-aarch64.sh;;
  *)
    conda_installer=Miniconda3-latest-Linux-x86_64.sh;;
esac
curl -LO https://repo.anaconda.com/miniconda/$conda_installer
bash $conda_installer -b -p "/var/lib/buildkite-agent/miniconda3"
su - buildkite-agent -c "/var/lib/buildkite-agent/miniconda3/bin/conda init bash"
