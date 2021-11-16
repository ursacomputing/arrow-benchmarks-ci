from datetime import datetime
import json
import logging
import os
import psutil
import requests
import subprocess

from utils import generate_uuid
from .run_context import run_context

benchmarkable_id = os.getenv("BENCHMARKABLE")
run_id = os.getenv("RUN_ID")
run_name = os.getenv("RUN_NAME")
machine = os.getenv("MACHINE")
build_dir = os.getcwd()
total_machine_memory = psutil.virtual_memory().total
logging.basicConfig(level=logging.DEBUG)

repos_with_benchmark_groups = [
    {
        "repo": "https://github.com/ursacomputing/benchmarks.git",
        "root": "benchmarks",
        "branch": "main",
        "setup_commands": ["python setup.py develop"],
        "path_to_benchmark_groups_list_json": "benchmarks/benchmarks.json",
        "url_for_benchmark_groups_list_json": "https://raw.githubusercontent.com/ursacomputing/benchmarks/main/benchmarks.json",
        "setup_commands_for_lang_benchmarks": {  # These commands need to be defined as functions in buildkite/benchmark/utils.sh
            "C++": ["install_archery"],
            "Python": ["create_data_dir"],
            "R": [
                "build_arrow_r",
                "install_duckdb_r_with_tpch",
                "install_arrowbench",
                "create_data_dir",
            ],
            "Java": ["build_arrow_java", "install_archery"],
            "JavaScript": ["install_java_script_project_dependencies"],
        },
        "env_vars": {
            "PYTHONFAULTHANDLER": "1",  # makes it easy to debug segmentation faults
            "BENCHMARKS_DATA_DIR": f"{os.getenv('HOME')}/data",  # allows to avoid loading Python and R benchmarks input data from s3 for every build
            "ARROWBENCH_DATA_DIR": f"{os.getenv('HOME')}/data",  # allows to avoid loading R benchmarks input data from s3 for every build
            "ARROW_SRC": f"{build_dir}/arrow",  # required by Java Script benchmarks
        },
    }
]


class BenchmarkGroup:
    def __init__(self, lang, name, options="", flags="", mock_run=False):
        self.id = generate_uuid()
        self.lang = lang
        self.name = name
        self.options = options
        self.flags = flags
        self.process_pid = psutil.Process().pid
        self.mock_run = mock_run
        self.memory_monitor = None
        self.started_at = None
        self.finished_at = None
        self.return_code = None
        self.stderr = None

    def __repr__(self):
        return f"<Benchmark {self.name} {self.lang}>"

    @property
    def command(self):
        command = f'conbench {self.name} {self.options} --run-id=$RUN_ID --run-name="$RUN_NAME"'

        if self.lang == "Java":
            command += f" --commit={benchmarkable_id} --src={build_dir}/arrow"

        return command

    @property
    def failed(self):
        if self.return_code or self.stderr:
            return self.return_code != 0 or "ERROR" in self.stderr

        return False

    @property
    def total_run_time(self):
        if self.started_at and self.finished_at:
            return self.finished_at - self.started_at

    def start_memory_monitor(self):
        if self.mock_run:
            return

        # Monitor memory only Python and R benchmarks
        if self.lang not in ["Python", "R"]:
            return

        self.memory_monitor = subprocess.Popen(
            f"python -m buildkite.benchmark.monitor_memory {self.process_pid} {self.id}",
            shell=True,
            executable="/bin/bash",
        )

    def stop_memory_monitor(self):
        if self.mock_run:
            return

        if self.memory_monitor:
            self.memory_monitor.kill()
            self.memory_monitor = None

    def log_data(self):
        return {
            "type": "BenchmarkGroupExecution",
            "id": self.id,
            "lang": self.lang,
            "name": self.name,
            "options": self.options,
            "flags": self.flags,
            "benchmarkable_id": benchmarkable_id,
            "run_id": run_id,
            "run_name": run_name,
            "machine": machine,
            "process_pid": psutil.Process().pid,
            "command": self.command,
            "started_at": str(self.started_at),
            "finished_at": str(self.finished_at),
            "total_run_time": str(self.total_run_time),
            "failed": self.failed,
            "return_code": self.return_code,
            "stderr": self.stderr,
            "total_machine_virtual_memory": total_machine_memory,
        }

    def log_execution(self):
        if self.mock_run:
            return

        logging.info(self.log_data())
        requests.post(
            "https://benchmark-jobs.ursa.dev/logs",
            data=json.dumps(self.log_data()),
            headers={"Content-Type": "application/json"},
        )


class Run:
    def __init__(self, repo_params):
        self.repo = repo_params["repo"]
        self.root = repo_params["root"]
        self.branch = repo_params["branch"]
        self.setup_commands = repo_params["setup_commands"]
        self.path_to_benchmark_groups_list_json = repo_params[
            "path_to_benchmark_groups_list_json"
        ]
        self.url_for_benchmark_groups_list_json = repo_params[
            "url_for_benchmark_groups_list_json"
        ]
        self.benchmarkable_type = os.getenv("BENCHMARKABLE_TYPE")
        self.filters = json.loads(os.getenv("FILTERS", "{}"))
        self.setup_commands_for_lang_benchmarks = repo_params[
            "setup_commands_for_lang_benchmarks"
        ]
        self.env_vars = repo_params["env_vars"]
        self.benchmark_groups = []
        self.executed_commands = []

    def capture_context(self):
        requests.post(
            f"https://benchmark-jobs.ursa.dev/runs/{run_id}",
            data=json.dumps(run_context()),
            headers={"Content-Type": "application/json"},
        )

    def execute_command(self, command, path=".", exit_on_failure=True):
        logging.info(f"Started executing -> {command}")
        self.executed_commands.append((command, path, exit_on_failure))

        result = subprocess.run(
            f"cd {path}; {command}",
            capture_output=True,
            shell=True,
            executable="/bin/bash",
        )
        return_code = result.returncode
        stderr = result.stderr.decode()
        stdout = result.stdout.decode()

        logging.info(stderr)
        logging.info(stdout)

        if exit_on_failure and (return_code != 0 or "ERROR" in stderr):
            logging.error(return_code)
            logging.error(stderr)
            raise Exception(f"Failed to execute {command}")

        # Always fail the build if benchmark logs have Internal Server Error because
        # it could mean that we are loosing benchmark results because
        # Conbench can't store benchmark results
        if "Internal Server Error" in stdout or "Internal Server Error" in stderr:
            logging.error(stdout)
            logging.error(stderr)
            raise Exception(
                "Failed to post benchmark results because of Internal Server Error"
            )

        logging.info(f"Done executing -> {command}")
        return return_code, stderr

    def setup_benchmarks_repo(self):
        self.execute_command(f"git clone {self.repo}")
        self.execute_command(f"git fetch && git checkout {self.branch}", self.root)
        for command in self.setup_commands:
            self.execute_command(command, self.root)

    def setup_conbench_credentials(self):
        with open(f"{build_dir}/{self.root}/.conbench", "w") as f:
            f.writelines(
                [
                    f"url: {os.getenv('CONBENCH_URL')}\n",
                    f"email: {os.getenv('CONBENCH_EMAIL')}\n",
                    f"password: {os.getenv('CONBENCH_PASSWORD')}\n",
                    f"host_name: {os.getenv('MACHINE')}\n",
                ]
            )

    def set_benchmark_groups(self):
        for benchmark_group in self.get_benchmark_groups():
            command = benchmark_group["command"]
            name, options = command.split(" ", 1) if " " in command else (command, "")
            self.benchmark_groups.append(
                BenchmarkGroup(
                    benchmark_group["flags"]["language"],
                    name,
                    options,
                    benchmark_group["flags"],
                    mock_run=False,
                )
            )

    def get_benchmark_groups(self):
        with open(self.path_to_benchmark_groups_list_json) as f:
            return json.load(f)

    def filter_benchmark_groups(self):
        if "command" in self.filters:
            self.benchmark_groups = [BenchmarkGroup("C++", self.filters["command"])]
            return

        if "lang" in self.filters:
            langs = self.filters["lang"].split(",")
            self.benchmark_groups = list(
                filter(
                    lambda benchmark_group: benchmark_group.lang in langs,
                    self.benchmark_groups,
                )
            )

        if "name" in self.filters:
            name = self.filters["name"]
            if name[-1] == "*":
                self.benchmark_groups = list(
                    filter(
                        lambda benchmark_group: benchmark_group.name.startswith(
                            name[:-1]
                        ),
                        self.benchmark_groups,
                    )
                )
            else:
                self.benchmark_groups = list(
                    filter(
                        lambda benchmark_group: benchmark_group.name == name,
                        self.benchmark_groups,
                    )
                )

        if "flags" in self.filters:
            self.benchmark_groups = list(
                filter(
                    lambda benchmark_group: all(
                        benchmark_group.flags.get(flag) == value
                        for flag, value in self.filters["flags"].items()
                    ),
                    self.benchmark_groups,
                )
            )

    def set_env_vars(self):
        for var, value in self.env_vars.items():
            os.environ[var] = value

    @staticmethod
    def print_env_vars():
        for var, value in sorted(os.environ.items()):
            if "PASSWORD" in var or "SECRET" in var or "TOKEN" in var:
                continue
            logging.info(f"{var}={value}")

    def benchmark_groups_for_lang(self, lang):
        return list(
            filter(
                lambda benchmark_group: benchmark_group.lang == lang,
                self.benchmark_groups,
            )
        )

    def additional_setup_for_benchmark_groups(self, lang):
        for command in self.setup_commands_for_lang_benchmarks[lang]:
            self.execute_command(f"source buildkite/benchmark/utils.sh {command}")

    def run_benchmark_groups(self, lang):
        self.print_env_vars()
        for benchmark_group in self.benchmark_groups_for_lang(lang):
            benchmark_group.start_memory_monitor()
            benchmark_group.started_at = datetime.now()

            return_code, stderr = self.execute_command(
                benchmark_group.command,
                path=self.root,
                exit_on_failure=False,
            )

            benchmark_group.finished_at = datetime.now()
            benchmark_group.return_code = return_code
            benchmark_group.stderr = stderr
            benchmark_group.stop_memory_monitor()
            benchmark_group.log_execution()

    def print_results(self):
        print(
            "======================= Benchmark Groups Results =========================="
        )
        for benchmark_group in filter(
            lambda b: b.failed is False, self.benchmark_groups
        ):
            print(
                "PASSED",
                benchmark_group.lang,
                benchmark_group.name,
                benchmark_group.total_run_time,
            )

        for benchmark_group in filter(lambda b: b.failed, self.benchmark_groups):
            if benchmark_group.stderr and len(benchmark_group.stderr) > 200:
                stderr = benchmark_group.stderr[-200:-1]
            else:
                stderr = ""
            print(
                "FAILED",
                benchmark_group.lang,
                benchmark_group.name,
                benchmark_group.return_code,
                stderr,
            )

    def failed_benchmark_groups(self):
        return list(filter(lambda b: b.failed, self.benchmark_groups))

    def run_all_benchmark_groups(self):
        self.capture_context()
        self.setup_benchmarks_repo()
        self.setup_conbench_credentials()
        self.set_env_vars()
        self.set_benchmark_groups()
        self.filter_benchmark_groups()

        for lang in ["C++", "Java", "Python", "R", "JavaScript"]:
            if not self.benchmark_groups_for_lang(lang):
                continue

            if self.benchmarkable_type == "arrow-commit":
                self.additional_setup_for_benchmark_groups(lang)

            self.run_benchmark_groups(lang)

        self.print_results()

        if len(self.failed_benchmark_groups()) > 0:
            raise Exception("Build has failed benchmarks.")


# MockRun is used for:
# 1. testing Run().run_all_benchmark_groups method in non-benchmark machine environment without executing any
# shell commands
# 2. checking if provided benchmark filters on PR benchmark request comments do not filter out all benchmarks in
# https://raw.githubusercontent.com/ursacomputing/benchmarks/main/benchmarks.json
class MockRun(Run):
    def __init__(self, repo_params, filters):
        super().__init__(repo_params)
        self.filters = filters

    def capture_context(self):
        pass

    def set_env_vars(self):
        pass

    def setup_conbench_credentials(self):
        pass

    def execute_command(self, command, path=".", exit_on_failure=True):
        logging.info(f"Started executing -> {command}")
        self.executed_commands.append((command, path, exit_on_failure))
        return 0, ""

    def get_benchmark_groups(self):
        return requests.get(self.url_for_benchmark_groups_list_json).json()

    def has_benchmark_groups_to_execute(self):
        self.set_benchmark_groups()
        self.filter_benchmark_groups()
        return len(self.benchmark_groups) > 0
