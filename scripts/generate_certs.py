#!/usr/bin/env python3
"""
Generate Development Certificates for INDB mTLS
"""

from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime
import ipaddress

def generate_key():
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

def save_key(key, path):
    with open(path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

def save_cert(cert, path):
    with open(path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

def generate_self_signed_ca():
    key = generate_key()
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"INDB Dev CA"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    return key, cert

def generate_cert(ca_key, ca_cert, name, common_name, san_dns=None, san_ip=None):
    key = generate_key()
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
    )
    
    san_list = []
    if san_dns:
        for dns in san_dns:
            san_list.append(x509.DNSName(dns))
    if san_ip:
        for ip in san_ip:
            san_list.append(x509.IPAddress(ipaddress.ip_address(ip)))
            
    if san_list:
        builder = builder.add_extension(
            x509.SubjectAlternativeName(san_list),
            critical=False,
        )
        
    cert = builder.sign(ca_key, hashes.SHA256())
    return key, cert

def main():
    base_dir = Path("certs")
    base_dir.mkdir(exist_ok=True)
    (base_dir / "ca").mkdir(exist_ok=True)
    (base_dir / "server").mkdir(exist_ok=True)
    (base_dir / "clients").mkdir(exist_ok=True)

    print("🔑 Generating CA...")
    ca_key, ca_cert = generate_self_signed_ca()
    save_key(ca_key, base_dir / "ca/ca.key")
    save_cert(ca_cert, base_dir / "ca/ca.crt")
    
    print("🖥️  Generating Server Cert...")
    srv_key, srv_cert = generate_cert(
        ca_key, ca_cert, "server", u"localhost", 
        san_dns=[u"localhost", u"indb-api"], 
        san_ip=[u"127.0.0.1", u"0.0.0.0"]
    )
    save_key(srv_key, base_dir / "server/server.key")
    save_cert(srv_cert, base_dir / "server/server.crt")
    
    print("📱 Generating Client Cert (Backend Service)...")
    client_key, client_cert = generate_cert(ca_key, ca_cert, "client", u"indb-admin")
    save_key(client_key, base_dir / "clients/backend-service.key")
    save_cert(client_cert, base_dir / "clients/backend-service.crt")
    
    print("✅ Certificates generated in certs/")

if __name__ == "__main__":
    main()
