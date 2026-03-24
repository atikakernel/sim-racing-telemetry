# Vehicle Telemetry Big Data Pipeline

This project implements a Big Data pipeline using **Apache Spark** for data processing and **Apache Airflow** for orchestration. It ingests vehicle telemetry and energy consumption data from Kaggle, transforms it to extract key performance indicators (KPIs), and saves the results in an optimized Parquet format.

## Architecture

1.  **Data Ingestion**: Downloads the "Vehicle Energy & Telemetry Dataset" from Kaggle using the Kaggle API.
2.  **Processing (Spark)**: A PySpark job reads the raw CSV, cleans column names, and aggregates data by `VehId` and `Trip` to calculate:
    -   Average Speed (km/h)
    -   Maximum Engine RPM
    -   Total Fuel Rate Consumption
3.  **Orchestration (Airflow)**: A DAG (`vehicle_telemetry_pipeline`) manages the execution of the Spark job, ensuring the environment (Java) is correctly configured.

## Project Structure

```bash
.
├── airflow/                   # Airflow home directory (DB, logs, and configs)
│   └── dags/                  # Airflow DAG definitions
│       └── telemetry_dag.py
├── data/
│   ├── processed/             # Processed Parquet files
│   └── raw/                   # Raw CSV data from Kaggle
├── scripts/
│   └── spark_processor.py      # PySpark transformation script
├── requirements.txt           # Python dependencies
└── venv/                      # Python virtual environment
```

## Setup & Implementation

### Prerequisites

-   Python 3.12+
-   Java 21 (required by PySpark)
-   Kaggle API Key (`kaggle.json`)

### Installation

1.  Clone the repository:
    ```bash
    git clone <repository_url>
    cd spark_airflow_telemetry
    ```

2.  Initialize the environment and install dependencies:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  Initialize Airflow:
    ```bash
    export AIRFLOW_HOME=$(pwd)/airflow
    airflow db init
    airflow users create --username admin --firstname Admin --lastname User --role Admin --email admin@example.com --password admin888
    ```

### Running the Pipeline

To run the Spark job manually:
```bash
export JAVA_HOME=$(readlink -f /usr/bin/java | sed "s:/bin/java::")
python scripts/spark_processor.py data/raw/vehicle_data.csv data/processed/aggregated_telemetry.parquet
```

To run Airflow:
```bash
export AIRFLOW_HOME=$(pwd)/airflow
# Start scheduler in one terminal
airflow scheduler
# Start webserver in another
airflow webserver
```

## Dataset
The project uses the [Vehicle Energy & Telemetry Dataset](https://www.kaggle.com/datasets/yashdev01/vehicle-energy-and-telemetry-dataset) from Kaggle.
