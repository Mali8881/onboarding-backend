from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        return self.get_ident(request)


class PasswordResetRequestThrottle(SimpleRateThrottle):
    scope = "password_reset_request"

    def get_cache_key(self, request, view):
        return self.get_ident(request)


class PasswordResetConfirmThrottle(SimpleRateThrottle):
    scope = "password_reset_confirm"

    def get_cache_key(self, request, view):
        return self.get_ident(request)
