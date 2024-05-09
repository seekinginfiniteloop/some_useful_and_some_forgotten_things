import sqlite3

import pandas as pd


def write_csv_to_sqlite(csv_file: str, db_name: str, table_name: str, chunk_size: int = 50000) -> None:
    """
    Read the CSV in chunks and write to SQLite
    """
    # Create SQLite database
    conn = sqlite3.connect(db_name)

    # Initialize counter
    for chunk_no, chunk in enumerate(pd.read_csv(csv_file, chunksize=chunk_size)):
        chunk.to_sql(name=table_name, con=conn, if_exists='append', index=False)
        print(f"Processed chunk {chunk_no+1}")

    print(f"Processed {table_name} csv")

    # Close the SQLite database connection
    conn.close()

