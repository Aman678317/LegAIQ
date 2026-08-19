"""SSO Authentication API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
import uuid

from app.config import get_settings
from app.security.auth import AuthContext, get_auth_context, require_role
from app.security.sso import (
    SSOProviderType,
    SSOProviderConfig,
    SSOBinding,
    sso_provider_manager,
    SAMLAuthenticator,
    OIDCAuthenticator,
    sso_session_manager,
    SSOSession,
    build_saml_metadata,
    generate_pkce_pair,
)

settings = get_settings()
router = APIRouter(prefix="/auth/sso", tags=["sso"])


# ==================== Request/Response Models ====================

class SSOProviderCreate(BaseModel):
    provider_id: str
    provider_type: SSOProviderType
    display_name: str
    enabled: bool = True
    
    # SAML
    saml_entity_id: Optional[str] = None
    saml_sso_url: Optional[str] = None
    saml_slo_url: Optional[str] = None
    saml_x509_cert: Optional[str] = None
    saml_private_key: Optional[str] = None
    saml_name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    saml_attribute_mapping: dict = {}
    saml_binding: SSOBinding = SSOBinding.HTTP_REDIRECT
    saml_want_assertions_signed: bool = True
    saml_want_response_signed: bool = True
    
    # OIDC
    oidc_issuer_url: Optional[str] = None
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None
    oidc_discovery_url: Optional[str] = None
    oidc_authorization_endpoint: Optional[str] = None
    oidc_token_endpoint: Optional[str] = None
    oidc_jwks_uri: Optional[str] = None
    oidc_userinfo_endpoint: Optional[str] = None
    oidc_end_session_endpoint: Optional[str] = None
    oidc_scopes: List[str] = ["openid", "email", "profile"]
    oidc_response_type: str = "code"
    oidc_pkce_enabled: bool = True
    oidc_attribute_mapping: dict = {}
    
    # General
    auto_provision_users: bool = True
    default_role: str = "STAFF"
    default_organization_id: Optional[str] = None
    allowed_domains: List[str] = []
    attribute_require_email: bool = True
    sign_requests: bool = True
    encrypt_assertions: bool = False


class SSOProviderUpdate(BaseModel):
    display_name: Optional[str] = None
    enabled: Optional[bool] = None
    saml_entity_id: Optional[str] = None
    saml_sso_url: Optional[str] = None
    saml_slo_url: Optional[str] = None
    saml_x509_cert: Optional[str] = None
    saml_private_key: Optional[str] = None
    saml_name_id_format: Optional[str] = None
    saml_attribute_mapping: Optional[dict] = None
    saml_binding: Optional[SSOBinding] = None
    saml_want_assertions_signed: Optional[bool] = None
    saml_want_response_signed: Optional[bool] = None
    oidc_issuer_url: Optional[str] = None
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None
    oidc_discovery_url: Optional[str] = None
    oidc_authorization_endpoint: Optional[str] = None
    oidc_token_endpoint: Optional[str] = None
    oidc_jwks_uri: Optional[str] = None
    oidc_userinfo_endpoint: Optional[str] = None
    oidc_end_session_endpoint: Optional[str] = None
    oidc_scopes: Optional[List[str]] = None
    oidc_response_type: Optional[str] = None
    oidc_pkce_enabled: Optional[bool] = None
    oidc_attribute_mapping: Optional[dict] = None
    auto_provision_users: Optional[bool] = None
    default_role: Optional[str] = None
    default_organization_id: Optional[str] = None
    allowed_domains: Optional[List[str]] = None
    attribute_require_email: Optional[bool] = None
    sign_requests: Optional[bool] = None
    encrypt_assertions: Optional[bool] = None


class SSOProviderResponse(BaseModel):
    provider_id: str
    provider_type: str
    display_name: str
    enabled: bool
    created_at: str


class SSOLoginRequest(BaseModel):
    provider_id: str
    relay_state: Optional[str] = None
    redirect_url: Optional[HttpUrl] = None


class SSOLoginResponse(BaseModel):
    login_url: str
    session_id: str
    provider_id: str


# ==================== Provider Management (Admin only) ====================

@router.get("/providers", response_model=List[SSOProviderResponse])
async def list_sso_providers(
    ctx: AuthContext = Depends(require_role("ADMIN")),
):
    """List all configured SSO providers."""
    providers = sso_provider_manager.get_providers()
    return [
        SSOProviderResponse(
            provider_id=p.provider_id,
            provider_type=p.provider_type.value,
            display_name=p.display_name,
            enabled=p.enabled,
            created_at=p.created_at.isoformat(),
        )
        for p in providers
    ]


@router.post("/providers", response_model=SSOProviderResponse)
async def create_sso_provider(
    config: SSOProviderCreate,
    ctx: AuthContext = Depends(require_role("ADMIN")),
):
    """Create a new SSO provider configuration."""
    provider_config = SSOProviderConfig(
        provider_id=config.provider_id,
        provider_type=config.provider_type,
        display_name=config.display_name,
        enabled=config.enabled,
        saml_entity_id=config.saml_entity_id,
        saml_sso_url=config.saml_sso_url,
        saml_slo_url=config.saml_slo_url,
        saml_x509_cert=config.saml_x509_cert,
        saml_private_key=config.saml_private_key,
        saml_name_id_format=config.saml_name_id_format,
        saml_attribute_mapping=config.saml_attribute_mapping,
        saml_binding=config.saml_binding,
        saml_want_assertions_signed=config.saml_want_assertions_signed,
        saml_want_response_signed=config.saml_want_response_signed,
        oidc_issuer_url=config.oidc_issuer_url,
        oidc_client_id=config.oidc_client_id,
        oidc_client_secret=config.oidc_client_secret,
        oidc_discovery_url=config.oidc_discovery_url,
        oidc_authorization_endpoint=config.oidc_authorization_endpoint,
        oidc_token_endpoint=config.oidc_token_endpoint,
        oidc_jwks_uri=config.oidc_jwks_uri,
        oidc_userinfo_endpoint=config.oidc_userinfo_endpoint,
        oidc_end_session_endpoint=config.oidc_end_session_endpoint,
        oidc_scopes=config.oidc_scopes,
        oidc_response_type=config.oidc_response_type,
        oidc_pkce_enabled=config.oidc_pkce_enabled,
        oidc_attribute_mapping=config.oidc_attribute_mapping,
        auto_provision_users=config.auto_provision_users,
        default_role=config.default_role,
        default_organization_id=config.default_organization_id,
        allowed_domains=config.allowed_domains,
        attribute_require_email=config.attribute_require_email,
        sign_requests=config.sign_requests,
        encrypt_assertions=config.encrypt_assertions,
    )
    
    created = sso_provider_manager.create_provider(provider_config)
    return SSOProviderResponse(
        provider_id=created.provider_id,
        provider_type=created.provider_type.value,
        display_name=created.display_name,
        enabled=created.enabled,
        created_at=created.created_at.isoformat(),
    )


@router.patch("/providers/{provider_id}", response_model=SSOProviderResponse)
async def update_sso_provider(
    provider_id: str,
    updates: SSOProviderUpdate,
    ctx: AuthContext = Depends(require_role("ADMIN")),
):
    """Update an SSO provider configuration."""
    update_data = updates.model_dump(exclude_unset=True)
    updated = sso_provider_manager.update_provider(provider_id, update_data)
    
    if not updated:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return SSOProviderResponse(
        provider_id=updated.provider_id,
        provider_type=updated.provider_type.value,
        display_name=updated.display_name,
        enabled=updated.enabled,
        created_at=updated.created_at.isoformat(),
    )


@router.delete("/providers/{provider_id}")
async def delete_sso_provider(
    provider_id: str,
    ctx: AuthContext = Depends(require_role("ADMIN")),
):
    """Delete an SSO provider configuration."""
    success = sso_provider_manager.delete_provider(provider_id)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"deleted": True}


@router.get("/providers/{provider_id}/metadata")
async def get_saml_metadata(provider_id: str):
    """Get SAML SP metadata for a provider."""
    provider = sso_provider_manager.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    if provider.provider_type != SSOProviderType.SAML:
        raise HTTPException(status_code=400, detail="Provider is not SAML type")
    
    metadata = build_saml_metadata(provider)
    return Response(content=metadata, media_type="application/xml")


# ==================== Authentication Flows ====================

@router.post("/login", response_model=SSOLoginResponse)
async def initiate_sso_login(
    request: SSOLoginRequest,
    response: Response,
):
    """Initiate SSO login for a provider."""
    provider = sso_provider_manager.get_provider(request.provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    if not provider.enabled:
        raise HTTPException(status_code=400, detail="Provider is disabled")
    
    relay_state = request.relay_state or str(uuid.uuid4())
    
    if provider.provider_type == SSOProviderType.SAML:
        # SAML flow
        authenticator = SAMLAuthenticator(provider)
        login_url, request_id = authenticator.build_authn_request(relay_state)
        
        # Store session with relay state
        session = SSOSession(
            session_id=f"saml_{request_id}",
            provider_id=provider.provider_id,
            user_id="",  # Will be filled after ACS
            email="",
            name="",
            roles=[],
            relay_state=relay_state,
        )
        sso_session_manager.create_session(session)
        
        return SSOLoginResponse(
            login_url=login_url,
            session_id=session.session_id,
            provider_id=provider.provider_id,
        )
    
    else:
        # OIDC flow
        authenticator = OIDCAuthenticator(provider)
        redirect_uri = str(request.redirect_url) if request.redirect_url else f"{settings.SUPABASE_URL}/auth/sso/oidc/callback"
        
        state = str(uuid.uuid4())
        nonce = str(uuid.uuid4())
        code_verifier, code_challenge = generate_pkce_pair()
        
        # Store PKCE and state in session
        session = SSOSession(
            session_id=f"oidc_{state}",
            provider_id=provider.provider_id,
            user_id="",
            email="",
            name="",
            roles=[],
            attributes={
                "code_verifier": code_verifier,
                "nonce": nonce,
                "redirect_uri": redirect_uri,
            },
            relay_state=relay_state,
        )
        sso_session_manager.create_session(session)
        
        login_url = await authenticator.build_authorization_url(redirect_uri, state, nonce)
        
        return SSOLoginResponse(
            login_url=login_url,
            session_id=session.session_id,
            provider_id=provider.provider_id,
        )


@router.get("/saml/acs")
async def saml_acs(
    SAMLResponse: str,
    RelayState: Optional[str] = None,
):
    """SAML Assertion Consumer Service endpoint."""
    # Find session by relay state
    session = None
    for s in sso_session_manager._sessions.values():
        if s.relay_state == RelayState:
            session = s
            break
    
    if not session:
        raise HTTPException(status_code=400, detail="Invalid or expired session")
    
    provider = sso_provider_manager.get_provider(session.provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    authenticator = SAMLAuthenticator(provider)
    sso_session = authenticator.parse_authn_response(SAMLResponse, RelayState)
    
    if not sso_session:
        raise HTTPException(status_code=400, detail="SAML response validation failed")
    
    # Update session with user info
    sso_session.session_id = session.session_id
    sso_session_manager.create_session(sso_session)
    
    # Set secure cookie
    response = RedirectResponse(url=f"{settings.FRONTEND_URL}/sso/callback?session_id={sso_session.session_id}")
    response.set_cookie(
        key="sso_session",
        value=sso_session.session_id,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=3600,
    )
    
    return response


@router.get("/oidc/callback")
async def oidc_callback(
    code: str,
    state: str,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """OIDC Authorization Code callback endpoint."""
    if error:
        raise HTTPException(status_code=400, detail=f"OIDC error: {error} - {error_description}")
    
    # Find session by state
    session = sso_session_manager.get_session(f"oidc_{state}")
    if not session:
        raise HTTPException(status_code=400, detail="Invalid or expired session")
    
    provider = sso_provider_manager.get_provider(session.provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    authenticator = OIDCAuthenticator(provider)
    
    # Exchange code for tokens
    code_verifier = session.attributes.get("code_verifier")
    redirect_uri = session.attributes.get("redirect_uri", f"{settings.SUPABASE_URL}/auth/sso/oidc/callback")
    
    tokens = await authenticator.exchange_code_for_tokens(code, redirect_uri, code_verifier)
    
    # Validate ID token
    id_token = tokens.get("id_token")
    nonce = session.attributes.get("nonce")
    
    if id_token:
        claims = await authenticator.validate_id_token(id_token, nonce)
    else:
        # Fallback to userinfo endpoint
        access_token = tokens.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")
        userinfo = await authenticator.get_userinfo(access_token)
        claims = userinfo.model_dump()
    
    # Extract user info using attribute mapping
    email = claims.get(provider.oidc_attribute_mapping.get("email", "email"))
    first_name = claims.get(provider.oidc_attribute_mapping.get("first_name", "given_name"))
    last_name = claims.get(provider.oidc_attribute_mapping.get("last_name", "family_name"))
    groups = claims.get(provider.oidc_attribute_mapping.get("groups", "groups"), [])
    
    if not email and provider.attribute_require_email:
        raise HTTPException(status_code=400, detail="Email not provided by identity provider")
    
    # Create SSO session
    sso_session = SSOSession(
        session_id=session.session_id,
        provider_id=provider.provider_id,
        user_id=email or claims.get("sub", str(uuid.uuid4())),
        email=email or "",
        name=f"{first_name or ''} {last_name or ''}".strip() or email or "Unknown",
        roles=groups if isinstance(groups, list) else ([groups] if groups else []),
        attributes=claims,
        relay_state=session.relay_state,
    )
    sso_session_manager.create_session(sso_session)
    
    # Redirect to frontend with session
    response = RedirectResponse(url=f"{settings.FRONTEND_URL}/sso/callback?session_id={sso_session.session_id}")
    response.set_cookie(
        key="sso_session",
        value=sso_session.session_id,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=3600,
    )
    
    return response


@router.post("/logout")
async def sso_logout(
    request: Request,
    response: Response,
):
    """Logout from SSO session."""
    session_id = request.cookies.get("sso_session")
    if session_id:
        session = sso_session_manager.get_session(session_id)
        if session:
            provider = sso_provider_manager.get_provider(session.provider_id)
            if provider and provider.provider_type != SSOProviderType.SAML:
                # OIDC logout
                authenticator = OIDCAuthenticator(provider)
                discovery = await authenticator.get_discovery_document()
                end_session_endpoint = provider.oidc_end_session_endpoint or discovery.get("end_session_endpoint")
                
                if end_session_endpoint:
                    # Redirect to IdP logout
                    logout_url = f"{end_session_endpoint}?post_logout_redirect_uri={settings.FRONTEND_URL}/login"
                    response = RedirectResponse(url=logout_url)
                    response.delete_cookie("sso_session")
                    return response
        
        sso_session_manager.delete_session(session_id)
    
    response.delete_cookie("sso_session")
    return {"logged_out": True}


@router.get("/session/{session_id}")
async def get_sso_session(
    session_id: str,
    ctx: AuthContext = Depends(get_auth_context),
):
    """Get SSO session details (for frontend callback)."""
    session = sso_session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Verify session belongs to current user or user is admin
    if session.user_id != ctx.user_id and ctx.role not in ("ADMIN", "OWNER"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "session_id": session.session_id,
        "provider_id": session.provider_id,
        "user_id": session.user_id,
        "email": session.email,
        "name": session.name,
        "roles": session.roles,
        "organization_id": session.organization_id,
        "created_at": session.created_at.isoformat(),
    }


@router.post("/session/{session_id}/exchange")
async def exchange_sso_session(
    session_id: str,
    ctx: AuthContext = Depends(get_auth_context),
):
    """Exchange SSO session for JWT token."""
    session = sso_session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Verify session belongs to current user
    if session.user_id != ctx.user_id and ctx.role not in ("ADMIN", "OWNER"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Create JWT token with SSO info
    import jwt
    from datetime import datetime, timezone, timedelta
    
    payload = {
        "sub": session.user_id,
        "email": session.email,
        "name": session.name,
        "roles": session.roles,
        "organization_id": session.organization_id,
        "sso_provider": session.provider_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
        "iat": datetime.now(timezone.utc),
    }
    
    token = jwt.encode(payload, settings.JWT_SECRET or "secret", algorithm="HS256")
    
    # Clean up session
    sso_session_manager.delete_session(session_id)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 86400,
    }


# ==================== Health Check ====================

@router.get("/health")
async def sso_health():
    """SSO service health check."""
    providers = sso_provider_manager.get_providers()
    return {
        "status": "healthy",
        "providers_configured": len(providers),
        "active_sessions": len(sso_session_manager._sessions),
    }