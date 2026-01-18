import re
from datetime import datetime

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.billing.decorators import subscription_required
from app.clients import bp
from app.clients.forms import ClientForm
from app.decorators import lawyer_required
from app.models import Client, Dependent, Estado, User
from app.office.utils import can_access_record, filter_by_office_member, get_office_user_ids
from app.utils.audit import AuditManager
from app.utils.pagination import PaginationHelper


def sanitize_cpf_cnpj(value: str) -> str:
    """Remove caracteres não numéricos do CPF/CNPJ para comparação."""
    if not value:
        return ""
    return re.sub(r"[^0-9]", "", value)


def check_duplicate_cpf_cnpj(cpf_cnpj: str, exclude_client_id: int = None) -> Client | None:
    """
    Verifica se já existe um cliente com o mesmo CPF/CNPJ no escopo do escritório.
    
    Prioridade de escopo:
    1. Se usuário pertence a um escritório, busca por office_id
    2. Senão, busca por lawyer_id (advogado individual)
    
    Args:
        cpf_cnpj: CPF ou CNPJ a verificar
        exclude_client_id: ID do cliente a excluir da busca (para edição)
    
    Returns:
        Client existente se encontrado, None caso contrário
    """
    if not cpf_cnpj:
        return None
    
    sanitized = sanitize_cpf_cnpj(cpf_cnpj)
    if len(sanitized) < 11:  # CPF mínimo tem 11 dígitos
        return None
    
    # Determinar escopo: escritório ou advogado individual
    if current_user.office_id:
        # Buscar por office_id (prioridade) ou por advogados do escritório (fallback)
        office_user_ids = get_office_user_ids()
        query = Client.query.filter(
            db.or_(
                Client.office_id == current_user.office_id,
                Client.lawyer_id.in_(office_user_ids)
            )
        )
    else:
        # Advogado individual: buscar apenas seus próprios clientes
        query = Client.query.filter(Client.lawyer_id == current_user.id)
    
    # Excluir o próprio cliente na edição
    if exclude_client_id:
        query = query.filter(Client.id != exclude_client_id)
    
    # Buscar clientes com CPF/CNPJ similar (comparando apenas números)
    existing_clients = query.all()
    
    for client in existing_clients:
        if sanitize_cpf_cnpj(client.cpf_cnpj) == sanitized:
            return client
    
    return None


@bp.route("/")
@login_required
@lawyer_required
@subscription_required
def index():
    search = request.args.get("search", "")

    # Filtrar por escritório se o usuário pertence a um
    query = filter_by_office_member(Client, "lawyer_id").order_by(
        Client.created_at.desc()
    )

    # Paginação padronizada
    pagination = PaginationHelper(query=query, per_page=20, filters={"search": search})

    return render_template(
        "clients/index.html",
        title="Clientes",
        clients=pagination.paginated,
        pagination=pagination.to_dict(),
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
@subscription_required
def new():
    form = ClientForm()

    # Populate estado choices from database
    estados = Estado.query.order_by(Estado.nome).all()
    form.uf.choices = [("", "Selecione...")] + [(e.sigla, e.nome) for e in estados]

    if form.validate_on_submit():
        # Verificar duplicidade de CPF/CNPJ
        existing_client = check_duplicate_cpf_cnpj(form.cpf_cnpj.data)
        if existing_client:
            flash(
                f"Já existe um cliente cadastrado com este CPF/CNPJ: {existing_client.full_name}. "
                "Verifique os dados ou acesse o cadastro existente.",
                "warning"
            )
            return render_template("clients/form.html", title="Novo cliente", form=form)
        
        client = Client(
            office_id=current_user.office_id,  # Vincula ao escritório (pode ser None para advogado individual)
            lawyer_id=current_user.id,
            full_name=form.full_name.data,
            rg=form.rg.data,
            cpf_cnpj=form.cpf_cnpj.data,
            civil_status=form.civil_status.data,
            birth_date=form.birth_date.data,
            profession=form.profession.data,
            nationality=form.nationality.data,
            birth_place=form.birth_place.data,
            mother_name=form.mother_name.data,
            father_name=form.father_name.data,
            address_type=form.address_type.data,
            cep=form.cep.data,
            street=form.street.data,
            number=form.number.data,
            complement=form.complement.data,
            neighborhood=form.neighborhood.data,
            city=form.city.data,
            uf=form.uf.data,
            landline_phone=form.landline_phone.data,
            email=form.email.data,
            mobile_phone=form.mobile_phone.data,
            lgbt_declared=form.lgbt_declared.data,
            has_disability=form.has_disability.data,
            disability_types=(
                ",".join(form.disability_types.data)
                if form.disability_types.data
                else None
            ),
            is_pregnant_postpartum=form.is_pregnant_postpartum.data,
            delivery_date=form.delivery_date.data,
        )

        db.session.add(client)
        db.session.flush()  # Get the client ID

        # Adicionar advogado atual como advogado principal na relação muitos-para-muitos
        client.add_lawyer(current_user, is_primary=True)

        # Add dependents
        for dependent_form in form.dependents:
            if dependent_form.full_name.data:
                dependent = Dependent(
                    client_id=client.id,
                    full_name=dependent_form.full_name.data,
                    relationship=dependent_form.relationship.data,
                    birth_date=dependent_form.birth_date.data,
                    cpf=dependent_form.cpf.data,
                )
                db.session.add(dependent)

        db.session.commit()
        flash("Cliente cadastrado com sucesso!", "success")

        # Log de auditoria para criação de cliente
        AuditManager.log_client_change(
            client,
            "create",
            new_values={
                "full_name": client.full_name,
                "email": client.email,
                "cpf_cnpj": client.cpf_cnpj,
                "mobile_phone": client.mobile_phone,
                "profession": client.profession,
                "city": client.city,
                "uf": client.uf,
            },
        )

        return redirect(url_for("clients.index"))

    return render_template("clients/form.html", title="Novo cliente", form=form)


@bp.route("/<int:id>")
@login_required
@subscription_required
def view(id):
    client = Client.query.get_or_404(id)
    # Verificar se pode acessar (mesmo escritório ou dono)
    if not can_access_record(client, "lawyer_id"):
        abort(403)
    return render_template(
        "clients/view.html", title=f"Cliente: {client.full_name}", client=client
    )


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
@subscription_required
def edit(id):
    client = Client.query.get_or_404(id)
    # Verificar se pode acessar (mesmo escritório ou dono)
    if not can_access_record(client, "lawyer_id"):
        abort(403)
    form = ClientForm(obj=client)

    # Populate estado choices from database
    estados = Estado.query.order_by(Estado.nome).all()
    form.uf.choices = [("", "Selecione...")] + [(e.sigla, e.nome) for e in estados]

    if form.validate_on_submit():
        # Verificar duplicidade de CPF/CNPJ (excluindo o próprio cliente)
        if form.cpf_cnpj.data != client.cpf_cnpj:
            existing_client = check_duplicate_cpf_cnpj(form.cpf_cnpj.data, exclude_client_id=client.id)
            if existing_client:
                flash(
                    f"Já existe outro cliente cadastrado com este CPF/CNPJ: {existing_client.full_name}. "
                    "Verifique os dados.",
                    "warning"
                )
                return render_template(
                    "clients/form.html",
                    title=f"Editar: {client.full_name}",
                    form=form,
                    client=client,
                )
        
        # Capturar valores antigos para auditoria
        old_values = {
            "full_name": client.full_name,
            "email": client.email,
            "cpf_cnpj": client.cpf_cnpj,
            "mobile_phone": client.mobile_phone,
            "profession": client.profession,
            "civil_status": client.civil_status,
            "cep": client.cep,
            "street": client.street,
            "city": client.city,
            "uf": client.uf,
            "neighborhood": client.neighborhood,
        }

        form.populate_obj(client)
        client.disability_types = (
            ",".join(form.disability_types.data) if form.disability_types.data else None
        )
        client.updated_at = datetime.utcnow()

        # Remove existing dependents
        for dependent in client.dependents:
            db.session.delete(dependent)

        # Add new dependents
        for dependent_form in form.dependents:
            if dependent_form.full_name.data:
                dependent = Dependent(
                    client_id=client.id,
                    full_name=dependent_form.full_name.data,
                    relationship=dependent_form.relationship.data,
                    birth_date=dependent_form.birth_date.data,
                    cpf=dependent_form.cpf.data,
                )
                db.session.add(dependent)

        db.session.commit()
        flash("Cliente atualizado com sucesso!", "success")

        # Capturar valores novos para auditoria
        new_values = {
            "full_name": client.full_name,
            "email": client.email,
            "cpf_cnpj": client.cpf_cnpj,
            "mobile_phone": client.mobile_phone,
            "profession": client.profession,
            "civil_status": client.civil_status,
            "cep": client.cep,
            "street": client.street,
            "city": client.city,
            "uf": client.uf,
            "neighborhood": client.neighborhood,
        }

        # Identificar campos alterados
        changed_fields = []
        for key in old_values:
            if old_values[key] != new_values[key]:
                changed_fields.append(key)

        # Log de auditoria
        if changed_fields:
            AuditManager.log_client_change(
                client, "update", old_values, new_values, changed_fields
            )

        return redirect(url_for("clients.view", id=client.id))

    elif request.method == "GET":
        # Populate disability types
        if client.disability_types:
            form.disability_types.data = client.disability_types.split(",")

        # Populate dependents
        for dependent in client.dependents:
            dependent_form = form.dependents.append_entry()
            dependent_form.full_name.data = dependent.full_name
            dependent_form.relationship.data = dependent.relationship
            dependent_form.birth_date.data = dependent.birth_date
            dependent_form.cpf.data = dependent.cpf

    return render_template(
        "clients/form.html",
        title=f"Editar: {client.full_name}",
        form=form,
        client=client,
    )


@bp.route("/<int:id>/add-lawyer", methods=["POST"])
@login_required
@subscription_required
def add_lawyer(id):
    """Adiciona um advogado ao cliente"""
    client = Client.query.filter_by(id=id).first_or_404()

    # Verificar se o usuário atual tem acesso a este cliente
    if not client.has_lawyer(current_user) and client.lawyer_id != current_user.id:
        abort(403)

    lawyer_email = request.form.get("lawyer_email")
    specialty = request.form.get("specialty")

    if not lawyer_email:
        flash("Email do advogado é obrigatório", "danger")
        return redirect(url_for("clients.view", id=id))

    # Buscar advogado por email
    lawyer = User.query.filter_by(email=lawyer_email).first()

    if not lawyer:
        flash("Advogado não encontrado com este email", "danger")
        return redirect(url_for("clients.view", id=id))

    if lawyer.user_type not in ["advogado", "escritorio"]:
        flash("Este usuário não é um advogado", "danger")
        return redirect(url_for("clients.view", id=id))

    if client.has_lawyer(lawyer):
        flash("Este advogado já está associado ao cliente", "warning")
        return redirect(url_for("clients.view", id=id))

    # Adicionar advogado
    client.add_lawyer(lawyer, specialty=specialty)
    db.session.commit()

    flash(
        f"Advogado {lawyer.full_name or lawyer.username} adicionado com sucesso!",
        "success",
    )
    return redirect(url_for("clients.view", id=id))


@bp.route("/<int:id>/remove-lawyer/<int:lawyer_id>", methods=["POST"])
@login_required
@subscription_required
def remove_lawyer(id, lawyer_id):
    """Remove um advogado do cliente"""
    client = Client.query.filter_by(id=id).first_or_404()

    # Verificar se o usuário atual tem acesso a este cliente
    if not client.has_lawyer(current_user) and client.lawyer_id != current_user.id:
        abort(403)

    # Não permitir remover o advogado principal
    if lawyer_id == client.lawyer_id:
        flash("Não é possível remover o advogado principal", "danger")
        return redirect(url_for("clients.view", id=id))

    lawyer = User.query.get_or_404(lawyer_id)

    if not client.has_lawyer(lawyer):
        flash("Este advogado não está associado ao cliente", "warning")
        return redirect(url_for("clients.view", id=id))

    # Remover advogado
    client.remove_lawyer(lawyer)
    db.session.commit()

    flash(
        f"Advogado {lawyer.full_name or lawyer.username} removido com sucesso!",
        "success",
    )
    return redirect(url_for("clients.view", id=id))


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
@subscription_required
def delete(id):
    client = Client.query.filter_by(id=id, lawyer_id=current_user.id).first_or_404()
    db.session.delete(client)
    db.session.commit()
    flash("Cliente excluído com sucesso!", "success")
    return redirect(url_for("clients.index"))
