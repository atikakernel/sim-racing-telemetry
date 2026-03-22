import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, max as spark_max, sum as spark_sum

def clean_column_names(df):
    for c in df.columns:
        new_c = c.replace(' ', '_').replace('[', '_').replace(']', '').replace('(', '_').replace(')', '').replace('/', '_per_')
        df = df.withColumnRenamed(c, new_c)
    return df

def main(input_path, output_path):
    spark = SparkSession.builder \
        .appName("Telemetry Data Processor") \
        .config("spark.sql.parquet.compression.codec", "snappy") \
        .getOrCreate()
    
    print(f"Reading data from {input_path}")
    df = spark.read.csv(input_path, header=True, inferSchema=True)
    df = clean_column_names(df)
    
    print("Aggregating telemetry data by VehId and Trip...")
    # Based on the CSV header, the column names after cleaning will be:
    # Vehicle_Speed_km_per_h, Engine_RPM_RPM, Fuel_Rate_L_per_hr
    
    agg_df = df.groupBy("VehId", "Trip").agg(
        avg("Vehicle_Speed_km_per_h").alias("avg_speed_kmh"),
        spark_max("Engine_RPM_RPM").alias("max_rpm"),
        spark_sum("Fuel_Rate_L_per_hr").alias("total_fuel_rate")
    )
    
    # Filter out null VehId just in case
    agg_df = agg_df.filter(col("VehId").isNotNull())
    
    print(f"Writing processed data to {output_path}")
    agg_df.write.mode("overwrite").parquet(output_path)
    print("Data processing complete.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: spark_processor.py <input_path> <output_path>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
