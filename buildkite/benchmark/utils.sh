#!/bin/bash

init_conda() {
  eval "$(command "$HOME/miniconda3/bin/conda" 'shell.bash' 'hook' 2> /dev/null)"
}

create_conda_env_for_arrow_commit() {
  pushd $REPO_DIR
  
  if [[ "$OSTYPE" == "darwin"* ]]
  then
    aws_sdk_version="1.9.185"
  else
    aws_sdk_version=$(cat cpp/thirdparty/versions.txt | grep ARROW_AWSSDK_BUILD_VERSION= | sed s/"ARROW_AWSSDK_BUILD_VERSION="//)
  fi
  
  conda create -y -n "${BENCHMARKABLE_TYPE}" -c conda-forge \
  --file ci/conda_env_unix.txt \
  --file ci/conda_env_cpp.txt \
  --file ci/conda_env_python.txt \
  compilers \
  python="${PYTHON_VERSION}" \
  pandas \
  r

  source dev/conbench_envs/hooks.sh activate_conda_env_for_benchmark_build
  source dev/conbench_envs/hooks.sh install_arrow_python_dependencies
  
  if [[ "$OSTYPE" == "darwin"* ]]
  then
    # archery gets SIGKILLed with cctools==973.0.1
    conda install -y -c conda-forge cctools==949.0.1
  fi
  
  source dev/conbench_envs/hooks.sh set_arrow_build_and_run_env_vars

  export RANLIB=`which $RANLIB`
  export AR=`which $AR`
  export ARROW_JEMALLOC=OFF

  source dev/conbench_envs/hooks.sh build_arrow_cpp
  source dev/conbench_envs/hooks.sh build_arrow_python
  popd
}

create_conda_env_for_pyarrow_apache_wheel() {
  conda create -y -n pyarrow-apache-wheel -c conda-forge \
    python="${PYTHON_VERSION}" \
    pandas
  conda activate pyarrow-apache-wheel
  pip install "${BENCHMARKABLE}"
}

create_conda_env_for_benchmarkable_repo_commit() {
  conda create -y -n "${BENCHMARKABLE_TYPE}" python="${PYTHON_VERSION}"
  conda activate "${BENCHMARKABLE_TYPE}"
}

clone_repo() {
  rm -rf arrow
  git clone "${REPO}"
  pushd $REPO_DIR
  git fetch -v --prune -- origin "${BENCHMARKABLE}"
  git checkout -f "${BENCHMARKABLE}"
  popd
}

install_conbench() {
  git clone https://github.com/conbench/conbench.git
  pushd conbench
  pip install -r requirements-cli.txt
  pip install -U PyYAML
  python setup.py install
  
  # Workaround until conbench is fixed
  pip uninstall -y pytest
  pip install pytest==6.2.5
  popd
}

build_arrow_r() {
  pushd $REPO_DIR
  source dev/conbench_envs/hooks.sh build_arrow_r
  popd
}

build_arrow_java() {
  pushd $REPO_DIR
  source dev/conbench_envs/hooks.sh build_arrow_java
  popd
}

install_archery() {
  clone_repo
  pushd $REPO_DIR
  source dev/conbench_envs/hooks.sh install_archery
  popd
}

install_arrowbench() {
  # do I need to cd into benchmarks dir?
  git clone https://github.com/ursacomputing/arrowbench.git
  R -e "remotes::install_local('./arrowbench')"
}

install_duckdb_r_with_tpch() {
  git clone https://github.com/duckdb/duckdb.git

  # now fetch the latest tag to install
  cd duckdb
  git fetch --tags
  latestTag=$(git describe --tags `git rev-list --tags --max-count=1`)
  git checkout $latestTag

  # and then do the install
  cd tools/rpkg
  R -e "remotes::install_deps()"
  DUCKDB_R_EXTENSIONS=tpch R CMD INSTALL .
}

install_java_script_project_dependencies() {
  pushd $REPO_DIR
  source dev/conbench_envs/hooks.sh install_java_script_project_dependencies
  popd
}

create_data_dir() {
  mkdir -p "${BENCHMARKS_DATA_DIR}"
  mkdir -p "${BENCHMARKS_DATA_DIR}/temp"
}

test_pyarrow_is_built() {
  echo "------------>Testing pyarrow is built"
  python -c "import pyarrow; print(pyarrow.__version__)"
  echo "------------>End"
}

create_conda_env_and_run_benchmarks() {
  init_conda
  case "${BENCHMARKABLE_TYPE}" in
    "arrow-commit")
      export REPO=https://github.com/apache/arrow.git
      export REPO_DIR=arrow
      clone_repo
      create_conda_env_for_arrow_commit
      test_pyarrow_is_built
      ;;
    "pyarrow-apache-wheel")
      create_conda_env_for_pyarrow_apache_wheel
      ;;
    "benchmarkable-repo-commit")
      export REPO=https://github.com/ElenaHenderson/benchmarkable-repo.git
      export REPO_DIR=benchmarkable-repo
      clone_repo
      create_conda_env_for_benchmarkable_repo_commit
      ;;
  esac

  install_conbench
  python -m buildkite.benchmark.run_benchmark_groups
}

"$@"
