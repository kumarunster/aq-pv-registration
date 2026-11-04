class PortalError(Exception):
    """Only fixed, non-sensitive messages may be returned to API clients."""

    code = "upstream_error"
    status_code = 502
    message = "NRM returned an unexpected response."


class AuthenticationError(PortalError):
    code = "nrm_authentication_failed"
    message = "NRM sign-in failed or requires an interactive step. Check the server credentials."


class SessionExpired(PortalError):
    code = "nrm_session_expired"
    message = "NRM rejected the authenticated session."


class PortalTimeout(PortalError):
    code = "nrm_timeout"
    status_code = 504
    message = "The NRM portal did not respond within the configured request timeout."


class PortalUnavailable(PortalError):
    code = "nrm_unavailable"
    status_code = 503
    message = "The NRM portal is temporarily unavailable."


class ActionRequired(PortalError):
    code = "portal_action_required"
    status_code = 409
    message = "e-netz requires the account holder to read and acknowledge outstanding portal notices."


class UnsupportedOperation(PortalError):
    code = "operation_not_implemented"
    status_code = 501
    message = "This operation has not been verified and implemented for this provider."


class ProviderNotConfigured(PortalError):
    code = "provider_not_configured"
    status_code = 503
    message = "Credentials for this provider are not configured on the server."


class RecordNotFound(PortalError):
    code = "record_not_found"
    status_code = 404
    message = "The requested record is not accessible in this account."
