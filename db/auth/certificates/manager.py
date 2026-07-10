#!/usr/bin/env python3
"""
Certificate Manager for INDB
Generates and manages X.509 certificates for mTLS authentication
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

class CertificateManager:
    """Manages certificate generation and validation"""
    
    def __init__(self, certs_dir: str = "certs"):
        self.certs_dir = Path(certs_dir)
        self.ca_dir = self.certs_dir / "ca"
        self.server_dir = self.certs_dir / "server"
        self.clients_dir = self.certs_dir / "clients"
        
        # Create directories
        self.ca_dir.mkdir(parents=True, exist_ok=True)
        self.server_dir.mkdir(parents=True, exist_ok=True)
        self.clients_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_private_key(self) -> rsa.RSAPrivateKey:
        """Generate RSA private key"""
        return rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
    
    def save_private_key(self, key: rsa.RSAPrivateKey, filepath: Path):
        """Save private key to file"""
        with open(filepath, 'wb') as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        os.chmod(filepath, 0o600)  # Restrict permissions
    
    def save_certificate(self, cert: x509.Certificate, filepath: Path):
        """Save certificate to file"""
        with open(filepath, 'wb') as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    def generate_ca(self) -> tuple:
        """Generate Certificate Authority"""
        print("🔐 Generating Certificate Authority...")
        
        # Generate CA private key
        ca_key = self.generate_private_key()
        
        # Create CA certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "NL"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Zuid-Holland"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Rotterdam"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "INDB"),
            x509.NameAttribute(NameOID.COMMON_NAME, "INDB Root CA"),
        ])
        
        ca_cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            ca_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=3650)  # 10 years
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).sign(ca_key, hashes.SHA256(), default_backend())
        
        # Save CA key and certificate
        ca_key_path = self.ca_dir / "ca.key"
        ca_cert_path = self.ca_dir / "ca.crt"
        
        self.save_private_key(ca_key, ca_key_path)
        self.save_certificate(ca_cert, ca_cert_path)
        
        print(f"✅ CA certificate: {ca_cert_path}")
        print(f"✅ CA private key: {ca_key_path}")
        
        return ca_key, ca_cert
    
    def load_ca(self) -> tuple:
        """Load existing CA"""
        ca_key_path = self.ca_dir / "ca.key"
        ca_cert_path = self.ca_dir / "ca.crt"
        
        if not ca_key_path.exists() or not ca_cert_path.exists():
            raise FileNotFoundError("CA not found. Run generate_ca() first.")
        
        with open(ca_key_path, 'rb') as f:
            ca_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
        
        with open(ca_cert_path, 'rb') as f:
            ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())
        
        return ca_key, ca_cert
    
    def generate_server_cert(self, hostname: str = "localhost"):
        """Generate server certificate"""
        print(f"🔐 Generating server certificate for {hostname}...")
        
        # Load CA
        ca_key, ca_cert = self.load_ca()
        
        # Generate server private key
        server_key = self.generate_private_key()
        
        # Create server certificate
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "NL"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Zuid-Holland"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Rotterdam"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "INDB"),
            x509.NameAttribute(NameOID.COMMON_NAME, hostname),
        ])
        
        server_cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            ca_cert.subject
        ).public_key(
            server_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)  # 1 year
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(hostname),
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            ]),
            critical=False,
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_cert_sign=False,
                crl_sign=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).sign(ca_key, hashes.SHA256(), default_backend())
        
        # Save server key and certificate
        server_key_path = self.server_dir / "server.key"
        server_cert_path = self.server_dir / "server.crt"
        
        self.save_private_key(server_key, server_key_path)
        self.save_certificate(server_cert, server_cert_path)
        
        print(f"✅ Server certificate: {server_cert_path}")
        print(f"✅ Server private key: {server_key_path}")
    
    def generate_client_cert(self, client_name: str):
        """Generate client certificate"""
        print(f"🔐 Generating client certificate for '{client_name}'...")
        
        # Load CA
        ca_key, ca_cert = self.load_ca()
        
        # Generate client private key
        client_key = self.generate_private_key()
        
        # Create client certificate
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "NL"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Zuid-Holland"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Rotterdam"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "INDB"),
            x509.NameAttribute(NameOID.COMMON_NAME, client_name),
        ])
        
        client_cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            ca_cert.subject
        ).public_key(
            client_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)  # 1 year
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_cert_sign=False,
                crl_sign=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).sign(ca_key, hashes.SHA256(), default_backend())
        
        # Save client key and certificate
        client_key_path = self.clients_dir / f"{client_name}.key"
        client_cert_path = self.clients_dir / f"{client_name}.crt"
        
        self.save_private_key(client_key, client_key_path)
        self.save_certificate(client_cert, client_cert_path)
        
        print(f"✅ Client certificate: {client_cert_path}")
        print(f"✅ Client private key: {client_key_path}")
        
        return client_cert_path, client_key_path
    
    def setup_initial_certs(self):
        """Setup initial certificates (CA, server, backend client)"""
        print("\n" + "="*60)
        print("🚀 INDB Certificate Setup")
        print("="*60 + "\n")
        
        # Check if CA exists
        ca_exists = (self.ca_dir / "ca.crt").exists()
        
        if not ca_exists:
            # Generate CA
            self.generate_ca()
        else:
            print("ℹ️  CA already exists, skipping...")
        
        # Generate server certificate
        if not (self.server_dir / "server.crt").exists():
            self.generate_server_cert()
        else:
            print("ℹ️  Server certificate already exists, skipping...")
        
        # Generate backend service certificate
        if not (self.clients_dir / "backend-service.crt").exists():
            self.generate_client_cert("backend-service")
        else:
            print("ℹ️  Backend service certificate already exists, skipping...")
        
        print("\n" + "="*60)
        print("✅ Certificate setup complete!")
        print("="*60 + "\n")

# Add missing import
import ipaddress

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="INDB Certificate Manager")
    subparsers = parser.add_subparsers(dest='command')
    
    # Setup command
    parser_setup = subparsers.add_parser('setup', help='Setup initial certificates')
    
    # Generate CA
    parser_ca = subparsers.add_parser('generate-ca', help='Generate Certificate Authority')
    
    # Generate server cert
    parser_server = subparsers.add_parser('generate-server', help='Generate server certificate')
    parser_server.add_argument('--hostname', default='localhost', help='Server hostname')
    
    # Generate client cert
    parser_client = subparsers.add_parser('generate-client', help='Generate client certificate')
    parser_client.add_argument('--name', required=True, help='Client name')
    
    args = parser.parse_args()
    
    manager = CertificateManager()
    
    if args.command == 'setup':
        manager.setup_initial_certs()
    elif args.command == 'generate-ca':
        manager.generate_ca()
    elif args.command == 'generate-server':
        manager.generate_server_cert(args.hostname)
    elif args.command == 'generate-client':
        manager.generate_client_cert(args.name)
    else:
        parser.print_help()
