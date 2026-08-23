"""
On-disk format tests for INDB.

The store is a single binary contract: MAGIC | VERSION | CRC32 | AES-256-GCM payload, at
DATA_DIR/indb.bin. Every engine that touches it — synchronous, async, mmap — has to agree
on both the frame and the location, or a write lands somewhere no reader looks.
"""

import asyncio
import struct
import zlib

import pytest

import storage.async_binary as async_binary
import storage.binary as binary

EVENT = {
    "id": "format-test",
    "timestamp": 1770018600.0,
    "raw_data_anchor": ["quay", "fog"],
    "location": "harbour/berth-9",
}


@pytest.fixture
def store(tmp_path, monkeypatch):
    """An isolated store file, shared by both engines exactly as it is in production."""
    path = str(tmp_path / "indb.bin")
    monkeypatch.setattr(binary, "DB_FILE", path)
    monkeypatch.setattr(async_binary, "DB_FILE", path)
    return path


def test_every_engine_reads_the_same_location():
    """A relative path here would write beside the process instead of into the volume."""
    from storage import format as fmt
    from storage import mmap_store

    assert binary.DB_FILE == fmt.DB_FILE
    assert async_binary.DB_FILE == fmt.DB_FILE
    assert mmap_store.DB_FILE == fmt.DB_FILE
    assert async_binary.KEY_FILE == fmt.KEY_FILE


def test_written_frame_carries_magic_version_and_crc(store):
    binary.save_encrypted([EVENT])

    with open(store, "rb") as handle:
        raw = handle.read()

    magic, version, crc = struct.unpack(">4sBI", raw[:9])
    assert magic == binary.MAGIC
    assert version == binary.FORMAT_VERSION
    assert crc == zlib.crc32(raw[9:]) & 0xFFFFFFFF


def test_sync_write_is_readable_by_the_async_engine(store):
    binary.save_encrypted([EVENT])

    events = asyncio.run(async_binary.load_decrypted_async(binary.MASTER_KEY))

    assert [e.location for e in events] == [EVENT["location"]]


def test_async_write_is_readable_by_the_sync_engine(store):
    asyncio.run(async_binary.save_encrypted_async([EVENT], binary.MASTER_KEY))

    events = binary.load_decrypted()

    assert [e.location for e in events] == [EVENT["location"]]


def test_store_without_header_is_refused_rather_than_read_as_empty(store):
    """
    The dangerous failure mode: reporting [] for a file that holds data.

    Memory would start empty and the first persist would replace the file, so an
    unreadable store has to stop the process instead.
    """
    binary.save_encrypted([EVENT])
    with open(store, "rb") as handle:
        framed = handle.read()
    with open(store, "wb") as handle:
        handle.write(framed[9:])

    with pytest.raises(ValueError, match="CRITICAL"):
        binary.load_decrypted()

    assert binary.verify_integrity()["valid"] is False


def test_corrupted_payload_is_refused_by_both_engines(store):
    binary.save_encrypted([EVENT])
    with open(store, "r+b") as handle:
        handle.seek(9)
        handle.write(b"\x00\x00\x00\x00")

    with pytest.raises(ValueError, match="CRITICAL"):
        binary.load_decrypted()

    # The async engine logs and returns [], but it must not hand back a decrypted event.
    assert asyncio.run(async_binary.load_decrypted_async(binary.MASTER_KEY)) == []


def test_empty_file_is_an_empty_store(store):
    """Nothing written yet is a legitimate state and must not raise."""
    open(store, "wb").close()

    assert binary.load_decrypted() == []
