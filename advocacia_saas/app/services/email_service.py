"""
Serviço de email usando Resend
Responsável por enviar emails transacionais incluindo 2FA
"""
import os
import secrets
from typing import Optional

from flask import current_app, render_template_string


class EmailService:
    """Serviço de email com Resend"""

    @staticmethod
    def _get_resend_client():
        """Obtém cliente Resend ou retorna None se não configurado"""
        try:
            from resend import Resend
            api_key = os.getenv("RESEND_API_KEY")
            if not api_key:
                current_app.logger.warning("RESEND_API_KEY não configurada")
                return None
            return Resend(api_key=api_key)
        except ImportError:
            current_app.logger.warning("Resend não instalado. Instale: pip install resend")
            return None

    @staticmethod
    def send_2fa_code_email(user_email: str, code: str, method: str = "email") -> bool:
        """
        Envia código 2FA por email
        
        Args:
            user_email: Email do usuário
            code: Código 2FA a ser enviado
            method: Método 2FA ('email' ou 'totp')
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        client = EmailService._get_resend_client()
        if not client:
            current_app.logger.warning(f"Não foi possível enviar 2FA para {user_email}: Resend não configurado")
            return False

        try:
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #2c3e50;">Código de Autenticação em Dois Fatores</h2>
                        
                        <p>Olá,</p>
                        
                        <p>Seu código de autenticação de dois fatores é:</p>
                        
                        <div style="background-color: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0; border-radius: 5px;">
                            <h1 style="letter-spacing: 5px; color: #2c3e50; margin: 0;">{code}</h1>
                        </div>
                        
                        <p><strong>Validade:</strong> Este código expira em 10 minutos</p>
                        
                        <p style="color: #7f8c8d; font-size: 14px;">
                            Se você não solicitou este código, por favor ignore este email.
                        </p>
                        
                        <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 20px 0;">
                        
                        <p style="color: #7f8c8d; font-size: 12px;">
                            Petitio - Sistema de Gestão de Petições
                        </p>
                    </div>
                </body>
            </html>
            """
            
            response = client.emails.send({
                "from": "noreply@petitio.com.br",
                "to": user_email,
                "subject": "Código de Autenticação em Dois Fatores",
                "html": html_content
            })
            
            if response.get("id"):
                current_app.logger.info(f"Email 2FA enviado com sucesso para {user_email}")
                return True
            else:
                current_app.logger.error(f"Erro ao enviar 2FA para {user_email}: {response}")
                return False
                
        except Exception as e:
            current_app.logger.error(f"Erro ao enviar email 2FA para {user_email}: {str(e)}", exc_info=True)
            return False

    @staticmethod
    def send_2fa_enabled_notification(user_email: str, user_name: str, method: str) -> bool:
        """
        Notifica usuário que 2FA foi ativado
        
        Args:
            user_email: Email do usuário
            user_name: Nome do usuário
            method: Método ativado ('email' ou 'totp')
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        client = EmailService._get_resend_client()
        if not client:
            current_app.logger.warning(f"Não foi possível notificar {user_email}: Resend não configurado")
            return False

        try:
            method_name = "Email" if method == "email" else "Aplicativo Autenticador (TOTP)"
            
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #27ae60;">✓ Autenticação em Dois Fatores Ativada</h2>
                        
                        <p>Olá {user_name},</p>
                        
                        <p>Sua conta agora está protegida com autenticação em dois fatores!</p>
                        
                        <div style="background-color: #e8f8f5; padding: 15px; margin: 20px 0; border-left: 4px solid #27ae60; border-radius: 3px;">
                            <p><strong>Método ativado:</strong> {method_name}</p>
                        </div>
                        
                        <h3>O que isso significa?</h3>
                        <ul>
                            <li>Sua conta está mais segura</li>
                            <li>Você precisará de um segundo fator para fazer login</li>
                            <li>Apenas você terá acesso à sua conta</li>
                        </ul>
                        
                        <h3>Códigos de Backup</h3>
                        <p>Você recebeu 10 códigos de backup. Guarde-os em um local seguro. Se perder acesso ao seu {method_name}, pode usá-los para fazer login.</p>
                        
                        <p style="color: #7f8c8d; font-size: 14px;">
                            Se você não ativou a autenticação em dois fatores, por favor entre em contato conosco imediatamente.
                        </p>
                        
                        <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 20px 0;">
                        
                        <p style="color: #7f8c8d; font-size: 12px;">
                            Petitio - Sistema de Gestão de Petições
                        </p>
                    </div>
                </body>
            </html>
            """
            
            response = client.emails.send({
                "from": "noreply@petitio.com.br",
                "to": user_email,
                "subject": "Autenticação em Dois Fatores Ativada",
                "html": html_content
            })
            
            if response.get("id"):
                current_app.logger.info(f"Notificação 2FA ativado enviada para {user_email}")
                return True
            else:
                current_app.logger.error(f"Erro ao notificar {user_email}: {response}")
                return False
                
        except Exception as e:
            current_app.logger.error(f"Erro ao enviar notificação 2FA para {user_email}: {str(e)}", exc_info=True)
            return False

    @staticmethod
    def send_2fa_disabled_notification(user_email: str, user_name: str) -> bool:
        """
        Notifica usuário que 2FA foi desativado
        
        Args:
            user_email: Email do usuário
            user_name: Nome do usuário
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        client = EmailService._get_resend_client()
        if not client:
            current_app.logger.warning(f"Não foi possível notificar {user_email}: Resend não configurado")
            return False

        try:
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #e74c3c;">Autenticação em Dois Fatores Desativada</h2>
                        
                        <p>Olá {user_name},</p>
                        
                        <p>A autenticação em dois fatores foi desativada em sua conta.</p>
                        
                        <div style="background-color: #fadbd8; padding: 15px; margin: 20px 0; border-left: 4px solid #e74c3c; border-radius: 3px;">
                            <p><strong>Ação:</strong> 2FA foi removida de sua conta</p>
                        </div>
                        
                        <p style="color: #e74c3c; font-weight: bold;">
                            ⚠️ Sua conta agora é menos segura. Recomendamos reativar a autenticação em dois fatores.
                        </p>
                        
                        <p style="color: #7f8c8d; font-size: 14px;">
                            Se você não desativou a autenticação em dois fatores, por favor entre em contato conosco imediatamente.
                        </p>
                        
                        <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 20px 0;">
                        
                        <p style="color: #7f8c8d; font-size: 12px;">
                            Petitio - Sistema de Gestão de Petições
                        </p>
                    </div>
                </body>
            </html>
            """
            
            response = client.emails.send({
                "from": "noreply@petitio.com.br",
                "to": user_email,
                "subject": "Autenticação em Dois Fatores Desativada",
                "html": html_content
            })
            
            if response.get("id"):
                current_app.logger.info(f"Notificação 2FA desativado enviada para {user_email}")
                return True
            else:
                current_app.logger.error(f"Erro ao notificar {user_email}: {response}")
                return False
                
        except Exception as e:
            current_app.logger.error(f"Erro ao enviar notificação 2FA desativado para {user_email}: {str(e)}", exc_info=True)
            return False


# Gerar código de 6 dígitos para 2FA por email
def generate_email_2fa_code() -> str:
    """Gera código numérico de 6 dígitos para 2FA por email"""
    import random
    return ''.join(str(random.randint(0, 9)) for _ in range(6))
