import pandas as pd
import sys
import glob
import os

def main():
    path = "/home/diegokernel/proyectos/spark_airflow_telemetry/data/processed/aggregated_telemetry.parquet"
    if not os.path.exists(path):
        print(f"Error: Path {path} does not exist.")
        return

    # Parquet files are typically directories in Spark
    df = pd.read_parquet(path)
    print("--- Processed Telemetry (First 5 records) ---")
    print(df.head())
    print(f"\nTotal records: {len(df)}")

if __name__ == "__main__":
    main()
