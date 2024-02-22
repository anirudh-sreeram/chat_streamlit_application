#!/usr/bin/env python3
"""
Auth using LDAP
"""

import lib.ldap_authenticator as ldap_auth


def auth_window(authc, ldap_server, error):
    authc.write("LDAP Login")
    if error:
        authc.error(error)
    username = authc.text_input("Username")
    password = authc.text_input("Password", type="password")
    submitted = authc.button("Submit")
    if submitted:
        ldapauth = ldap_auth.LDAPAuth()
        return ldapauth.authenticate(username, password), username
    return False, username
