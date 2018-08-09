#
#
# python intellietl.py --p_tgt_db redshiftdb --p_src_schema snow_d1 --p_load_queue redshift_load_queue --p_code_dir code_dir
import boto3
import ast
import json
import glob
import argparse
import sys
import os
import string
import subprocess
import zipfile
import logging
import calendar
import time
import fcntl
from boto3.dynamodb.conditions import Key, Attr
from subprocess import check_output, STDOUT, CalledProcessError


def main(arguments):

    #logging
    p_ts = str(calendar.timegm(time.gmtime()))
    p_logfile = 'intellietl_' + p_ts + '.log'
    logging.basicConfig(filename=p_logfile, level=logging.INFO)

    #lock file
    p_processlock = open('intellietl.lock', 'w+')
    try:
        fcntl.flock(p_processlock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        logging.info('Success: Acquired lock')
    except:
        logging.error('Error: Cannot acquire lock')
        sys.exit(1)

    #Parse arguments
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--p_tgt_db', required=True)
    parser.add_argument('--p_code_dir', required=True)
    parser.add_argument('--p_src_schema', required=True)
    parser.add_argument('--p_load_queue', required=True)
    
    args = parser.parse_args(arguments)

    #Secret manager
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(
        SecretId=args.p_tgt_db
    )

    sm_response = json.loads(response['SecretString'])
    p_username = sm_response['username']
    p_password = sm_response['password']
    p_redshift_cluster = sm_response['cluster']
    p_port = sm_response['port']
    p_database = sm_response['database']
    p_snstopic = sm_response['snstopic']
    
    #download files from s3 location
    #s3 = boto3.resource('s3')
    #s3.meta.client.download_file(args.p_etlscript_bucket, args.p_etlscript_file, 'run.zip')
    #zip = zipfile.ZipFile('run.zip')
    #zip.extractall()

    #Query dynamodb
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table(args.p_load_queue)

    response = table.query(
        KeyConditionExpression=Key('queue_name').eq('snow'), ScanIndexForward = True, Limit = 2
    )

    #Loop through DynamoDB queue and execute ETL scripts on Redshift
    for i in response['Items']:
        # search for ingest_dt= with regexp
        p_ingest_dt = i['s3_path'].split('/')

        p_path = args.p_code_dir + '/' + i['src_table'] + '__*.sql'
        p_sqlfile = glob.glob(p_path)
        for j, val in enumerate(p_sqlfile):
            p_sqllog = p_sqlfile[j].split('.')[0] + '_' + p_ts + '.log'
            pgsql = 'export PGPASSWORD=' + p_password + '; psql -h ' + p_redshift_cluster +  ' -p ' + p_port + ' -U ' + p_username +  ' -d ' + p_database +  ' -v ' + \
                p_ingest_dt[-1] + ' -v job_id=' + p_ts + ' -v ON_ERROR_STOP=1 -P pager=off' + ' -f ' +  p_sqlfile[j] + \
                 ' -L ' + p_sqllog + ' &> /dev/null; echo $?'

            logging.info('Executing: ' + pgsql)
            o = check_output(pgsql , stderr=None, shell=True)

            if int(o.decode("utf-8")) == 0:
                #log success message and remove queue record from DynamoDB
                logging.info('Success: ' + pgsql)
                p_result = 'success'
            else:
                #log error message and publish message on SNS
                logging.error('Error: ' + pgsql)
                p_result = 'failure'
                client = boto3.client('sns')

                p_subject = 'Failure for job_id=' + \
                    p_ts + ' load script ' + p_sqlfile[j] + '.sql'
                p_message = 'Check logfile ' + p_sqllog 
                response = client.publish(
                    TopicArn=p_snstopic,
                    Message=p_message,
                    Subject=p_subject
                )

        if p_result == 'success':
            dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            table = dynamodb.Table(args.p_load_queue)
            p_key = eval("{" + "'queue_name':" + "'snow'" + "," + "'queue_utc_ts':" + str(i['queue_utc_ts']) + "}")
            response = table.delete_item(Key=p_key)
        
    
    fcntl.flock(p_processlock, fcntl.LOCK_UN)
    
if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
