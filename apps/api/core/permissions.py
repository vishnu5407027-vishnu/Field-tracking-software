"""Role-based access control, declared per-view via `allowed_roles`."""

from rest_framework.permissions import BasePermission


class HasRole(BasePermission):
    """Grants access when the authenticated user's role is allowed by the view.

    Views declare either `allowed_roles` (all methods) or
    `allowed_roles_by_method` (e.g. list open to dispatchers, create restricted
    to admins). Views declaring neither accept any authenticated user.
    """

    message = "Insufficient role"

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        by_method = getattr(view, "allowed_roles_by_method", None)
        if by_method is not None and request.method in by_method:
            return request.user.role in by_method[request.method]
        allowed = getattr(view, "allowed_roles", None)
        return allowed is None or request.user.role in allowed
