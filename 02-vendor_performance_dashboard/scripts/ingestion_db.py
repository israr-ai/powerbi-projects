import duckdb
import os
import logging
import time



# Logging configuration
logging.basicConfig(
    filename="logs/ingestion_db.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a"
)

# DuckDB connection
con = duckdb.connect("inventory.db")

def ingest_db(df, table_name, con):
    """ This function will ingest the dataframe into database table"""
    con.register("temp_df", df)
    con.execute(f"""
        CREATE OR REPLACE TABLE {table_name} AS
        SELECT * FROM temp_df
    """)

    

def load_raw_data():
    """
    This function loads CSV files and ingests them into DuckDB
    """

    start = time.time()

    for file in os.listdir("data"):

        if file.endswith(".csv"):

            table_name = file[:-4]
            file_path = os.path.join("data", file)

            print(f"Processing {file}")
            logging.info(f"Ingesting {file} into DB")

            try:
                con.execute(f"""
                    CREATE OR REPLACE TABLE {table_name} AS
                    SELECT *
                    FROM read_csv_auto('{file_path}')
                """)

                print(f"{file} completed")
                logging.info(f"{file} ingestion completed")

            except Exception as e:
                print(f"Error processing {file}: {e}")
                logging.error(f"Error processing {file}: {e}")

    end = time.time()
    total_time = (end - start) / 60

    logging.info("--------------- Ingestion Complete -----------")
    logging.info(f"Total Time Taken: {total_time:.2f} minutes")

    print(f"\nTotal Time Taken: {total_time:.2f} minutes")


if __name__ == '__main__':
    load_raw_data()
    con.close()