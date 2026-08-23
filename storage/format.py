"""
On-disk format constants and data locations.

Kept free of any core imports on purpose. The satellite stores (resonance graph,
causal graph, paradox) need these values, and importing them from storage.binary
pulled in core.encryption -> core -> core.indb -> back into storage.binary, which
fails whenever storage is imported before core.
"""
import os

# Header Format: MAGIC (4b) | VER (1b) | CRC32 (4b)
MAGIC = b'INDB'
FORMAT_VERSION = 1

# Use DATA_DIR for Docker/production deployments
DATA_DIR = os.getenv("DATA_DIR", ".")
KEY_FILE = os.path.join(DATA_DIR, "indb.key")
DB_FILE = os.path.join(DATA_DIR, "indb.bin")


def ensure_data_dir() -> None:
    """
    Create DATA_DIR before writing into it.

    Called from write paths rather than at import time: importing storage generates the
    master key on first run, and pointing DATA_DIR at a directory that does not exist yet
    used to abort the import — taking a third of the package down with it.
    """
    if DATA_DIR:
        os.makedirs(DATA_DIR, exist_ok=True)
