from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse


class FreshLoginOnExternalEntryMiddleware:
    """Require a fresh login when an authenticated user re-enters the app."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        fetch_site = request.headers.get("Sec-Fetch-Site", "").lower()
        fetch_mode = request.headers.get("Sec-Fetch-Mode", "").lower()
        is_external_entry = (
            request.method == "GET"
            and fetch_mode == "navigate"
            and fetch_site in {"none", "cross-site"}
        )

        if request.user.is_authenticated and is_external_entry:
            login_path = reverse("login")
            logout(request)
            if request.path != login_path:
                return redirect("login")

        return self.get_response(request)
