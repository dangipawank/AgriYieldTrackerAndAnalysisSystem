from sqlalchemy import select, insert
from models import (
    engine,
    raw_yield_data,
    yielddata
)
print("Etl starting")
with engine.connect() as conn:

  #Extract data from raw_yield_data
  query=select(raw_yield_data)
  result=conn.execute(query)

  raw_records=result.fetchall()
  print(f"Found {len(raw_records)} raw records") 