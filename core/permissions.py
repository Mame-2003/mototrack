from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsManager(BasePermission):
    message = "Accès réservé au responsable."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser))


class IsManagerOrReadOwn(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        return request.method in SAFE_METHODS or getattr(view, "action", None) == "valider_otp"

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        livreur = getattr(request.user, "livreur", None)
        return obj == livreur or getattr(obj, "livreur", None) == livreur
