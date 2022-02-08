# kubectl exec deploy/arrow-bci-deployment -- python -m scripts.rerun-failed-builds

from datetime import datetime, timedelta

from models.run import Run

runs = Run.all(status="failed")

runs = [r for r in runs if r.created_at > datetime.now() - timedelta(hours=24)]

print(f"Found {len(runs)} failed builds")

# Trigger new Buildkite builds for all failed runs
for run in runs:
    run.status = "created"
    run.buildkite_data = None
    run.scheduled_at = None
    run.finished_at = None
    run.total_run_time = None
    run.context = None
    run.machine_info = None
    run.conda_packages = None
    run.save()

# Resend slack notifications and update Pull Request comments associated with failed runs
for run in runs:
    for notification in run.benchmarkable.notifications:
        notification.finished_at = None
        notification.save()
