from unittest.mock import MagicMock

import pytest

from core.exception.exceptions import ExternalServiceException
from domains.auth import email_service as email_service_module
from domains.auth.email_service import EmailService
from domains.auth.verification_store import PURPOSE_SIGNUP


async def test_console_backend_does_not_raise():
    service = EmailService(backend="console")

    await service.send_verification_code("test@example.com", "123456", PURPOSE_SIGNUP)  # 예외 없이 통과해야 함


async def test_unsupported_backend_raises():
    service = EmailService(backend="unknown")

    with pytest.raises(ExternalServiceException):
        await service.send_verification_code("test@example.com", "123456", PURPOSE_SIGNUP)


async def test_smtp_backend_raises_when_config_missing():
    service = EmailService(backend="smtp", smtp_host=None, smtp_from_email=None)

    with pytest.raises(ExternalServiceException):
        await service.send_verification_code("test@example.com", "123456", PURPOSE_SIGNUP)


async def test_smtp_backend_sends_message_via_smtplib(monkeypatch: pytest.MonkeyPatch):
    smtp_instance = MagicMock()
    smtp_instance.__enter__.return_value = smtp_instance
    smtp_instance.__exit__.return_value = False
    smtp_class = MagicMock(return_value=smtp_instance)
    monkeypatch.setattr(email_service_module.smtplib, "SMTP", smtp_class)

    service = EmailService(
        backend="smtp",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="user",
        smtp_password="pass",
        smtp_from_email="noreply@example.com",
    )

    await service.send_verification_code("test@example.com", "123456", PURPOSE_SIGNUP)

    smtp_class.assert_called_once_with("smtp.example.com", 587, timeout=30)
    smtp_instance.starttls.assert_called_once()
    smtp_instance.login.assert_called_once_with("user", "pass")
    smtp_instance.send_message.assert_called_once()
    sent_message = smtp_instance.send_message.call_args.args[0]
    assert sent_message["To"] == "test@example.com"
    assert "123456" in sent_message.get_content()


async def test_smtp_backend_skips_login_when_no_credentials(monkeypatch: pytest.MonkeyPatch):
    smtp_instance = MagicMock()
    smtp_instance.__enter__.return_value = smtp_instance
    smtp_instance.__exit__.return_value = False
    monkeypatch.setattr(email_service_module.smtplib, "SMTP", MagicMock(return_value=smtp_instance))

    service = EmailService(backend="smtp", smtp_host="smtp.example.com", smtp_from_email="noreply@example.com")

    await service.send_verification_code("test@example.com", "123456", PURPOSE_SIGNUP)

    smtp_instance.login.assert_not_called()


async def test_smtp_backend_wraps_unexpected_errors(monkeypatch: pytest.MonkeyPatch):
    smtp_class = MagicMock(side_effect=OSError("connection refused"))
    monkeypatch.setattr(email_service_module.smtplib, "SMTP", smtp_class)

    service = EmailService(backend="smtp", smtp_host="smtp.example.com", smtp_from_email="noreply@example.com")

    with pytest.raises(ExternalServiceException):
        await service.send_verification_code("test@example.com", "123456", PURPOSE_SIGNUP)
