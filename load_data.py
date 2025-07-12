import sqlite3

import pandas as pd

# read from file into pandas
df = pd.read_csv('data/BasicCompanyData-2025-07-01-part1_7.csv')

df.columns = df.columns.str.strip()  # Remove leading/trailing spaces from column names

# Map pandas dtypes to SQLite types
def pandas_to_sqlite(dtype):
    if pd.api.types.is_integer_dtype(dtype):
        return 'INTEGER'
    elif pd.api.types.is_float_dtype(dtype):
        return 'REAL'
    elif pd.api.types.is_bool_dtype(dtype):
        return 'INTEGER'
    else:
        return 'TEXT'

columns_with_types = [f'"{col}" {pandas_to_sqlite(dtype)}' for col, dtype in df.dtypes.items()]

create_table_sql = f'CREATE TABLE IF NOT EXISTS companies (\n    {', '.join(columns_with_types)}\n);'
# print('Inferred CREATE TABLE statement:')
# print(create_table_sql)

# Create a SQLite connection
conn = sqlite3.connect("companies.db")
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS companies")

# Create the table
cur.execute(create_table_sql)
conn.commit()

# Truncate the table before loading new data
# cur.execute("DELETE FROM companies")
# conn.commit()

# Insert the data
for _, row in df.iterrows():
    placeholders = ', '.join(['?'] * len(row))
    columns = ', '.join([f'"{col}"' for col in row.index])
    sql = f'INSERT INTO companies ({columns}) VALUES ({placeholders})'
    cur.execute(sql, list(row.values))
conn.commit()
# read number of rows
cur.execute("SELECT COUNT(*) FROM companies")
print(cur.fetchone()[0])

cur.execute('SELECT COUNT(*) FROM companies WHERE "Accounts.AccountCategory" = "MICRO ENTITY"')
print(cur.fetchone()[0])
# Close the connection
conn.close()
