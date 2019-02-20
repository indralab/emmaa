"""The AWS Lambda emmaa-model-update definition.

This file contains the function that will be run daily and start model update 
cycle. It must be placed on AWS Lambda, which can either be done manually (not 
recommended) or by running:

$ python update.py

in this directory.
"""

import boto3
from datetime import datetime

JOB_DEF = 'emmaa_jobdef'
QUEUE = 'run_db_lite_queue'
PROJECT = 'aske'
PURPOSE = 'update-emmaa-models'
BRANCH = 'indralab/master'


def lambda_handler(event, context):
    """Initial batch jobs for any changed models or tests.

    This function is designed to be placed on lambda, taking the event and
    context arguments that are passed, and extracting the names of the
    uploaded (which includes changed) model or test definitions on s3.
    Lambda is configured to be triggered by any such changes, and will
    automatically run this script.

    See the top of the page for the Lambda update procedure.

    Note that this function must always have the same parameters, even if any
    or all of them are unused, because we do not have control over what Lambda
    sends as parameters. For more information on the context parameter, see
    here:

      https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    And for more informationn about AWS Lambda handlers, see here:

      https://docs.aws.amazon.com/lambda/latest/dg/python-programming-model-handler-types.html


    Parameters
    ----------
    event : dict
        A dictionary containing metadata regarding the triggering event.
    context : object
        This is an object containing potentially useful context provided by
        Lambda. See the documentation cited above for details.

    Returns
    -------
    ret : dict
        A dict containing 'statusCode', with a valid HTTP status code, and any
        other data to be returned to Lambda.
    """
    batch = boto3.client('batch')
    core_command = 'bash scripts/git_and_run.sh'
    if BRANCH is not None:
        core_command += f' --branch {BRANCH}'
    core_command += (' python scripts/run_model_update.py')
    print(core_command)
    cont_overrides = {
        'command': ['python', '-m', 'indra.util.aws', 'run_in_batch',
                    '--project', PROJECT, '--purpose', PURPOSE,
                    core_command]
        }
    now_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    ret = batch.submit_job(jobName=f'model_update_{now_str}',
                            jobQueue=QUEUE, jobDefinition=JOB_DEF,
                            containerOverrides=cont_overrides)
    job_id = ret['jobId']

    return {'statusCode': 200, 'result': 'SUCCESS', 'job_id': job_id}
