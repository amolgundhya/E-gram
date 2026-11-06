# Pickler for SQLAlchemy PickleType columns, shared by Windows 7/8 (Python 3.7)
# and Windows 10 (Python 3.8+) builds that use the same database.
# - dumps: PickleType passes protocol=4, which Python 3.7 can read.
# - loads: Python 3.7's pickle cannot read protocol 5 (Python 3.8+ default),
#   so use the pickle5 backport when it is installed.
try:
    import pickle5 as _pickle
except ImportError:
    import pickle as _pickle

PROTOCOL = 4


def dumps(obj, protocol=PROTOCOL):
    return _pickle.dumps(obj, protocol)


def loads(data):
    return _pickle.loads(data)
