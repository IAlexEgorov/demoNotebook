from kubernetes.client import models as k8s

try:
    from airflow import DAG
    from airflow.operators.python_operator import PythonOperator
    from airflow.decorators import task
    
    from datetime import datetime, timedelta
    import pandas as pd
    from sklearn import datasets
    import os

    from evidently.dashboard import Dashboard
    from evidently.dashboard.tabs import DataDriftTab

    from evidently.model_profile import Profile
    from evidently.model_profile.sections import DataDriftProfileSection
    import boto3

except Exception as e:
    print("Error  {} ".format(e))

dir_path = 'tmp'
file_path = 'boston_data_drift_by_airflow.html'

def load_data_execute(**context):
    print("load_data_execute   ")

    boston = datasets.load_boston()
    boston_frame = pd.DataFrame(boston.data, columns = boston.feature_names)

    context['ti'].xcom_push(key='boston_frame', value=boston_frame.to_json())


def drift_analysis_execute(**context):
    dataframe = context.get("ti").xcom_pull(key='boston_frame')
    data = pd.read_json(dataframe)

    boston_data_drift_dashboard = Dashboard(tabs=[DataDriftTab()])
    boston_data_drift_dashboard.calculate(data[:200], data[200:])

    try:
        os.mkdir(dir_path)
    except OSError:
        print ("Creation of the directory {} failed".format(dir_path))

    boston_data_drift_dashboard.save(os.path.join(dir_path, file_path))

def publish_report(**context):
    client = boto3.client(
    's3',
    aws_access_key_id='D5AVIET70ETHEJKZDV8Y',
    aws_secret_access_key='JABGFAPGxEJcyGFU7J8odWksX75FNO6ERpFWknQ1',
    endpoint_url='http://ceph.ml.neoflex.ru:7480'
    )
    client.put_object(Body=os.path.join(dir_path, file_path), Bucket='dognauts-airf', Key=os.path.join('evidently', file_path))

with DAG(
        dag_id="evidently_drift_dashboard",
        schedule_interval=None,
        default_args={
            "owner": "airflow",
            "retries": 1,
            "retry_delay": timedelta(minutes=5),
            "start_date": datetime(2021, 1, 1),
        },
        catchup=False) as f:

    load_data_execute = PythonOperator(
        task_id="load_data_execute",
        python_callable=load_data_execute,
        provide_context=True,
        op_kwargs={"parameter_variable":"parameter_value"} #not used now, may be used to specify data
    )

    drift_analysis_execute = PythonOperator(
        task_id="drift_analysis_execute",
        python_callable=drift_analysis_execute,
        provide_context=True,
    )

    publish_report = PythonOperator(
        task_id="publish_report",
        python_callable=publish_report,
        provide_context=True,
    )

load_data_execute >> drift_analysis_execute >> publish_report

