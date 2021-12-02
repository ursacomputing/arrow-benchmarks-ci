## How to Add New Benchmark Machine

##### 1. Create Pull Request to add your machine to `Config.MACHINES`
Adding new machine to `Config.MACHINES` and merging your pull request into `main` branch will automatically
- create **"Arrow BCI Benchmark on ..."** Buildkite pipeline for your machine in 
[Apache Arrow CI Buildkite organization](https://buildkite.com/apache-arrow)
- enable **"Arrow BCI Benchmark on ..."** Buildkite pipeline builds being created for all 
[Apache Arrow repo](https://github.com/apache/arrow) master commits and `@ursabot` benchmark requests on pull requests.

Add your benchmark machine to `MACHINES` in [config.py](../config.py) and set `publish_benchmark_results` to `False` so
benchmark results for your machine are not published to [Apache Arrow repo](https://github.com/apache/arrow) pull requests
until you are ready to do so.
```python
MACHINES = {
    "your-benchmark-machine": {
        "info": "Supported langs: Python",
        "default_filters": {
            "arrow-commit": {"lang": "Python"},
        },
        "supported_filters": ["name", "lang"],
        "supported_langs": ["Python"],
        "offline_warning_enabled": False,
        "publish_benchmark_results": False,
    },
}
```

##### 2. Get environment vars for Buildkite Agent your benchmark machine
- Add a comment to your Pull Request
```
@ElenaHenderson Will you please provide environment vars for Buildkite Agent for our benchmark machine 
with name = your-benchmark-machine:
- ARROW_BCI_URL
- ARROW_BCI_API_ACCESS_TOKEN
- BUILDKITE_AGENT_TOKEN
- BUILDKITE_QUEUE
- CONBENCH_EMAIL
- CONBENCH_PASSWORD
- CONBENCH_URL
- MACHINE
```
- Please also let us know how you would like environment vars to be shared with you.

##### 3. Setup your benchmark machine
Note:
- [setup-benchmark-machine-ubuntu-20.04.sh](../scripts/setup-benchmark-machine-ubuntu-20.04.sh) only installs dependencies for Apache Arrow C++, Python, R, Java and JavaScript.
- If you need to install additional dependencies, please update [setup-benchmark-machine-ubuntu-20.04.sh](../scripts/setup-benchmark-machine-ubuntu-20.04.sh). 
- If your machine is running OS other than Ubuntu, please create a new setup script and use [setup-benchmark-machine-ubuntu-20.04.sh](../scripts/setup-benchmark-machine-ubuntu-20.04.sh) as a reference.

```shell script
sudo su

# Export env vars to be used by setup-benchmark-machine-ubuntu-20.04.sh
export ARROW_BCI_URL=<ARROW_BCI_URL>
export ARROW_BCI_API_ACCESS_TOKEN=<ARROW_BCI_API_ACCESS_TOKEN>
export BUILDKITE_AGENT_TOKEN=<BUILDKITE_AGENT_TOKEN>
export BUILDKITE_QUEUE=<BUILDKITE_QUEUE>
export CONBENCH_EMAIL=<CONBENCH_EMAIL>
export CONBENCH_PASSWORD=<CONBENCH_PASSWORD>
export CONBENCH_URL=<CONBENCH_URL>
export MACHINE=<MACHINE>

# Install Apache Arrow C++, Python, R, Java and JavaScript dependencies and Buildkite Agent
curl -LO https://raw.githubusercontent.com/ursacomputing/arrow-benchmarks-ci/main/scripts/setup-benchmark-machine-ubuntu-20.04.sh
chmod +x setup-benchmark-machine-ubuntu-20.04.sh
source ./setup-benchmark-machine-ubuntu-20.04.sh

# Verify you have at least these versions of java, javac, mvn, node and yarn
$ java -version
openjdk version "1.8.0_292"
$ javac -version
javac 1.8.0_292
$ mvn -version
Apache Maven 3.6.3
$ node --version
v14.18.2
$ yarn --version
1.22.17

# Install Conda for buildkite-agent user
su - buildkite-agent
curl -LO https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p "$HOME/miniconda3"
bash 
"$HOME/miniconda3/bin/conda" init
exit
exit

# Verify Conda is installed for buildkite-agent user
su - buildkite-agent
bash
conda --version
conda env list
exit
exit

# Start Buildkite Agent
systemctl enable buildkite-agent && systemctl start buildkite-agent

# Verify Buildkite Agent is running
ps aux | grep buildkite
journalctl -f -u buildkite-agent
```

##### 4. Test benchmark build on your machine
TODO

##### 5. Disable Swap, Boost, CPU frequency scaling and Hyper-Threading on your machine
TODO

##### 6. Get Pull Request reviewed and merged
Suggested Reviewers: 
- [Elena Henderson](https://github.com/elenahenderson)
- [Jonathan Keane](https://github.com/jonkeane)

##### 7. Verify benchmark builds on your machine are running as expected
- Go to [Apache Arrow CI Buildkite organization](https://buildkite.com/apache-arrow)
- Click on **"Arrow BCI Benchmark on ..."** Buildkite pipeline for your machine and 
verify benchmark builds are running as expected

##### 8. Verify benchmark results from your machine are logged into Conbench
- Go to [Conbench](https://conbench.ursa.dev/)
- Enter your machine name into Search box
- Click on a few runs and verify that all benchmark results form your machine are logged

##### 9. Create Pull Request to enable `publish_benchmark_results` for your machine
- Update `MACHINES` in [config.py](../config.py) and set `publish_benchmark_results` to `True` for your machine
