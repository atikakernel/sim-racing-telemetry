from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import os

# Configuración de rutas
PROJECT_ROOT = "/home/diegokernel/proyectos/spark_airflow_telemetry"
SPARK_SCRIPT = os.path.join(PROJECT_ROOT, "scripts/spark_processor.py")
INPUT_FILE = os.path.join(PROJECT_ROOT, "data/raw/vehicle_data.csv")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "data/processed/vehicle_telemetry_agg")
SPARK_SUBMIT = os.path.join(PROJECT_ROOT, "venv/bin/spark-submit")

# Configuración de dbt
DBT_PROJECT_DIR = os.path.join(PROJECT_ROOT, "telemetry_dbt")
DBT_BIN = os.path.join(PROJECT_ROOT, "venv/bin/dbt")

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'email_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'vehicle_telemetry_processing',
    default_args=default_args,
    description='Pipeline de telemetría de vehículos usando Spark, dbt y Airflow',
    schedule_interval=timedelta(days=1),
    catchup=False,
    tags=['spark', 'telemetry', 'dbt'],
) as dag:

    # 1. Verificar si el archivo de datos crudos existe
    check_input_file = BashOperator(
        task_id='check_input_file',
        bash_command=f'test -f {INPUT_FILE}',
    )

    # 2. Ejecutar el procesamiento de Spark (Curación)
    run_spark_job = BashOperator(
        task_id='run_spark_job',
        bash_command=f'{SPARK_SUBMIT} {SPARK_SCRIPT} {INPUT_FILE} {OUTPUT_PATH}',
        env={
            **os.environ,
            'JAVA_HOME': '/usr/lib/jvm/java-21-openjdk-amd64',
            'SPARK_HOME': os.path.join(PROJECT_ROOT, "venv/lib/python3.12/site-packages/pyspark"),
            'PATH': f'{os.path.join(PROJECT_ROOT, "venv/bin")}:/usr/lib/jvm/java-21-openjdk-amd64/bin:{os.environ.get("PATH", "")}'
        }
    )

    # 3. Ejecutar transformaciones analíticas con dbt
    # Navega al directorio del proyecto y corre dbt usando el perfil local
    run_dbt_transformations = BashOperator(
        task_id='run_dbt_transformations',
        bash_command=f'cd {DBT_PROJECT_DIR} && {DBT_BIN} run --profiles-dir .',
    )

    # Definir el flujo: Check -> Spark -> dbt
    check_input_file >> run_spark_job >> run_dbt_transformations
