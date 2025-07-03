import time
from rq import get_current_job


def long_task(steps: int) -> str:
    """
    Dummy long-running task: sleeps one second per step,
    writing progress into job.meta.
    """
    job = get_current_job()
    job.meta["step"] = "started"
    job.save_meta()

    for i in range(1, steps + 1):
        time.sleep(3)
        job.meta["step"] = f"progress: {i}/{steps}"
        job.save_meta()

    job.meta["step"] = "done"
    job.save_meta()
    return f"Completed {steps} steps"
