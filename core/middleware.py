"""
System Middleware

Implements critical cross-cutting concerns:
1. Response Signing (Security)
2. Metrics (Observability)
"""

import time
import json
import sys
import base64
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.datastructures import MutableHeaders
from fastapi import Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from core.encryption import PayloadEncryptor
from core.config import config
from core.signing import compute_key_id

# Prometheus Metrics
REQUEST_COUNT = Counter(
    "indb_requests_total",
    "Total Request Count",
    ["method", "endpoint", "status_code"]
)
REQUEST_LATENCY = Histogram(
    "indb_request_duration_seconds",
    "Request duration seconds",
    ["endpoint"]
)

class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Prometheus metrics middleware.
    Tracks request count and latency.
    """
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Handle /metrics separately to avoid infinite loop
        if request.url.path == "/metrics":
            return await call_next(request)
            
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
        except Exception as e:
            status_code = "500"
            raise e
        finally:
            process_time = time.time() - start_time
            endpoint = request.url.path
            
            # Record metrics
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()
            
            REQUEST_LATENCY.labels(endpoint=endpoint).observe(process_time)
            
        return response

class ResponseSigningMiddleware(BaseHTTPMiddleware):
    """
    Signs API responses using Ed25519.
    
    NOTE: In a real system, the private key would be securely loaded from a vault.
    Here we generate a static one for demonstration purposes or load from env.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        if config.SIGNING_PRIVATE_KEY:
            raw = base64.b64decode(config.SIGNING_PRIVATE_KEY)
            self.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(raw)
            sys.stderr.write("INFO: ResponseSigningMiddleware loaded stable signing key from SIGNING_PRIVATE_KEY\n")
        else:
            self.private_key = ed25519.Ed25519PrivateKey.generate()
            sys.stderr.write(
                "WARNING: SIGNING_PRIVATE_KEY not set — ephemeral key generated. "
                "Signatures will not survive restarts.\n"
            )
        self.public_key = self.private_key.public_key()

        pub_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        self.public_key_b64 = base64.b64encode(pub_bytes).decode('utf-8')

    async def dispatch(self, request: Request, call_next):
        # Only sign API responses
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
            
        response = await call_next(request)
        
        # Signed on success for both wire formats. Leaving msgpack unsigned would make the
        # guarantee depend on the Accept header, which is not a guarantee.
        content_type = response.headers.get("content-type", "")
        is_json = "application/json" in content_type
        is_msgpack = "msgpack" in content_type
        if response.status_code == 200 and (is_json or is_msgpack):
            # Consume the response body
            # If the response is a known Starlette Response, it often has .body set
            if hasattr(response, "body") and response.body:
                full_body = response.body
            else:
                body_bytes = [section async for section in response.body_iterator]
                full_body = b"".join(body_bytes)

            try:
                data = json.loads(full_body) if is_json else None
                
                # Check if already signed (avoid double signing)
                if isinstance(data, dict) and "signature" in data:
                     return Response(
                        content=full_body,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type
                    )

                # JSON is signed in canonical form, so a client that reserialises the body
                # can still recompute the message. msgpack is signed as the exact bytes on
                # the wire, since there is no second canonical form to agree on.
                message = (
                    json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')
                    if is_json
                    else full_body
                )
                signature = self.private_key.sign(message)
                signature_b64 = base64.b64encode(signature).decode('utf-8')
                
                key_id = compute_key_id(self.public_key_b64)
                signed_at = time.time()

                # Prepare new headers
                new_headers = dict(response.headers)
                new_headers.pop("content-length", None)
                new_headers.pop("Content-Length", None)

                if isinstance(data, dict):
                    data['signature'] = {
                        "algorithm": "Ed25519",
                        "public_key": self.public_key_b64,
                        "signature": signature_b64,
                        "key_id": key_id,
                        "timestamp": signed_at
                    }
                    new_body = json.dumps(data).encode('utf-8')
                else:
                    # Arrays, scalars (e.g. /export/json) and msgpack bodies have nowhere to
                    # hold a signature block, so the body is left byte-identical and the
                    # signature travels in headers over the message described above.
                    new_body = full_body
                    new_headers.update({
                        "X-INDB-Signature-Algorithm": "Ed25519",
                        "X-INDB-Public-Key": self.public_key_b64,
                        "X-INDB-Signature": signature_b64,
                        "X-INDB-Key-Id": key_id,
                        "X-INDB-Signed-At": str(signed_at),
                    })
                
                # Create new response
                new_response = Response(
                    content=new_body,
                    status_code=response.status_code,
                    headers=new_headers,
                    media_type=response.media_type
                )
                
                # We must explicitly set Content-Length because Response init might not update it automatically
                # if we provide bytes causing header mismatch if we just copy headers.
                # So we update it.
                new_response.headers["Content-Length"] = str(len(new_body))
                
                return new_response
                
            except Exception as e:
                sys.stderr.write(f"ERROR: Signing failed: {e}\n")
                # Fallback on error (return original)
                # If we consumed iterator, we MUST return a new response with the body
                return Response(
                    content=full_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
                
        # For non-JSON or streaming, we just pass through
        return response

class EncryptionMiddleware(BaseHTTPMiddleware):
    """
    Transparent E2E Encryption Middleware.
    
    If 'X-Encryption-Key' header is present (Base64 32-byte key):
    1. Decrypts incoming request body.
    2. Encrypts outgoing response body.
    """
    
    async def dispatch(self, request: Request, call_next):
        key_b64 = request.headers.get("X-Encryption-Key")
        if not key_b64:
            return await call_next(request)
            
        try:
            key = base64.b64decode(key_b64)
            if len(key) != 32:
                return Response("Invalid Key Length", status_code=400)
                
            # 1. Decrypt Request (if body exists)
            body = await request.body()
            if body:
                try:
                    payload = json.loads(body)
                    if "encrypted_payload" in payload:
                        decrypted = PayloadEncryptor.decrypt(payload, key)
                        # Replace body with decrypted content for next handlers
                        # We need to hack the request receive to return decrypted bytes
                        new_body = json.dumps(decrypted).encode('utf-8')
                        
                        async def new_receive():
                            return {"type": "http.request", "body": new_body, "more_body": False}
                            
                        request = Request(request.scope, new_receive)
                except Exception as e:
                    return Response(f"Decryption Failed: {str(e)}", status_code=400)

            # 2. Process Request
            response = await call_next(request)
            
            # 3. Encrypt Response
            # Only encrypt successful JSON responses
            if response.status_code == 200 and "application/json" in response.headers.get("content-type", ""):
                if hasattr(response, "body") and response.body:
                    resp_body = response.body
                else:
                    resp_body = b"".join([section async for section in response.body_iterator])
                
                data = json.loads(resp_body)
                encrypted = PayloadEncryptor.encrypt(data, key)
                
                new_resp_body = json.dumps(encrypted).encode('utf-8')
                
                new_headers = dict(response.headers)
                new_headers.pop("content-length", None)
                new_headers.pop("Content-Length", None)
                
                new_response = Response(
                    content=new_resp_body,
                    status_code=response.status_code,
                    headers=new_headers,
                    media_type="application/json"
                )
                new_response.headers["Content-Length"] = str(len(new_resp_body))
                return new_response
                
            return response
            
        except Exception as e:
            return Response(f"Encryption Middleware Error: {str(e)}", status_code=500)

class BrotliMiddleware(BaseHTTPMiddleware):
    """
    Middleware for Brotli compression.
    Fallback to Gzip if Brotli not accepted by client.
    """
    def __init__(self, app: ASGIApp, minimum_size: int = 500, quality: int = 4):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.quality = quality

    async def dispatch(self, request: Request, call_next):
        accept_encoding = request.headers.get("Accept-Encoding", "")
        
        # If client doesn't support br, pass through (GZipMiddleware might catch it if stacked)
        if "br" not in accept_encoding:
            return await call_next(request)
            
        response = await call_next(request)
        
        if response.status_code < 200 or response.status_code >= 300:
            return response
            
        content_type = response.headers.get("content-type", "")
        if "text/" not in content_type and "application/" not in content_type:
             return response

        # Check existing encoding
        if "content-encoding" in response.headers:
            return response

        # Compress
        try:
            if hasattr(response, "body") and response.body:
                content = response.body
            else:
                content = b"".join([section async for section in response.body_iterator])
                
            if len(content) < self.minimum_size:
                return Response(
                    content=content,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
                
            import brotli
            compressed = brotli.compress(content, quality=self.quality)
            
            import brotli
            compressed = brotli.compress(content, quality=self.quality)
            
            new_headers = dict(response.headers)
            new_headers.pop("content-length", None)
            new_headers.pop("Content-Length", None)
            new_headers["Content-Encoding"] = "br"
            new_headers["Content-Length"] = str(len(compressed))
            new_headers["Vary"] = "Accept-Encoding"
            
            return Response(
                content=compressed,
                status_code=response.status_code,
                headers=new_headers,
                media_type=response.media_type
            )
        except Exception:
            # Fallback
            return response

def metrics_endpoint(request: Request):
    """Expose Prometheus metrics."""
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
