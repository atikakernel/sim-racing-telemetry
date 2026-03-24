from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
import os

# Paths
PROJECT_DIR = "/home/diegokernel/proyectos/spark_airflow_telemetry"
VENV_PYTHON = f"{PROJECT_DIR}/venv/bin/python"
SPARK_SCRIPT = f"{PROJECT_DIR}/scripts/spark_processor.py"
RAW_DATA = f"{PROJECT_DIR}/data/raw/vehicle_data.csv"
PROCESSED_DATA = f"{PROJECT_DIR}/data/processed/aggregated_telemetry.parquet"

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'vehicle_telemetry_pipeline',
    default_args=default_args,
    description='A simple Spark and Airflow telemetry pipeline',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['telemetry', 'spark'],
) as dag:

    # Task to ensure JAVA_HOME is set and run Spark
    # We use a single BashOperator to simplify the environment setup (JAVA_HOME)
    process_telemetry = BashOperator(
        task_id='process_telemetry_spark',
        bash_command=f"""
            export JAVA_HOME=$(readlink -f /usr/bin/java | sed "s:/bin/java::") && \
            {VENV_PYTHON} {SPARK_SCRIPT} {RAW_DATA} {PROCESSED_DATA}
        """,
    )

    process_telemetry
