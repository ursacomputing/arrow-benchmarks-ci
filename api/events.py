import hashlib
import hmac
import json
import os

from flask import request
from flask_restful import Resource

from integrations.github import github
from logger import log
from models.benchmarkable import Benchmarkable

expected_phrase = "@ursabot please benchmark"
benchmark_command_examples = """
Supported benchmark command examples:

`@ursabot benchmark help`

To run all benchmarks:
`@ursabot please benchmark`

To filter benchmarks by language:
`@ursabot please benchmark lang=Python`
`@ursabot please benchmark lang=C++`
`@ursabot please benchmark lang=R`
`@ursabot please benchmark lang=Java`
`@ursabot please benchmark lang=JavaScript`

To filter Python and R benchmarks by name:
`@ursabot please benchmark name=file-write`
`@ursabot please benchmark name=file-write lang=Python`
`@ursabot please benchmark name=file-.*`

To filter C++ benchmarks by archery --suite-filter and --benchmark-filter:
`@ursabot please benchmark command=cpp-micro --suite-filter=arrow-compute-vector-selection-benchmark --benchmark-filter=TakeStringRandomIndicesWithNulls/262144/2 --iterations=3`

For other `command=cpp-micro` options, please see https://github.com/ursacomputing/benchmarks/blob/main/benchmarks/cpp_micro_benchmarks.py
"""


class UnsupportedBenchmarkCommand(Exception):
    pass


class CommitHasScheduledBenchmarkRuns(Exception):
    pass


def verify_github_request_signature(github_request):
    actual_github_request_signature = github_request.headers.get("X-Hub-Signature-256")

    if not actual_github_request_signature:
        raise Exception("X-Hub-Signature-256 header was not sent.")

    github_secret = os.getenv("GITHUB_SECRET")

    if not github_secret:
        raise Exception("GITHUB_SECRET is not set in webhooks-secret")

    expected_github_request_signature = "sha256=" + (
        hmac.new(
            key=github_secret.encode(),
            msg=github_request.data,
            digestmod=hashlib.sha256,
        ).hexdigest()
    )

    if not hmac.compare_digest(
        expected_github_request_signature, actual_github_request_signature
    ):
        raise Exception(
            "Github's actual X-Hub-Signature-256 dit not match expected X-Hub-Signature-256"
        )


def get_pull_benchmark_filters(comment):
    if expected_phrase not in comment:
        raise UnsupportedBenchmarkCommand

    filters_phrase = comment.split(expected_phrase)[-1].strip()

    if not filters_phrase:
        return {}

    # Command option is only supported for C++ benchmarks
    if filters_phrase.startswith("command=cpp-micro"):
        return {"command": filters_phrase.replace("command=", "")}

    filters = {}
    for text_filter in filters_phrase.split(" "):
        if text_filter == "":
            continue

        filter_key, filter_value = text_filter.split("=")

        if (
            filter_key not in ("lang", "name")
            or filter_key in filters
            or (
                filter_key == "lang"
                and filter_value not in ["Python", "C++", "R", "Java", "JavaScript"]
            )
        ):
            raise UnsupportedBenchmarkCommand

        filters[filter_key] = filter_value

    # Filtering C++, Java, JavaScript benchmarks by name is not supported
    if filters.get("lang") in ["C++", "Java", "JavaScript"] and filters.get("name"):
        raise UnsupportedBenchmarkCommand

    return filters


def create_benchmarkable_and_runs(pull_dict, pull_benchmark_filters):
    benchmarkable_type = "arrow-commit"
    id = pull_dict["head"]["sha"]

    if Benchmarkable.get(id):
        raise CommitHasScheduledBenchmarkRuns(
            f"Commit {id} already has scheduled benchmark runs."
        )

    data = github().get_commit(id)
    baseline_id = pull_dict["base"]["sha"]
    baseline_data = github().get_commit(baseline_id)

    Benchmarkable.create(
        dict(
            id=id,
            type=benchmarkable_type,
            data=data,
            baseline_id=baseline_id,
            reason="pull-request",
            filters=pull_benchmark_filters,
            pull_number=pull_dict["number"],
        )
    )
    Benchmarkable.create(
        dict(
            id=baseline_id,
            type=benchmarkable_type,
            data=baseline_data,
            baseline_id=baseline_data["parents"][0]["sha"],
            reason="arrow-commit",
        )
    )


def is_pull_request_comment_for_ursabot(event):
    return (
        event.get("action") == "created"
        and event.get("issue")
        and event.get("comment")
        and event["comment"]["body"]
        .replace("\n", "")
        .replace("\r", "")
        .startswith("@ursabot")
        and benchmark_command_examples not in event["comment"]["body"]
    )


class Events(Resource):
    def post(self):
        verify_github_request_signature(request)
        event = json.loads(request.data)
        log.info(event)

        if is_pull_request_comment_for_ursabot(event):
            pull_number = event["issue"]["number"]

            # TODO: remove this code once done testing
            if int(pull_number) not in [1234, 9272]:
                return "", 202

            try:
                benchmark_filters = get_pull_benchmark_filters(event["comment"]["body"])
                pull_dict = github().get_pull(pull_number)
                create_benchmarkable_and_runs(pull_dict, benchmark_filters)
            except UnsupportedBenchmarkCommand:
                github.create_pull_comment(pull_number, benchmark_command_examples)
            except CommitHasScheduledBenchmarkRuns as e:
                github.create_pull_comment(pull_number, e.args[0])

        return "", 202
