# TLS/SSL Configuration Guide

## Overview

INDB now supports TLS/SSL encryption for all HTTP/WebSocket traffic using self-signed certificates.

## Quick Start

### Enable SSL
```bash
export INDB_USE_SSL=true
./start.sh
```

Access at: `https://localhost:8000`

### Disable SSL (Default)
```bash
export INDB_USE_SSL=false
./start.sh
```

Access at: `http://localhost:8000`

## Certificate Management

### Automatic Generation
Certificates are automatically generated on first run if they don't exist:
- **Location**: `auth/certificates/`
- **Files**: `server.crt`, `server.key`
- **Algorithm**: RSA-2048
- **Hash**: SHA-256
- **Validity**: 365 days
- **Subject Alternative Names**: localhost, 127.0.0.1, ::1

### Manual Generation
```bash
cd backend
python3 -m auth.certificates.generator
```

### Certificate Renewal
Certificates are automatically checked for validity on startup. If expired, new ones are generated.

## Production Deployment

### Using Let's Encrypt
For production, use real certificates from Let's Encrypt:

```bash
# Install certbot
sudo apt-get install certbot

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com

# Configure INDB
export INDB_USE_SSL=true
export INDB_SSL_CERT=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
export INDB_SSL_KEY=/etc/letsencrypt/live/yourdomain.com/privkey.pem
```

Update `launcher.py` to use environment variables for cert paths.

### Behind Reverse Proxy
If using nginx/Apache, handle SSL there and disable in INDB:

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

```bash
export INDB_USE_SSL=false
./start.sh
```

## Security Considerations

### Self-Signed Certificates
⚠️ **Warning**: Self-signed certificates are for development only!

Browsers will show security warnings. To bypass:
- Chrome: Type `thisisunsafe` on warning page
- Firefox: Click "Advanced" → "Accept Risk"
- curl: Use `-k` or `--insecure` flag

### Production Certificates
For production, always use certificates from a trusted CA:
- Let's Encrypt (free)
- DigiCert
- Comodo
- GlobalSign

### Certificate Pinning
For high-security deployments, implement certificate pinning in clients.

## Testing

### Test HTTPS Endpoint
```bash
# With self-signed cert
curl -k https://localhost:8000/health

# With valid cert
curl https://yourdomain.com/health
```

### Test WebSocket over TLS
```bash
wscat -c wss://localhost:8000/ws --no-check
```

### Verify Certificate
```bash
openssl x509 -in auth/certificates/server.crt -text -noout
```

## Troubleshooting

### Certificate Not Found
```
Error: SSL certificate not found
```
**Solution**: Run `python3 -m auth.certificates.generator`

### Permission Denied
```
Error: Permission denied: auth/certificates/server.key
```
**Solution**: `chmod 600 auth/certificates/server.key`

### Certificate Expired
```
Warning: Certificate expired. Generating new one...
```
**Solution**: Automatic - new cert will be generated

### Browser Security Warning
```
NET::ERR_CERT_AUTHORITY_INVALID
```
**Solution**: Normal for self-signed certs. Click "Advanced" → "Proceed"

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `INDB_USE_SSL` | `false` | Enable/disable SSL |
| `INDB_SSL_CERT` | `auth/certificates/server.crt` | Certificate path |
| `INDB_SSL_KEY` | `auth/certificates/server.key` | Private key path |
| `PORT` | `8003` | Server port |

## Next Steps

- [ ] Add TLS to gRPC server
- [ ] Add DTLS to UDP server
- [ ] Implement mTLS (mutual TLS)
- [ ] Add certificate rotation
- [ ] Integrate with HashiCorp Vault
