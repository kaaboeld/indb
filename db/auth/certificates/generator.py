"""
Certificate Generator for INDB
Generates self-signed certificates for development and testing.
"""

import os
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from typing import Tuple


class CertificateGenerator:
    """Generate self-signed TLS certificates for INDB."""
    
    CERT_DIR = "auth/certificates"
    CERT_FILE = "server.crt"
    KEY_FILE = "server.key"
    
    @staticmethod
    def generate_self_signed_cert(
        common_name: str = "localhost",
        organization: str = "INDB",
        validity_days: int = 365,
        key_size: int = 2048
    ) -> Tuple[str, str]:
        """
        Generate a self-signed certificate and private key.
        
        Args:
            common_name: Common Name (CN) for the certificate
            organization: Organization (O) name
            validity_days: Certificate validity period in days
            key_size: RSA key size in bits
            
        Returns:
            Tuple of (cert_path, key_path)
        """
        # Ensure directory exists
        os.makedirs(CertificateGenerator.CERT_DIR, exist_ok=True)
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        
        # Certificate subject and issuer (same for self-signed)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        
        # Build certificate
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=validity_days))
            .add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.DNSName("127.0.0.1"),
                    x509.DNSName("::1"),
                ]),
                critical=False,
            )
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .sign(private_key, hashes.SHA256(), backend=default_backend())
        )
        
        # Write certificate
        cert_path = os.path.join(CertificateGenerator.CERT_DIR, CertificateGenerator.CERT_FILE)
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        # Write private key
        key_path = os.path.join(CertificateGenerator.CERT_DIR, CertificateGenerator.KEY_FILE)
        with open(key_path, "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )
        
        print(f"✓ Generated self-signed certificate:")
        print(f"  Certificate: {cert_path}")
        print(f"  Private Key: {key_path}")
        print(f"  Valid for: {validity_days} days")
        print(f"  Common Name: {common_name}")
        
        return cert_path, key_path
    
    @staticmethod
    def get_cert_paths() -> Tuple[str, str]:
        """
        Get paths to existing certificate and key.
        Generates new ones if they don't exist.
        
        Returns:
            Tuple of (cert_path, key_path)
        """
        cert_path = os.path.join(CertificateGenerator.CERT_DIR, CertificateGenerator.CERT_FILE)
        key_path = os.path.join(CertificateGenerator.CERT_DIR, CertificateGenerator.KEY_FILE)
        
        if not os.path.exists(cert_path) or not os.path.exists(key_path):
            print("⚠️  TLS certificates not found. Generating new self-signed certificates...")
            return CertificateGenerator.generate_self_signed_cert()
        
        return cert_path, key_path
    
    @staticmethod
    def verify_cert_validity(cert_path: str) -> bool:
        """
        Check if certificate is still valid.
        
        Args:
            cert_path: Path to certificate file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            with open(cert_path, "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read(), default_backend())
            
            now = datetime.utcnow()
            return cert.not_valid_before <= now <= cert.not_valid_after
        except Exception as e:
            print(f"Certificate validation error: {e}")
            return False


if __name__ == "__main__":
    # Generate certificate when run directly
    CertificateGenerator.generate_self_signed_cert()
