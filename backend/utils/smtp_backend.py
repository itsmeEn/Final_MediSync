import smtplib
import socket
import ssl
from typing import Optional

from django.core.mail.backends.smtp import EmailBackend as DjangoSMTPEmailBackend


class IPv4SMTPEmailBackend(DjangoSMTPEmailBackend):
    def open(self) -> Optional[bool]:
        if self.connection:
            return False

        try:
            host = self.host
            port = self.port

            connect_host = host
            try:
                addrinfos = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
                if addrinfos:
                    connect_host = addrinfos[0][4][0]
            except Exception:
                connect_host = host

            if self.use_ssl:
                self.connection = smtplib.SMTP_SSL(
                    connect_host,
                    port,
                    timeout=self.timeout,
                    local_hostname=self.local_hostname,
                )
                try:
                    self.connection._host = host
                except Exception:
                    pass
            else:
                self.connection = smtplib.SMTP(
                    connect_host,
                    port,
                    timeout=self.timeout,
                    local_hostname=self.local_hostname,
                )
                try:
                    self.connection._host = host
                except Exception:
                    pass
                try:
                    self.connection.ehlo()
                except Exception:
                    pass

                if self.use_tls:
                    context = ssl.create_default_context()
                    self.connection.starttls(context=context)
                    self.connection.ehlo()

            if self.username and self.password:
                self.connection.login(self.username, self.password)

            return True
        except Exception:
            if self.fail_silently:
                return False
            raise
