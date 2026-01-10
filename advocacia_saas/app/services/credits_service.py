"""
Serviço para gerenciamento de créditos de IA.
Inclui renovação mensal automática baseada nos planos.
"""
from datetime import datetime, timezone, timedelta
from app import db
from app.models import User, Feature, UserCredits, CreditTransaction
from sqlalchemy import text


class CreditsService:
    """Serviço para gerenciamento de créditos de IA"""

    @staticmethod
    def get_monthly_credits_for_plan(user):
        """
        Obtém a quantidade de créditos mensais do plano do usuário.
        
        Args:
            user: Objeto User
            
        Returns:
            int: Quantidade de créditos mensais (0 se não tiver)
        """
        if not user.billing_plan:
            return 0
        
        return user.get_monthly_credits() or 0

    @staticmethod
    def add_monthly_credits(user):
        """
        Adiciona créditos mensais ao usuário baseado no seu plano.
        
        Args:
            user: Objeto User
            
        Returns:
            tuple: (credits_added, new_balance) ou (0, current_balance) se não tiver direito
        """
        monthly_credits = CreditsService.get_monthly_credits_for_plan(user)
        
        if monthly_credits <= 0:
            current_balance = user.credits.balance if user.credits else 0
            return (0, current_balance)
        
        # Garante que o usuário tem registro de créditos
        if not user.credits:
            user.credits = UserCredits(user_id=user.id, balance=0)
            db.session.add(user.credits)
        
        # Adiciona os créditos
        user.credits.balance += monthly_credits
        
        # Registra a transação
        transaction = CreditTransaction(
            user_id=user.id,
            amount=monthly_credits,
            transaction_type="monthly_renewal",
            description=f"Renovação mensal de créditos - {user.billing_plan.name}",
            balance_after=user.credits.balance,
        )
        db.session.add(transaction)
        db.session.commit()
        
        return (monthly_credits, user.credits.balance)

    @staticmethod
    def process_monthly_renewals():
        """
        Processa a renovação mensal de créditos para todos os usuários elegíveis.
        Deve ser chamado por um job/cron no início de cada mês.
        
        Returns:
            dict: Resultado do processamento
        """
        results = {
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "total_credits_added": 0,
            "users_renewed": [],
        }
        
        # Busca usuários com assinatura ativa que têm direito a créditos mensais
        users_with_credits = db.session.execute(
            text("""
                SELECT u.id, u.email, u.full_name, pf.feature_limit as monthly_credits
                FROM "user" u
                JOIN billing_plans bp ON u.billing_plan_id = bp.id
                JOIN plan_features pf ON bp.id = pf.plan_id
                JOIN features f ON pf.feature_id = f.id
                WHERE f.slug = 'ai_credits_monthly'
                  AND u.subscription_status = 'active'
                  AND pf.feature_limit > 0
            """)
        ).fetchall()
        
        for row in users_with_credits:
            try:
                user = User.query.get(row.id)
                if not user:
                    results["skipped"] += 1
                    continue
                
                # Verifica se já renovou este mês
                current_month = datetime.now(timezone.utc).strftime('%Y-%m')
                last_renewal = CreditTransaction.query.filter(
                    CreditTransaction.user_id == user.id,
                    CreditTransaction.transaction_type == "monthly_renewal",
                    db.func.to_char(CreditTransaction.created_at, 'YYYY-MM') == current_month
                ).first()
                
                if last_renewal:
                    results["skipped"] += 1
                    continue
                
                # Adiciona os créditos
                credits_added, new_balance = CreditsService.add_monthly_credits(user)
                
                if credits_added > 0:
                    results["processed"] += 1
                    results["total_credits_added"] += credits_added
                    results["users_renewed"].append({
                        "user_id": user.id,
                        "email": user.email,
                        "credits_added": credits_added,
                        "new_balance": new_balance,
                    })
                else:
                    results["skipped"] += 1
                    
            except Exception as e:
                results["errors"] += 1
                print(f"Erro ao renovar créditos para usuário {row.id}: {e}")
        
        return results

    @staticmethod
    def get_user_credit_history(user_id, limit=50):
        """
        Retorna o histórico de transações de créditos de um usuário.
        
        Args:
            user_id: ID do usuário
            limit: Número máximo de transações
            
        Returns:
            list: Lista de transações
        """
        return CreditTransaction.query.filter_by(user_id=user_id)\
            .order_by(CreditTransaction.created_at.desc())\
            .limit(limit)\
            .all()

    @staticmethod
    def check_and_deduct_credits(user, amount=1):
        """
        Verifica se o usuário tem créditos suficientes e deduz.
        
        Args:
            user: Objeto User
            amount: Quantidade de créditos a deduzir
            
        Returns:
            tuple: (success, message, remaining_balance)
        """
        if not user.credits:
            return (False, "Usuário não possui créditos.", 0)
        
        if user.credits.balance < amount:
            return (False, f"Créditos insuficientes. Saldo: {user.credits.balance}", user.credits.balance)
        
        user.credits.balance -= amount
        
        transaction = CreditTransaction(
            user_id=user.id,
            amount=-amount,
            transaction_type="usage",
            description="Uso de crédito IA",
            balance_after=user.credits.balance,
        )
        db.session.add(transaction)
        db.session.commit()
        
        return (True, "Crédito deduzido com sucesso.", user.credits.balance)


def run_monthly_credits_job():
    """
    Função para ser chamada pelo job/cron de renovação mensal.
    Pode ser usado com APScheduler, Celery, ou chamado manualmente.
    """
    print(f"[{datetime.now()}] Iniciando renovação mensal de créditos...")
    
    results = CreditsService.process_monthly_renewals()
    
    print(f"[{datetime.now()}] Renovação concluída:")
    print(f"  - Processados: {results['processed']}")
    print(f"  - Ignorados: {results['skipped']}")
    print(f"  - Erros: {results['errors']}")
    print(f"  - Total de créditos adicionados: {results['total_credits_added']}")
    
    return results
