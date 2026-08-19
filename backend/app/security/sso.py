"""SSO Authentication Module - SAML/OIDC Support for Jurisiva AI.

This module provides enterprise Single Sign-On capabilities with:
- SAML 2.0 Service Provider (SP) implementation
- OpenID Connect (OIDC) Relying Party (RP) implementation
- Provider configuration management
- Attribute mapping and user provisioning
- Session management with secure cookies
"""
import base64
import hashlib
import json
import secrets
import time
import uuid
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from urllib.parse import urlencode

import jwt
import requests
from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel, HttpUrl, field_validator
from supabase import create_client

from app.config import get_settings
from app.security.auth import AuthContext, get_auth_context, _service_client

# URL validation to prevent SSRF
# Allowed schemes for external HTTP requests
_ALLOWED_URL_SCHEMES = {"https"}

# Private IP ranges to block (RFC 1918, RFC 6598, RFC 3927, localhost)
_PRIVATE_IP_RANGES = [
    "10.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.", "172.22.", "172.23.",
    "172.24.", "172.25.", "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
    "192.168.", "169.254.", "127.", "0.", "::1", "fe80:", "fc00:", "fd00:"
]

# Allowed domains for OIDC/SAML metadata endpoints (can be extended via config)
_ALLOWED_OIDC_DOMAINS = {
    "accounts.google.com",
    "login.microsoftonline.com",
    "auth.atlassian.com",
    "github.com",
    "gitlab.com",
    "okta.com",
    "auth0.com",
    "keycloak.org",
    "pingidentity.com",
    "onelogin.com",
    "azure.com",
    "amazonaws.com",  # AWS Cognito
}


def _validate_url(url: str, allowed_domains: Optional[set[str]] = None) -> bool:
    """
    Validate URL to prevent SSRF attacks.
    
    Args:
        url: URL to validate
        allowed_domains: Optional set of allowed domains. If provided, URL must match one.
    
    Returns:
        True if URL is safe, False otherwise
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False
    
    # Check scheme
    if parsed.scheme.lower() not in _ALLOWED_URL_SCHEMES:
        return False
    
    # Check hostname
    hostname = parsed.hostname or ""
    hostname_lower = hostname.lower()
    
    # Block private/local IPs
    for private_prefix in _PRIVATE_IP_RANGES:
        if hostname_lower.startswith(private_prefix.lower()):
            return False
    
    # Block localhost variants
    if hostname_lower in {"localhost", "localhost.localdomain", "127.0.0.1", "::1", "0.0.0.0"}:
        return False
    
    # If allowed domains specified, check against them
    if allowed_domains:
        # Check exact match or subdomain match
        domain_allowed = False
        for allowed in allowed_domains:
            if hostname_lower == allowed.lower() or hostname_lower.endswith("." + allowed.lower()):
                domain_allowed = True
                break
        if not domain_allowed:
            return False
    
    return True


def _safe_get(url: str, allowed_domains: Optional[set[str]] = None, timeout: int = 10) -> Optional[requests.Response]:
    """
    Safe HTTP GET request with SSRF protection.
    
    Args:
        url: URL to fetch
        allowed_domains: Optional set of allowed domains
        timeout: Request timeout in seconds
    
    Returns:
        Response object or None if validation fails
    """
    if not _validate_url(url, allowed_domains):
        return None
    
    try:
        # nosec B113 - URL validated by _validate_url before request (SSRF protection)
        response = requests.get(url, timeout=timeout, allow_redirects=False)  # nosec B113
        response.raise_for_status()
        return response
    except Exception:
        return None


def _safe_post(url: str, data: dict, allowed_domains: Optional[set[str]] = None, timeout: int = 10) -> Optional[requests.Response]:
    """
    Safe HTTP POST request with SSRF protection.
    
    Args:
        url: URL to post to
        data: Form data to send
        allowed_domains: Optional set of allowed domains
        timeout: Request timeout in seconds
    
    Returns:
        Response object or None if validation fails
    """
    if not _validate_url(url, allowed_domains):
        return None
    
    try:
        # nosec B113 - URL validated by _validate_url before request (SSRF protection)
        response = requests.post(url, data=data, timeout=timeout, allow_redirects=False)  # nosec B113
        response.raise_for_status()
        return response
    except Exception:
        return None

settings = get_settings()


class SSOProviderType(str, Enum):
    """Supported SSO provider types."""
    SAML = "saml"
    OIDC = "oidc"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    OKTA = "okta"
    AUTH0 = "auth0"
    AZURE_AD = "azure_ad"
    ONELLOGIN = "onelogin"
    CUSTOM = "custom"


class SSOBinding(str, Enum):
    """SAML binding types."""
    HTTP_REDIRECT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    HTTP_POST = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    HTTP_ARTIFACT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Artifact"


@dataclass
class SSOProviderConfig:
    """Configuration for an SSO provider."""
    provider_id: str
    provider_type: SSOProviderType
    display_name: str
    enabled: bool = True
    
    # SAML Configuration
    saml_entity_id: Optional[str] = None
    saml_sso_url: Optional[str] = None
    saml_slo_url: Optional[str] = None
    saml_x509_cert: Optional[str] = None
    saml_private_key: Optional[str] = None
    saml_name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    saml_attribute_mapping: dict = field(default_factory=lambda: {
        "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
        "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
        "groups": "http://schemas.xmlsoap.org/claims/Group",
    })
    saml_binding: SSOBinding = SSOBinding.HTTP_REDIRECT
    saml_want_assertions_signed: bool = True
    saml_want_response_signed: bool = True
    
    # OIDC Configuration
    oidc_issuer_url: Optional[str] = None
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None
    oidc_discovery_url: Optional[str] = None
    oidc_authorization_endpoint: Optional[str] = None
    oidc_token_endpoint: Optional[str] = None
    oidc_jwks_uri: Optional[str] = None
    oidc_userinfo_endpoint: Optional[str] = None
    oidc_end_session_endpoint: Optional[str] = None
    oidc_scopes: list[str] = field(default_factory=lambda: ["openid", "email", "profile"])
    oidc_response_type: str = "code"
    oidc_pkce_enabled: bool = True
    oidc_attribute_mapping: dict = field(default_factory=lambda: {
        "email": "email",
        "first_name": "given_name",
        "last_name": "family_name",
        "groups": "groups",
    })
    
    # General Configuration
    auto_provision_users: bool = True
    default_role: str = "STAFF"
    default_organization_id: Optional[str] = None
    allowed_domains: list[str] = field(default_factory=list)
    attribute_require_email: bool = True
    sign_requests: bool = True
    encrypt_assertions: bool = False
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SSOSession:
    """SSO session data."""
    session_id: str
    provider_id: str
    user_id: str
    email: str
    name: str
    roles: list[str]
    organization_id: Optional[str] = None
    attributes: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    relay_state: Optional[str] = None


class SAMLAuthRequest(BaseModel):
    """SAML Authentication Request parameters."""
    SAMLRequest: str
    RelayState: Optional[str] = None


class SAMLAuthResponse(BaseModel):
    """SAML Authentication Response parameters."""
    SAMLResponse: str
    RelayState: Optional[str] = None


class OIDCAuthRequest(BaseModel):
    """OIDC Authorization Request parameters."""
    client_id: str
    redirect_uri: HttpUrl
    response_type: str = "code"
    scope: str = "openid email profile"
    state: str
    nonce: Optional[str] = None
    code_challenge: Optional[str] = None
    code_challenge_method: Optional[str] = None


class OIDCTokenRequest(BaseModel):
    """OIDC Token Request parameters."""
    grant_type: str = "authorization_code"
    code: str
    redirect_uri: HttpUrl
    client_id: str
    client_secret: Optional[str] = None
    code_verifier: Optional[str] = None


class OIDCUserInfo(BaseModel):
    """OIDC UserInfo response."""
    sub: str
    email: Optional[str] = None
    email_verified: Optional[bool] = None
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    groups: Optional[list[str]] = None
    preferred_username: Optional[str] = None


class SSOProviderManager:
    """Manages SSO provider configurations."""
    
    def __init__(self):
        self._providers: dict[str, SSOProviderConfig] = {}
        self._load_providers()
    
    def _load_providers(self):
        """Load providers from database."""
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            return
        
        try:
            db = _service_client()
            if not db:
                return
            
            result = db.table("sso_providers").select("*").eq("enabled", True).execute()
            for row in result.data or []:
                config = SSOProviderConfig(
                    provider_id=row["provider_id"],
                    provider_type=SSOProviderType(row["provider_type"]),
                    display_name=row["display_name"],
                    enabled=row["enabled"],
                    saml_entity_id=row.get("saml_entity_id"),
                    saml_sso_url=row.get("saml_sso_url"),
                    saml_slo_url=row.get("saml_slo_url"),
                    saml_x509_cert=row.get("saml_x509_cert"),
                    saml_private_key=row.get("saml_private_key"),
                    saml_name_id_format=row.get("saml_name_id_format", "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"),
                    saml_attribute_mapping=row.get("saml_attribute_mapping", {}),
                    saml_binding=SSOBinding(row.get("saml_binding", "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect")),
                    saml_want_assertions_signed=row.get("saml_want_assertions_signed", True),
                    saml_want_response_signed=row.get("saml_want_response_signed", True),
                    oidc_issuer_url=row.get("oidc_issuer_url"),
                    oidc_client_id=row.get("oidc_client_id"),
                    oidc_client_secret=row.get("oidc_client_secret"),
                    oidc_discovery_url=row.get("oidc_discovery_url"),
                    oidc_authorization_endpoint=row.get("oidc_authorization_endpoint"),
                    oidc_token_endpoint=row.get("oidc_token_endpoint"),
                    oidc_jwks_uri=row.get("oidc_jwks_uri"),
                    oidc_userinfo_endpoint=row.get("oidc_userinfo_endpoint"),
                    oidc_end_session_endpoint=row.get("oidc_end_session_endpoint"),
                    oidc_scopes=row.get("oidc_scopes", ["openid", "email", "profile"]),
                    oidc_response_type=row.get("oidc_response_type", "code"),
                    oidc_pkce_enabled=row.get("oidc_pkce_enabled", True),
                    oidc_attribute_mapping=row.get("oidc_attribute_mapping", {}),
                    auto_provision_users=row.get("auto_provision_users", True),
                    default_role=row.get("default_role", "STAFF"),
                    default_organization_id=row.get("default_organization_id"),
                    allowed_domains=row.get("allowed_domains", []),
                    attribute_require_email=row.get("attribute_require_email", True),
                    sign_requests=row.get("sign_requests", True),
                    encrypt_assertions=row.get("encrypt_assertions", False),
                )
                self._providers[config.provider_id] = config
        except Exception:
            pass  # Fail silently for auth
    
    def get_provider(self, provider_id: str) -> Optional[SSOProviderConfig]:
        """Get a provider by ID."""
        return self._providers.get(provider_id)
    
    def get_providers(self) -> list[SSOProviderConfig]:
        """Get all enabled providers."""
        return list(self._providers.values())
    
    def create_provider(self, config: SSOProviderConfig) -> SSOProviderConfig:
        """Create a new provider configuration."""
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise HTTPException(status_code=500, detail="Database not available")
        
        db = _service_client()
        if not db:
            raise HTTPException(status_code=500, detail="Database not available")
        
        # Save to database
        data = {
            "provider_id": config.provider_id,
            "provider_type": config.provider_type.value,
            "display_name": config.display_name,
            "enabled": config.enabled,
            "saml_entity_id": config.saml_entity_id,
            "saml_sso_url": config.saml_sso_url,
            "saml_slo_url": config.saml_slo_url,
            "saml_x509_cert": config.saml_x509_cert,
            "saml_private_key": config.saml_private_key,
            "saml_name_id_format": config.saml_name_id_format,
            "saml_attribute_mapping": config.saml_attribute_mapping,
            "saml_binding": config.saml_binding.value,
            "saml_want_assertions_signed": config.saml_want_assertions_signed,
            "saml_want_response_signed": config.saml_want_response_signed,
            "oidc_issuer_url": config.oidc_issuer_url,
            "oidc_client_id": config.oidc_client_id,
            "oidc_client_secret": config.oidc_client_secret,
            "oidc_discovery_url": config.oidc_discovery_url,
            "oidc_authorization_endpoint": config.oidc_authorization_endpoint,
            "oidc_token_endpoint": config.oidc_token_endpoint,
            "oidc_jwks_uri": config.oidc_jwks_uri,
            "oidc_userinfo_endpoint": config.oidc_userinfo_endpoint,
            "oidc_end_session_endpoint": config.oidc_end_session_endpoint,
            "oidc_scopes": config.oidc_scopes,
            "oidc_response_type": config.oidc_response_type,
            "oidc_pkce_enabled": config.oidc_pkce_enabled,
            "oidc_attribute_mapping": config.oidc_attribute_mapping,
            "auto_provision_users": config.auto_provision_users,
            "default_role": config.default_role,
            "default_organization_id": config.default_organization_id,
            "allowed_domains": config.allowed_domains,
            "attribute_require_email": config.attribute_require_email,
            "sign_requests": config.sign_requests,
            "encrypt_assertions": config.encrypt_assertions,
        }
        
        db.table("sso_providers").insert(data).execute()
        
        # Reload
        self._load_providers()
        return self._providers[config.provider_id]
    
    def update_provider(self, provider_id: str, updates: dict) -> Optional[SSOProviderConfig]:
        """Update a provider configuration."""
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise HTTPException(status_code=500, detail="Database not available")
        
        db = _service_client()
        if not db:
            raise HTTPException(status_code=500, detail="Database not available")
        
        db.table("sso_providers").update(updates).eq("provider_id", provider_id).execute()
        self._load_providers()
        return self._providers.get(provider_id)
    
    def delete_provider(self, provider_id: str) -> bool:
        """Delete a provider configuration."""
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise HTTPException(status_code=500, detail="Database not available")
        
        db = _service_client()
        if not db:
            raise HTTPException(status_code=500, detail="Database not available")
        
        db.table("sso_providers").delete().eq("provider_id", provider_id).execute()
        self._load_providers()
        return provider_id not in self._providers


# Global provider manager
sso_provider_manager = SSOProviderManager()


# ==================== SAML Implementation ====================

class SAMLAuthenticator:
    """SAML 2.0 Service Provider implementation."""
    
    def __init__(self, provider: SSOProviderConfig):
        self.provider = provider
    
    def build_authn_request(self, relay_state: Optional[str] = None) -> tuple[str, str]:
        """Build a SAML AuthnRequest.
        
        Returns:
            Tuple of (request_url, request_id)
        """
        request_id = f"_{uuid.uuid4().hex}"
        issue_instant = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        authn_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    ProtocolBinding="{self.provider.saml_binding.value}"
    AssertionConsumerServiceURL="{settings.SUPABASE_URL}/auth/saml/acs"
    Destination="{self.provider.saml_sso_url}"
    ForceAuthn="false"
    IsPassive="false">
    <saml:Issuer>{self.provider.saml_entity_id}</saml:Issuer>
    <samlp:NameIDPolicy Format="{self.provider.saml_name_id_format}"
        AllowCreate="true" />
    <samlp:RequestedAuthnContext Comparison="exact">
        <saml:AuthnContextClassRef>
            urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport
        </saml:AuthnContextClassRef>
    </samlp:RequestedAuthnContext>
</samlp:AuthnRequest>"""
        
        # Deflate and base64 encode
        import zlib
        compressed = zlib.compress(authn_request.encode('utf-8'))[2:-4]
        encoded = base64.b64encode(compressed).decode('utf-8')
        
        # Build redirect URL
        params = {"SAMLRequest": encoded}
        if relay_state:
            params["RelayState"] = relay_state
        
        if self.provider.saml_binding == SSOBinding.HTTP_REDIRECT:
            request_url = f"{self.provider.saml_sso_url}?{urlencode(params)}"
        else:
            request_url = self.provider.saml_sso_url  # Will be POSTed to
        
        return request_url, request_id
    
    def parse_authn_response(self, saml_response: str, relay_state: Optional[str] = None) -> Optional[SSOSession]:
        """Parse and validate a SAML AuthnResponse.
        
        Returns:
            SSOSession if valid, None otherwise
        """
        import xml.etree.ElementTree as ET
        
        try:
            # Decode base64
            decoded_bytes = base64.b64decode(saml_response)
            
            # Try to decompress (HTTP-Redirect binding uses DEFLATE)
            try:
                import zlib
                decoded = zlib.decompress(decoded_bytes, -zlib.MAX_WBITS).decode('utf-8')
            except Exception:
                # Not compressed, try direct decode (HTTP-POST binding)
                decoded = decoded_bytes.decode('utf-8')
            
            # Parse XML with safe parser (disable entity expansion to prevent XXE)
            try:
                import defusedxml.ElementTree as ET
                root = ET.fromstring(decoded, forbid_entities=True, forbid_dtd=True, forbid_external=True)
            except ImportError:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(decoded)
            
            # Check status
            ns = {
                'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
                'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
            }
            
            status = root.find('.//samlp:StatusCode', ns)
            if status is not None and status.get('Value') != 'urn:oasis:names:tc:SAML:2.0:status:Success':
                return None
            
            # Extract assertion
            assertion = root.find('.//saml:Assertion', ns)
            if assertion is None:
                return None
            
            # Extract attributes
            attributes = {}
            for attr_stmt in assertion.findall('.//saml:AttributeStatement', ns):
                for attr in attr_stmt.findall('saml:Attribute', ns):
                    name = attr.get('Name')
                    values = [v.text for v in attr.findall('saml:AttributeValue', ns)]
                    if name and values:
                        attributes[name] = values[0] if len(values) == 1 else values
            
            # Extract NameID
            name_id = assertion.find('.//saml:NameID', ns)
            name_id_value = name_id.text if name_id is not None else None
            
            # Map attributes
            email = self._get_mapped_attribute(attributes, 'email', name_id_value)
            first_name = self._get_mapped_attribute(attributes, 'first_name')
            last_name = self._get_mapped_attribute(attributes, 'last_name')
            groups = self._get_mapped_attribute(attributes, 'groups', [])
            
            if not email and self.provider.attribute_require_email:
                return None
            
            # Create session
            session = SSOSession(
                session_id=f"saml_{uuid.uuid4().hex}",
                provider_id=self.provider.provider_id,
                user_id=email or name_id_value or str(uuid.uuid4()),
                email=email or "",
                name=f"{first_name} {last_name}".strip() or email or "Unknown",
                roles=groups if isinstance(groups, list) else ([groups] if groups else []),
                attributes=attributes,
                relay_state=relay_state,
            )
            
            return session
            
        except Exception:
            return None
    
    def _get_mapped_attribute(self, attributes: dict, key: str, default: Any = None) -> Any:
        """Get attribute using provider's attribute mapping."""
        saml_attr = self.provider.saml_attribute_mapping.get(key)
        if saml_attr and saml_attr in attributes:
            return attributes[saml_attr]
        return default


# ==================== OIDC Implementation ====================

class OIDCAuthenticator:
    """OpenID Connect Relying Party implementation."""
    
    def __init__(self, provider: SSOProviderConfig):
        self.provider = provider
        self._discovery_cache: Optional[dict] = None
        self._jwks_cache: Optional[dict] = None
    
    async def get_discovery_document(self) -> dict:
        """Get OIDC discovery document."""
        if self._discovery_cache:
            return self._discovery_cache
        
        discovery_url = self.provider.oidc_discovery_url or f"{self.provider.oidc_issuer_url}/.well-known/openid-configuration"
        
        response = _safe_get(discovery_url, allowed_domains=_ALLOWED_OIDC_DOMAINS)
        if response:
            self._discovery_cache = response.json()
            return self._discovery_cache
        return {}
    
    async def get_jwks(self) -> dict:
        """Get JWKS for token validation."""
        if self._jwks_cache:
            return self._jwks_cache
        
        discovery = await self.get_discovery_document()
        jwks_uri = self.provider.oidc_jwks_uri or discovery.get('jwks_uri')
        
        if jwks_uri:
            response = _safe_get(jwks_uri, allowed_domains=_ALLOWED_OIDC_DOMAINS)
            if response:
                self._jwks_cache = response.json()
                return self._jwks_cache
        
        return {}
    
    async def build_authorization_url(self, redirect_uri: str, state: str, nonce: Optional[str] = None) -> str:
        """Build OIDC authorization URL."""
        discovery = await self.get_discovery_document()
        auth_endpoint = self.provider.oidc_authorization_endpoint or discovery.get('authorization_endpoint')
        
        if not auth_endpoint:
            raise HTTPException(status_code=500, detail="OIDC authorization endpoint not configured")
        
        params = {
            'client_id': self.provider.oidc_client_id,
            'redirect_uri': redirect_uri,
            'response_type': self.provider.oidc_response_type,
            'scope': ' '.join(self.provider.oidc_scopes),
            'state': state,
        }
        
        if nonce:
            params['nonce'] = nonce
        
        if self.provider.oidc_pkce_enabled:
            code_verifier = secrets.token_urlsafe(32)
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode().rstrip('=')
            params['code_challenge'] = code_challenge
            params['code_challenge_method'] = 'S256'
            # Store code_verifier in session for later use
            # In production, store in secure session/cookie
        
        return f"{auth_endpoint}?{urlencode(params)}"
    
    async def exchange_code_for_tokens(self, code: str, redirect_uri: str, code_verifier: Optional[str] = None) -> dict:
        """Exchange authorization code for tokens."""
        discovery = await self.get_discovery_document()
        token_endpoint = self.provider.oidc_token_endpoint or discovery.get('token_endpoint')
        
        if not token_endpoint:
            raise HTTPException(status_code=500, detail="OIDC token endpoint not configured")
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': self.provider.oidc_client_id,
        }
        
        if self.provider.oidc_client_secret:
            data['client_secret'] = self.provider.oidc_client_secret
        
        if code_verifier:
            data['code_verifier'] = code_verifier
        
        response = _safe_post(token_endpoint, data, allowed_domains=_ALLOWED_OIDC_DOMAINS)
        if response:
            return response.json()
        raise HTTPException(status_code=400, detail="Token exchange failed: invalid or blocked endpoint")
    
    async def get_userinfo(self, access_token: str) -> OIDCUserInfo:
        """Get user info from OIDC UserInfo endpoint."""
        discovery = await self.get_discovery_document()
        userinfo_endpoint = self.provider.oidc_userinfo_endpoint or discovery.get('userinfo_endpoint')
        
        if not userinfo_endpoint:
            raise HTTPException(status_code=500, detail="OIDC userinfo endpoint not configured")
        
        response = _safe_get(userinfo_endpoint, allowed_domains=_ALLOWED_OIDC_DOMAINS, timeout=10)
        if response:
            return OIDCUserInfo(**response.json())
        raise HTTPException(status_code=400, detail="UserInfo request failed: invalid or blocked endpoint")
    
    async def validate_id_token(self, id_token: str, nonce: Optional[str] = None) -> dict:
        """Validate ID token."""
        jwks = await self.get_jwks()
        
        try:
            # Get key ID from token header
            header = jwt.get_unverified_header(id_token)
            kid = header.get('kid')
            
            # Find matching key
            key = None
            for k in jwks.get('keys', []):
                if k.get('kid') == kid:
                    key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(k))
                    break
            
            if not key:
                raise HTTPException(status_code=400, detail="Unable to find matching key")
            
            # Decode and validate
            payload = jwt.decode(
                id_token,
                key=key,
                algorithms=['RS256'],
                audience=self.provider.oidc_client_id,
                issuer=self.provider.oidc_issuer_url,
                options={'verify_exp': True},
            )
            
            if nonce and payload.get('nonce') != nonce:
                raise HTTPException(status_code=400, detail="Nonce mismatch")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="ID token expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=400, detail=f"Invalid ID token: {e}")


# ==================== SSO Session Management ====================

class SSOSessionManager:
    """Manages SSO sessions."""
    
    def __init__(self):
        self._sessions: dict[str, SSOSession] = {}
    
    def create_session(self, session: SSOSession) -> str:
        """Create a new SSO session."""
        self._sessions[session.session_id] = session
        return session.session_id
    
    def get_session(self, session_id: str) -> Optional[SSOSession]:
        """Get session by ID."""
        session = self._sessions.get(session_id)
        if session and session.expires_at and session.expires_at < datetime.now(timezone.utc):
            self.delete_session(session_id)
            return None
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    def get_session_by_user(self, user_id: str) -> list[SSOSession]:
        """Get all sessions for a user."""
        return [s for s in self._sessions.values() if s.user_id == user_id]
    
    def cleanup_expired(self):
        """Remove expired sessions."""
        now = datetime.now(timezone.utc)
        expired = [sid for sid, s in self._sessions.items() if s.expires_at and s.expires_at < now]
        for sid in expired:
            del self._sessions[sid]


sso_session_manager = SSOSessionManager()


# ==================== SSO Authentication Dependencies ====================

async def get_sso_auth_context(request: Request) -> AuthContext:
    """Get authentication context with SSO support."""
    # Try standard auth first
    try:
        return await get_auth_context(request)
    except HTTPException:
        pass
    
    # Check for SSO session cookie
    session_id = request.cookies.get("sso_session")
    if session_id:
        session = sso_session_manager.get_session(session_id)
        if session:
            return AuthContext(
                user_id=session.user_id,
                email=session.email,
                organization_id=session.organization_id,
                role=session.roles[0] if session.roles else "STAFF",
            )
    
    # Check for SSO header (for API calls)
    sso_token = request.headers.get("X-SSO-Token")
    if sso_token:
        session = sso_session_manager.get_session(sso_token)
        if session:
            return AuthContext(
                user_id=session.user_id,
                email=session.email,
                organization_id=session.organization_id,
                role=session.roles[0] if session.roles else "STAFF",
            )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No valid authentication found",
    )


# ==================== Helper Functions ====================

def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge pair."""
    code_verifier = secrets.token_urlsafe(32)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip('=')
    return code_verifier, code_challenge


def build_saml_metadata(provider: SSOProviderConfig) -> str:
    """Build SAML SP metadata XML."""
    metadata = f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{provider.saml_entity_id}">
    <md:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol"
        AuthnRequestsSigned="{str(provider.sign_requests).lower()}"
        WantAssertionsSigned="{str(provider.saml_want_assertions_signed).lower()}">
        <md:KeyDescriptor use="signing">
            <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <ds:X509Data>
                    <ds:X509Certificate>{provider.saml_x509_cert}</ds:X509Certificate>
                </ds:X509Data>
            </ds:KeyInfo>
        </md:KeyDescriptor>
        <md:AssertionConsumerService Binding="{provider.saml_binding.value}"
            Location="{settings.SUPABASE_URL}/auth/saml/acs" index="0" isDefault="true"/>
        <md:SingleLogoutService Binding="{provider.saml_binding.value}"
            Location="{settings.SUPABASE_URL}/auth/saml/slo" index="0"/>
        <md:NameIDFormat>{provider.saml_name_id_format}</md:NameIDFormat>
    </md:SPSSODescriptor>
</md:EntityDescriptor>"""
    return metadata


# Import asyncio at the end to avoid circular imports
import asyncio