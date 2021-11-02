
def validate(ident, config):
    """
    This function serves as a generic hook into the authentication system.  It should
    return a unique id string for a user based on the provided authentication token.

    :param ident: Identifying token, taken from the authorization field of the originating request
    :type ident: string
    
    :param config: Contains unis configuration dictionary for optional parameters
    :type config: dict

    :raises InvalidAuthError: Raises :class:`unis.auth.InvalidAuthError` if invalid credentials are provided
    :raises UndefinedAuthError: Raises :class:`unis.auth.UndefinedAuthError` if no credentials are provided

    :return: Filter token used by mongodb to identify record and group membership.
    :rtype: string
    """
    return ""
