# Redshift ETL script using python on EC2

## Load queue table
https://github.com/vishaldesai/AWS_Redshift/blob/master/ETL/PythonEC2/LoadDynamoDB.txt

## Create Secrets manager

{
  "password": "xxx$",
  "cluster": "redshift.xxx.us-east-1.redshift.amazonaws.com",
  "port": "xxx",
  "database": "xxxxx",
  "username": "xxxx",
  "snstopic": "arn:aws:sns:us-east-1:xxxxx:xxxx"
}

## Run ETL script
https://github.com/vishaldesai/AWS_Redshift/blob/master/ETL/PythonEC2/ETL.py
