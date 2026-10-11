# Python 3.7 bundles SQLite 3.31, which allows only 999 variables per query
# (Python 3.8+ builds ship newer SQLite with a 32766 limit), so a large
# IN (...) list is queried in chunks.
SQLITE_IN_CHUNK_SIZE = 900


def query_all_in_chunks(query, column, values):
    """query.filter(column.in_(values)).all(), run in chunks of 900.

    Values are de-duplicated and sorted, so rows come back in the same id
    order a single IN query returns. An order_by on `query` applies within
    each chunk only, so callers that need a global order sort afterwards.
    """
    values = sorted(set(values))
    rows = []
    for start in range(0, len(values), SQLITE_IN_CHUNK_SIZE):
        rows.extend(query.filter(column.in_(values[start:start + SQLITE_IN_CHUNK_SIZE])).all())
    return rows
