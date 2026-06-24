"""
Storage layer for INDB

Binary storage, encryption, and migrations.
"""

from storage.binary import load_decrypted, save_encrypted

__all__ = ['load_decrypted', 'save_encrypted']
