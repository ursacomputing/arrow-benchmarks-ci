import json
from utils import generate_uuid

from integrations.buildkite import buildkite


pipeline_name = "arrow-bci-benchmark-on-ec2-m5-4xlarge-us-east-2"
machine = "ec2-m5-4xlarge-us-east-2"
commit = "c82f80ad76bf80c7be28a2a0183b9e667fc89e5b"  # 10 iterations
branch = "elena/research-python-and-r-benchmarks-with-interations-10-and-15"
message = "test"
filters = {
            "langs": {
                "R": {
                    "names": [
                        "dataframe-to-table",
                        "file-read",
                        "file-write",
                        "partitioned-dataset-filter",
                        "wide-dataframe",
                        "tpch",
                    ]
                },
                "Python": {
                    "names": [
                        "csv-read",
                        "dataframe-to-table",
                        "dataset-filter",
                        "dataset-read",
                        "dataset-select",
                        "dataset-selectivity",
                        "file-read",
                        "file-write",
                        "wide-dataframe",
                    ]
                }
            }
        }
env = {
    "BENCHMARKABLE": "27e4bc16614f36857e1cdd491eba3fe3ec03d25e",
    "BENCHMARKABLE_TYPE": "arrow-commit",
    "FILTERS": json.dumps(filters),
    "MACHINE": machine,
    "RUN_ID": generate_uuid(),
    "RUN_NAME": f"test",
    "PYTHON_VERSION": "3.8",
}

print(buildkite.create_build(pipeline_name, commit, branch, message, env))
