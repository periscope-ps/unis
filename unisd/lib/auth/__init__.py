
class AuthError(Exception): pass
class UnknownAuthType(AuthError): pass
class UndefinedAuthError(AuthError): pass
class InvalidAuthError(AuthError): pass
