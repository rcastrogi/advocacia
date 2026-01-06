"""Services package for Petitio"""
from .email_service import EmailService, generate_email_2fa_code

__all__ = ["EmailService", "generate_email_2fa_code"]
