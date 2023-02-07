import os
import logging
import multiprocessing

num_cores = os.environ.get('SLURM_CPUS_PER_TASK', None)
if num_cores is None:
    num_cores = multiprocessing.cpu_count()


def parallel_eda_call(eda_job, params):
    """
    Runner function for running eda job objects
    """
    if params and 'top_features' in params:
        eda_job.run(params['top_features'])
    else:
        eda_job.run()


def parallel_kfold_call(kfold_job):
    """
    Runner function for running cv job objects
    """
    kfold_job.run()


def model_runner_fn(job, model):
    """
    Runner function for running model job objects
    """
    job.run(model)


def runner_fn(job):
    """
    Runner function for running job objects
    """
    job.run()


def run_jobs(job_list):
    """
    Function to start and join a list of job objects
    """
    for i in range(0, len(job_list), num_cores):
        sub_jobs(job_list[i:i + num_cores])


def sub_jobs(job_list):
    for job in job_list:
        job.start()
    for job in job_list:
        job.join()
