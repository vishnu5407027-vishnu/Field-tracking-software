from rest_framework_simplejwt.tokens import RefreshToken


def issue_tokens(user) -> dict[str, str]:
    """Access/refresh pair with the claims the realtime layer relies on
    (tenant and role are read straight from the token on WS connect)."""
    refresh = RefreshToken.for_user(user)
    for token in (refresh, refresh.access_token):
        token["tenantId"] = str(user.tenant_id) if user.tenant_id else None
        token["role"] = user.role
        token["email"] = user.email
        token["name"] = f"{user.first_name} {user.last_name}"
    return {"access": str(refresh.access_token), "refresh": str(refresh)}
