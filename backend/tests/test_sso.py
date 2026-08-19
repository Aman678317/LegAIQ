"""Tests for SSO authentication module."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import base64
import zlib
import uuid

from app.security.sso import (
    SSOProviderType,
    SSOProviderConfig,
    SSOBinding,
    SSOProviderManager,
    SAMLAuthenticator,
    OIDCAuthenticator,
    SSOSession,
    SSOSessionManager,
    generate_pkce_pair,
    build_saml_metadata,
)


class TestSSOProviderConfig:
    """Test SSO provider configuration."""
    
    def test_saml_provider_config(self):
        config = SSOProviderConfig(
            provider_id="test-saml",
            provider_type=SSOProviderType.SAML,
            display_name="Test SAML",
            saml_entity_id="https://example.com/saml/metadata",
            saml_sso_url="https://idp.example.com/sso",
            saml_x509_cert="MIID...",
        )
        assert config.provider_id == "test-saml"
        assert config.provider_type == SSOProviderType.SAML
        assert config.saml_entity_id == "https://example.com/saml/metadata"
    
    def test_oidc_provider_config(self):
        config = SSOProviderConfig(
            provider_id="test-oidc",
            provider_type=SSOProviderType.OIDC,
            display_name="Test OIDC",
            oidc_issuer_url="https://accounts.google.com",
            oidc_client_id="test-client-id",  # nosec B108
            oidc_client_secret="test-client-secret",  # nosec B108
        )
        assert config.provider_id == "test-oidc"
        assert config.provider_type == SSOProviderType.OIDC
        assert config.oidc_issuer_url == "https://accounts.google.com"


class TestSAMLAuthenticator:
    """Test SAML authentication."""
    
    @pytest.fixture
    def saml_provider(self):
        return SSOProviderConfig(
            provider_id="test-saml",
            provider_type=SSOProviderType.SAML,
            display_name="Test SAML",
            saml_entity_id="https://sp.example.com",
            saml_sso_url="https://idp.example.com/sso",
            saml_x509_cert="MIID...",
        )
    
    def test_build_authn_request(self, saml_provider):
        authenticator = SAMLAuthenticator(saml_provider)
        login_url, request_id = authenticator.build_authn_request("test-relay")
        
        assert "SAMLRequest=" in login_url
        assert "RelayState=test-relay" in login_url
        assert request_id.startswith("_")
    
    def test_build_authn_request_no_relay(self, saml_provider):
        authenticator = SAMLAuthenticator(saml_provider)
        login_url, request_id = authenticator.build_authn_request()
        
        assert "SAMLRequest=" in login_url
        assert "RelayState=" not in login_url
    
    def test_parse_authn_response_valid(self, saml_provider):
        """Test parsing a valid SAML response."""
        authenticator = SAMLAuthenticator(saml_provider)
        
        # Create a minimal valid SAML response
        saml_response = """<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="_12345" Version="2.0" IssueInstant="2024-01-01T00:00:00Z">
    <samlp:Status>
        <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
    </samlp:Status>
    <saml:Assertion ID="_assertion1" Version="2.0" IssueInstant="2024-01-01T00:00:00Z">
        <saml:Issuer>https://idp.example.com</saml:Issuer>
        <saml:Subject>
            <saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">user@example.com</saml:NameID>
        </saml:Subject>
        <saml:AttributeStatement>
            <saml:Attribute Name="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress">
                <saml:AttributeValue>user@example.com</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname">
                <saml:AttributeValue>John</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname">
                <saml:AttributeValue>Doe</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>
</samlp:Response>"""
        
        # Encode as base64 (simulating HTTP-Redirect binding)
        compressed = zlib.compress(saml_response.encode('utf-8'))[2:-4]
        encoded = base64.b64encode(compressed).decode('utf-8')
        
        session = authenticator.parse_authn_response(encoded, "test-relay")
        
        assert session is not None
        assert session.email == "user@example.com"
        assert session.name == "John Doe"
        assert session.provider_id == "test-saml"
    
    def test_parse_authn_response_invalid_status(self, saml_provider):
        """Test parsing SAML response with error status."""
        authenticator = SAMLAuthenticator(saml_provider)
        
        saml_response = """<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="_12345" Version="2.0">
    <samlp:Status>
        <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:AuthnFailed"/>
    </samlp:Status>
</samlp:Response>"""
        
        compressed = zlib.compress(saml_response.encode('utf-8'))[2:-4]
        encoded = base64.b64encode(compressed).decode('utf-8')
        
        session = authenticator.parse_authn_response(encoded)
        assert session is None


class TestOIDCAuthenticator:
    """Test OIDC authentication."""
    
    @pytest.fixture
    def oidc_provider(self):
        return SSOProviderConfig(
            provider_id="test-oidc",
            provider_type=SSOProviderType.OIDC,
            display_name="Test OIDC",
            oidc_issuer_url="https://accounts.google.com",
            oidc_client_id="test-client-id",  # nosec B108
            oidc_client_secret="test-client-secret",  # nosec B108
            oidc_discovery_url="https://accounts.google.com/.well-known/openid-configuration",
        )
    
    @pytest.mark.asyncio
    async def test_build_authorization_url(self, oidc_provider):
        """Test building OIDC authorization URL."""
        authenticator = OIDCAuthenticator(oidc_provider)
        
        # Mock discovery document
        with patch.object(authenticator, 'get_discovery_document', new_callable=AsyncMock) as mock_discovery:
            mock_discovery.return_value = {
                "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_endpoint": "https://oauth2.googleapis.com/token",
                "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo",
                "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
            }
            
            url = await authenticator.build_authorization_url(
                "https://app.example.com/callback",
                "test-state",
                "test-nonce"
            )
            
            assert "https://accounts.google.com/o/oauth2/v2/auth" in url
            assert "client_id=test-client-id" in url
            assert "redirect_uri=https%3A%2F%2Fapp.example.com%2Fcallback" in url
            assert "state=test-state" in url
            assert "nonce=test-nonce" in url
            assert "code_challenge=" in url
            assert "code_challenge_method=S256" in url


class TestPKCE:
    """Test PKCE generation."""
    
    def test_generate_pkce_pair(self):
        code_verifier, code_challenge = generate_pkce_pair()
        
        assert len(code_verifier) >= 43  # 32 bytes base64url encoded
        assert len(code_challenge) == 43  # SHA256 base64url encoded
        
        # Verify challenge is derived from verifier
        import hashlib
        import base64
        expected = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')
        assert code_challenge == expected


class TestSAMLMetadata:
    """Test SAML metadata generation."""
    
    def test_build_saml_metadata(self):
        provider = SSOProviderConfig(
            provider_id="test-saml",
            provider_type=SSOProviderType.SAML,
            display_name="Test SAML",
            saml_entity_id="https://sp.example.com",
            saml_x509_cert="MIID...",
            saml_binding=SSOBinding.HTTP_REDIRECT,
            sign_requests=True,
            saml_want_assertions_signed=True,
        )
        
        metadata = build_saml_metadata(provider)
        
        assert "EntityDescriptor" in metadata
        assert "https://sp.example.com" in metadata
        assert "MIID..." in metadata
        assert "HTTP-Redirect" in metadata


class TestSSOSessionManager:
    """Test SSO session management."""
    
    @pytest.fixture
    def session_manager(self):
        return SSOSessionManager()
    
    def test_create_and_get_session(self, session_manager):
        session = SSOSession(
            session_id="test-session",
            provider_id="test-provider",
            user_id="user123",
            email="user@example.com",
            name="Test User",
            roles=["STAFF"],
        )
        
        session_manager.create_session(session)
        retrieved = session_manager.get_session("test-session")
        
        assert retrieved is not None
        assert retrieved.session_id == "test-session"
        assert retrieved.email == "user@example.com"
    
    def test_delete_session(self, session_manager):
        session = SSOSession(
            session_id="test-session",
            provider_id="test-provider",
            user_id="user123",
            email="user@example.com",
            name="Test User",
            roles=["STAFF"],
        )
        
        session_manager.create_session(session)
        assert session_manager.delete_session("test-session") is True
        assert session_manager.get_session("test-session") is None
    
    def test_get_session_by_user(self, session_manager):
        session1 = SSOSession(
            session_id="session1",
            provider_id="provider1",
            user_id="user123",
            email="user@example.com",
            name="Test User",
            roles=["STAFF"],
        )
        session2 = SSOSession(
            session_id="session2",
            provider_id="provider2",
            user_id="user123",
            email="user@example.com",
            name="Test User",
            roles=["ADMIN"],
        )
        
        session_manager.create_session(session1)
        session_manager.create_session(session2)
        
        user_sessions = session_manager.get_session_by_user("user123")
        assert len(user_sessions) == 2
    
    def test_cleanup_expired(self, session_manager):
        from datetime import datetime, timezone, timedelta
        
        session = SSOSession(
            session_id="expired-session",
            provider_id="test-provider",
            user_id="user123",
            email="user@example.com",
            name="Test User",
            roles=["STAFF"],
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        
        session_manager.create_session(session)
        session_manager.cleanup_expired()
        
        assert session_manager.get_session("expired-session") is None


class TestSSOProviderManager:
    """Test SSO provider manager."""
    
    def test_get_provider_not_found(self):
        manager = SSOProviderManager()
        manager._providers = {}
        
        provider = manager.get_provider("non-existent")
        assert provider is None
    
    def test_get_providers_empty(self):
        manager = SSOProviderManager()
        manager._providers = {}
        
        providers = manager.get_providers()
        assert providers == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])