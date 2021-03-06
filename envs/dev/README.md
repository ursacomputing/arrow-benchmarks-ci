# Dev Env

Dev env is used for testing APIs and CI scripts with real Buildkite, Github, Pypy and Slack and mocked Conbench.

### Setup Conda env
### Autogenerate a migration
```shell script
cd ~/arrow-benchmarks-ci
conda create -y -n arrow-benchmarks-ci python=3.8
conda activate arrow-benchmarks-ci
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### Edit envs/dev-conda/env
In order to test APIs and CI scripts with real Buildkite, Github, Pypy and Slack, please edit `envs/dev-conda/env` and
    add values for these environment variables:
- BUILDKITE_API_TOKEN
- BUILDKITE_ORG
- GITHUB_API_TOKEN
- GITHUB_SECRET
- SLACK_API_TOKEN
- SLACK_CHANNEL_FOR_BENCHMARK_RESULTS
- SLACK_USER_ID_FOR_WARNINGS

### Set environment variables
```shell script
source envs/dev/env
```

### Start DB and create `postgres` user
```shell script
$ brew services start postgres
$ psql -d postgres
psql (13.3)
Type "help" for help.

postgres=# create user postgres with password 'postgres';
CREATE ROLE
postgres=# 
```
    
### Create DB schema
```shell script
dropdb postgres
createdb postgres
alembic upgrade head
```

### Populate machine table and create a Buildkite pipeline for each machine
```shell script
python -c 'from buildkite.deploy.update_machine_configs import update_machine_configs; update_machine_configs()'
```

### Autogenerate a migration
```shell script
# Start postgres db
$ brew services start postgres

# Recreate postgres db
$ dropdb postgres
$ createdb postgres

# Create postgres user
$ psql -d postgres
psql (13.3)
Type "help" for help.
postgres=# create user postgres with password 'postgres';
CREATE ROLE
postgres=#\q

# Generate alembic migration
$ cd ~/arrow-benchmarks-ci
$ git checkout main && git pull
$ alembic upgrade head
$ git checkout your-branch
$ alembic revision --autogenerate -m "new"
```

### Run individual CI scripts
```shell script
python -c 'from buildkite.deploy.update_machine_configs import update_machine_configs; update_machine_configs()'
python -c 'from buildkite.schedule_and_publish.get_commits import get_commits; get_commits()'
python -c 'from buildkite.schedule_and_publish.get_pyarrow_versions import get_pyarrow_versions; get_pyarrow_versions()'
python -c 'from buildkite.schedule_and_publish.create_benchmark_builds import create_benchmark_builds; create_benchmark_builds()'
```
    
### Run an automated script that runs all CI scripts
`checkr/openmock` docker container is used to mock Conbench

```shell script
source envs/dev/env 
docker run -it -d -p 9998:9999 -v $(pwd)/tests/mocked_integrations:/data/templates checkr/openmock
python -m envs.dev.test
```
