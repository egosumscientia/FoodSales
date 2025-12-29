from sqlalchemy import text
from app.storage.db import engine

def next_order_serial():
    sql = """
    SELECT 'AIFS-' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || '-' ||
           LPAD((COUNT(*) + 1)::text, 4, '0')
    FROM orders
    WHERE DATE(created_at) = CURRENT_DATE;
    """
    with engine.begin() as conn:
        n = conn.execute(text(sql)).scalar_one()
    return n
