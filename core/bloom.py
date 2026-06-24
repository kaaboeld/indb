"""
Bloom Filter for Fast Duplicate Detection
Probabilistic data structure for membership testing.
No false negatives, low false positive rate.
"""

import hashlib
import math
from typing import Any


class BloomFilter:
    """
    Space-efficient probabilistic data structure for set membership testing.
    Used for fast duplicate detection in INDB fusion engine.
    """
    
    def __init__(self, expected_elements: int = 10000, false_positive_rate: float = 0.01):
        """
        Initialize Bloom filter.
        
        Args:
            expected_elements: Expected number of elements
            false_positive_rate: Desired false positive rate (0.01 = 1%)
        """
        self.expected_elements = expected_elements
        self.false_positive_rate = false_positive_rate
        
        # Calculate optimal bit array size
        self.size = self._optimal_size(expected_elements, false_positive_rate)
        
        # Calculate optimal number of hash functions
        self.num_hashes = self._optimal_hash_count(self.size, expected_elements)
        
        # Bit array (using bytearray for efficiency)
        self.bit_array = bytearray(math.ceil(self.size / 8))
        
        # Element count
        self.count = 0
    
    @staticmethod
    def _optimal_size(n: int, p: float) -> int:
        """
        Calculate optimal bit array size.
        Formula: m = -(n * ln(p)) / (ln(2)^2)
        """
        m = -(n * math.log(p)) / (math.log(2) ** 2)
        return int(math.ceil(m))
    
    @staticmethod
    def _optimal_hash_count(m: int, n: int) -> int:
        """
        Calculate optimal number of hash functions.
        Formula: k = (m/n) * ln(2)
        """
        k = (m / n) * math.log(2)
        return max(1, int(math.ceil(k)))
    
    def _hashes(self, item: str) -> list[int]:
        """
        Generate multiple hash values for an item.
        Uses double hashing technique for efficiency.
        """
        # Primary hash (SHA256)
        h1 = int(hashlib.sha256(item.encode()).hexdigest(), 16)
        
        # Secondary hash (MD5)
        h2 = int(hashlib.md5(item.encode()).hexdigest(), 16)
        
        # Generate k hash values using double hashing
        hashes = []
        for i in range(self.num_hashes):
            hash_val = (h1 + i * h2) % self.size
            hashes.append(hash_val)
        
        return hashes
    
    def add(self, item: Any) -> None:
        """
        Add item to Bloom filter.
        
        Args:
            item: Item to add (will be converted to string)
        """
        item_str = str(item)
        
        for hash_val in self._hashes(item_str):
            # Set bit at position hash_val
            byte_index = hash_val // 8
            bit_index = hash_val % 8
            self.bit_array[byte_index] |= (1 << bit_index)
        
        self.count += 1
    
    def contains(self, item: Any) -> bool:
        """
        Check if item might be in the set.
        
        Args:
            item: Item to check
            
        Returns:
            True if item might be in set (possible false positive)
            False if item is definitely not in set (no false negatives)
        """
        item_str = str(item)
        
        for hash_val in self._hashes(item_str):
            # Check bit at position hash_val
            byte_index = hash_val // 8
            bit_index = hash_val % 8
            
            if not (self.bit_array[byte_index] & (1 << bit_index)):
                return False
        
        return True
    
    def clear(self) -> None:
        """Clear the Bloom filter."""
        self.bit_array = bytearray(math.ceil(self.size / 8))
        self.count = 0
    
    def estimated_fpr(self) -> float:
        """
        Estimate current false positive rate.
        Formula: (1 - e^(-kn/m))^k
        """
        if self.count == 0:
            return 0.0
        
        exponent = -self.num_hashes * self.count / self.size
        fpr = (1 - math.exp(exponent)) ** self.num_hashes
        return fpr
    
    def stats(self) -> dict:
        """Get Bloom filter statistics."""
        return {
            "size_bits": self.size,
            "size_bytes": len(self.bit_array),
            "num_hashes": self.num_hashes,
            "elements": self.count,
            "capacity": self.expected_elements,
            "target_fpr": self.false_positive_rate,
            "estimated_fpr": round(self.estimated_fpr(), 4),
            "fill_ratio": round(self.count / self.expected_elements, 2),
        }
    
    def __len__(self) -> int:
        """Return number of elements added."""
        return self.count
    
    def __contains__(self, item: Any) -> bool:
        """Support 'in' operator."""
        return self.contains(item)


# Global Bloom filter for deduplication
dedup_filter = BloomFilter(expected_elements=100000, false_positive_rate=0.001)


def check_duplicate(item: Any) -> bool:
    """
    Check if item is likely a duplicate.
    
    Returns:
        True if item might be duplicate
        False if item is definitely new
    """
    return item in dedup_filter


def mark_seen(item: Any) -> None:
    """Mark item as seen in deduplication filter."""
    dedup_filter.add(item)


def reset_dedup_filter() -> None:
    """Clear deduplication filter."""
    dedup_filter.clear()
