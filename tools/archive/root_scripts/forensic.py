import hashlib
import os

class ForensicValidator:
    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """
        Calculates SHA-256 hash of a file on the server.
        Must match the Mobile App's implementation exactly.
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read in 4K chunks to be memory efficient
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def verify_integrity(uploaded_path: str, claimed_hash: str) -> bool:
        """
        The Judge: Compares calculated hash vs claimed hash.
        """
        calculated = ForensicValidator.calculate_file_hash(uploaded_path)
        return calculated == claimed_hash
