import re
import logging
from dataclasses import dataclass, field
from typing import Literal, List

import ldap3
from ldap3.core.exceptions import LDAPBindError, LDAPCommunicationError
from ldap3.utils.uri import parse_uri


log_format = "%(asctime)s [LDAP][%(levelname)s][%(lineno)d]: %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger()


class BasicAuthException(Exception):
    pass


@dataclass
class LDAPAuth:
    authentication: Literal["LDAP"] = "LDAP"
    authorized_LDAP_groups: List[str] = field(default_factory=list)
    group_template = "cn={},ou=groups,dc=service-now,dc=com"
    user_template = "uid={},ou=people,dc=service-now,dc=com"
    valid_username_regex = "^[a-zA-Z][.a-zA-Z0-9_-]*$"
    server = "ldaps://ldapmaster.service-now.com:636"
    parsed = parse_uri(server)

    def authenticate(self, username: str, password: str) -> bool:

        if not re.match(self.valid_username_regex, username):
            raise BasicAuthException(f"Invalid username: must match {self.valid_username_regex}")

        if password.strip() == "":
            raise BasicAuthException("Invalid password: can not be empty")

        auto_bind = ldap3.AUTO_BIND_NO_TLS if self.parsed['ssl'] else ldap3.AUTO_BIND_TLS_BEFORE_BIND
        user = self.user_template.format(username)
        print("Server:", self.parsed)
        server = ldap3.Server(host=self.parsed['host'], port=self.parsed['port'], use_ssl=self.parsed['ssl'])
        print("Authenticating Now")
        try:
            connection = ldap3.Connection(
                server=server, user=user, password=password, auto_bind=auto_bind
            )
        except LDAPCommunicationError as e:
            raise BasicAuthException(f"Communication error (probably VPN?): {e}")
        except LDAPBindError as e:
            raise BasicAuthException(f"Authentication error: {e}")
        else:
            # Connection might already be bound depending on the auto_bind argument.
            is_bound = connection.bound or connection.bind()
            if not is_bound:
                raise BasicAuthException("Authentication error: bind not successful")
        finally:
            pass

        if self.authorized_LDAP_groups:
            attributes = ("member", "uniqueMember", "memberUid")
            values = (user, user, username)
            search_filter = f"(|{''.join(f'({a}={v})' for a, v in zip(attributes, values))})"
            for group_name in self.authorized_LDAP_groups:
                group = self.group_template.format(group_name)
                if connection.search(
                        search_base=group,
                        search_filter=search_filter,
                        search_scope=ldap3.BASE,
                        attributes=attributes,
                ):
                    logger.debug(f"Found authorized group: {group_name}")
                    break
            else:
                raise BasicAuthException(f"Not in authorized groups: {self.authorized_LDAP_groups}")
        print("Authenticated")
        return True
