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

    @staticmethod
    def send_office_invite(
        invite_email: str,
        invite_url: str,
        office_name: str,
        inviter_name: str,
        role_name: str,
        role_description: str,
        expires_in_days: int,
        expires_at: str,
        has_account: bool
    ) -> bool:
        """
        Envia email de convite para escritório
        
        Args:
            invite_email: Email do convidado
            invite_url: URL para aceitar o convite
            office_name: Nome do escritório
            inviter_name: Nome de quem convidou
            role_name: Nome da função (Advogado, Secretária, etc)
            role_description: Descrição da função
            expires_in_days: Dias até expirar
            expires_at: Data de expiração formatada
            has_account: Se o convidado já tem conta
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        client = EmailService._get_resend_client()
        if not client:
            current_app.logger.warning(f"Não foi possível enviar convite para {invite_email}: Resend não configurado")
            return False

        try:
            # Instruções baseadas em ter ou não conta
            if has_account:
                instructions = """
                    <li>Faça login na plataforma</li>
                    <li>Clique no botão "Aceitar Convite" acima</li>
                """
            else:
                instructions = f"""
                    <li>Crie sua conta no Petitio (se ainda não tiver)</li>
                    <li>Use o email <strong>{invite_email}</strong> no cadastro</li>
                    <li>Faça login na plataforma</li>
                    <li>Clique no botão "Aceitar Convite" acima</li>
                """

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Convite para Escritório</title>
            </head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f4; margin: 0; padding: 0;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <!-- Header -->
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                        <h1 style="color: #fff; margin: 0; font-size: 28px;">
                            📧 Convite para Escritório
                        </h1>
                    </div>

                    <!-- Content -->
                    <div style="background-color: #fff; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                        <p style="font-size: 16px;">Olá,</p>

                        <p style="font-size: 16px;">
                            <strong>{inviter_name}</strong> convidou você para fazer parte do escritório 
                            <strong>{office_name}</strong> no <strong>Petitio</strong>.
                        </p>

                        <!-- Role Info -->
                        <div style="background-color: #e8f4fd; padding: 20px; border-left: 4px solid #667eea; margin: 25px 0; border-radius: 0 8px 8px 0;">
                            <h3 style="margin-top: 0; color: #667eea; font-size: 18px;">
                                👤 Sua função será:
                            </h3>
                            <p style="margin-bottom: 0; font-size: 16px;">
                                <strong>{role_name}</strong>
                                <br><small style="color: #666;">{role_description}</small>
                            </p>
                        </div>

                        <!-- CTA Button -->
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{invite_url}" 
                               style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #fff; padding: 15px 40px; text-decoration: none; border-radius: 50px; font-size: 16px; font-weight: bold; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);">
                                Aceitar Convite
                            </a>
                        </div>

                        <p style="font-size: 14px; color: #666; text-align: center;">
                            Ou copie e cole este link no seu navegador:<br>
                            <a href="{invite_url}" style="color: #667eea; word-break: break-all;">{invite_url}</a>
                        </p>

                        <!-- Instructions -->
                        <div style="background-color: #fff8e6; padding: 15px; border-radius: 8px; margin: 25px 0;">
                            <h4 style="margin-top: 0; color: #856404;">
                                💡 Como aceitar o convite:
                            </h4>
                            <ol style="margin-bottom: 0; color: #856404; padding-left: 20px;">
                                {instructions}
                            </ol>
                        </div>

                        <!-- Expiration Warning -->
                        <p style="font-size: 14px; color: #dc3545; text-align: center;">
                            <strong>⏰ Atenção:</strong> Este convite expira em <strong>{expires_in_days} dias</strong> 
                            ({expires_at}).
                        </p>

                        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">

                        <p style="font-size: 14px; color: #666;">
                            Se você não esperava este convite ou não conhece o remetente, 
                            pode ignorar este email com segurança.
                        </p>

                        <p style="margin-bottom: 0;">
                            Atenciosamente,<br>
                            <strong>Equipe Petitio</strong>
                        </p>
                    </div>

                    <!-- Footer -->
                    <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
                        <p style="margin: 0;">
                            Este é um email automático. Não responda diretamente.
                        </p>
                        <p style="margin: 10px 0 0 0;">
                            © 2026 Petitio - Sistema de Gestão para Advogados
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            response = client.emails.send({
                "from": "noreply@petitio.com.br",
                "to": invite_email,
                "subject": f"📧 Convite para o escritório {office_name} - Petitio",
                "html": html_content
            })
            
            if response.get("id"):
                current_app.logger.info(f"Convite de escritório enviado para {invite_email}")
                return True
            else:
                current_app.logger.error(f"Erro ao enviar convite para {invite_email}: {response}")
                return False
                
        except Exception as e:
            current_app.logger.error(f"Erro ao enviar convite para {invite_email}: {str(e)}", exc_info=True)
            return False


# Gerar código de 6 dígitos para 2FA por email
def generate_email_2fa_code() -> str:
    """Gera código numérico de 6 dígitos para 2FA por email"""
    import random
    return ''.join(str(random.randint(0, 9)) for _ in range(6))
