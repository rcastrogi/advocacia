"""
Rotas HTTP para o módulo de Clientes.

Este arquivo contém apenas a camada de apresentação (HTTP handlers),
delegando toda a lógica de negócio para o ClientService.
"""

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.billing.decorators import subscription_required
from app.clients import bp
from app.clients.forms import ClientForm
from app.clients.services import client_service
from app.decorators import lawyer_required
from app.models import Estado
from app.utils.pagination import PaginationHelper


def _get_estados_choices():
    """Retorna choices de estados para formulários."""
    estados = Estado.query.order_by(Estado.nome).all()
    return [("", "Selecione...")] + [(e.sigla, e.nome) for e in estados]


def _extract_form_data(form: ClientForm) -> dict:
    """Extrai dados do formulário para dicionário."""
    disability_types = None
    if form.disability_types.data:
        disability_types = ",".join(form.disability_types.data)

    return {
        "full_name": form.full_name.data,
        "rg": form.rg.data,
        "cpf_cnpj": form.cpf_cnpj.data,
        "civil_status": form.civil_status.data,
        "birth_date": form.birth_date.data,
        "profession": form.profession.data,
        "nationality": form.nationality.data,
        "birth_place": form.birth_place.data,
        "mother_name": form.mother_name.data,
        "father_name": form.father_name.data,
        "address_type": form.address_type.data,
        "cep": form.cep.data,
        "street": form.street.data,
        "number": form.number.data,
        "complement": form.complement.data,
        "neighborhood": form.neighborhood.data,
        "city": form.city.data,
        "uf": form.uf.data,
        "landline_phone": form.landline_phone.data,
        "email": form.email.data,
        "mobile_phone": form.mobile_phone.data,
        "lgbt_declared": form.lgbt_declared.data,
        "has_disability": form.has_disability.data,
        "disability_types": disability_types,
        "is_pregnant_postpartum": form.is_pregnant_postpartum.data,
        "delivery_date": form.delivery_date.data,
    }


def _extract_dependents_data(form: ClientForm) -> list:
    """Extrai dados de dependentes do formulário."""
    dependents = []
    for dep_form in form.dependents:
        if dep_form.full_name.data:
            dependents.append({
                "full_name": dep_form.full_name.data,
                "relationship": dep_form.relationship.data,
                "birth_date": dep_form.birth_date.data,
                "cpf": dep_form.cpf.data,
            })
    return dependents


# ==============================================================================
# ROTAS DE LISTAGEM
# ==============================================================================


@bp.route("/")
@login_required
@lawyer_required
@subscription_required
def index():
    """Lista de clientes."""
    search = request.args.get("search", "")

    query = client_service.list_clients(current_user)

    pagination = PaginationHelper(query=query, per_page=20, filters={"search": search})

    return render_template(
        "clients/index.html",
        title="Clientes",
        clients=pagination.paginated,
        pagination=pagination.to_dict(),
    )


# ==============================================================================
# ROTAS DE CRUD
# ==============================================================================


@bp.route("/new", methods=["GET", "POST"])
@login_required
@subscription_required
def new():
    """Criar novo cliente."""
    form = ClientForm()
    form.uf.choices = _get_estados_choices()

    if form.validate_on_submit():
        form_data = _extract_form_data(form)
        dependents_data = _extract_dependents_data(form)

        result = client_service.create_client(form_data, dependents_data, current_user)

        if not result.success:
            flash(result.error, result.error_type)
            return render_template("clients/form.html", title="Novo cliente", form=form)

        flash("Cliente cadastrado com sucesso!", "success")
        return redirect(url_for("clients.index"))

    return render_template("clients/form.html", title="Novo cliente", form=form)


@bp.route("/<int:id>")
@login_required
@subscription_required
def view(id):
    """Visualizar cliente."""
    result = client_service.get_client(id, current_user)

    if not result.success:
        abort(403)

    return render_template(
        "clients/view.html",
        title=f"Cliente: {result.data.full_name}",
        client=result.data,
    )


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
@subscription_required
def edit(id):
    """Editar cliente."""
    result = client_service.get_client(id, current_user)

    if not result.success:
        abort(403)

    client = result.data
    form = ClientForm(obj=client)
    form.uf.choices = _get_estados_choices()

    if form.validate_on_submit():
        form_data = _extract_form_data(form)
        dependents_data = _extract_dependents_data(form)

        result = client_service.update_client(id, form_data, dependents_data, current_user)

        if not result.success:
            flash(result.error, result.error_type)
            return render_template(
                "clients/form.html",
                title=f"Editar: {client.full_name}",
                form=form,
                client=client,
            )

        flash("Cliente atualizado com sucesso!", "success")
        return redirect(url_for("clients.view", id=client.id))

    elif request.method == "GET":
        # Populate disability types
        if client.disability_types:
            form.disability_types.data = client.disability_types.split(",")

        # Populate dependents
        for dependent in client.dependents:
            dep_form = form.dependents.append_entry()
            dep_form.full_name.data = dependent.full_name
            dep_form.relationship.data = dependent.relationship
            dep_form.birth_date.data = dependent.birth_date
            dep_form.cpf.data = dependent.cpf

    return render_template(
        "clients/form.html",
        title=f"Editar: {client.full_name}",
        form=form,
        client=client,
    )


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
@subscription_required
def delete(id):
    """Excluir cliente."""
    result = client_service.delete_client(id, current_user)

    if not result.success:
        flash(result.error, result.error_type)
        return redirect(url_for("clients.index"))

    flash("Cliente excluído com sucesso!", "success")
    return redirect(url_for("clients.index"))


# ==============================================================================
# ROTAS DE ADVOGADOS ASSOCIADOS
# ==============================================================================


@bp.route("/<int:id>/add-lawyer", methods=["POST"])
@login_required
@subscription_required
def add_lawyer(id):
    """Adiciona um advogado ao cliente."""
    lawyer_email = request.form.get("lawyer_email")
    specialty = request.form.get("specialty")

    result = client_service.add_lawyer_to_client(id, lawyer_email, specialty, current_user)

    if not result.success:
        flash(result.error, result.error_type)
    else:
        flash(f"Advogado {result.data['lawyer_name']} adicionado com sucesso!", "success")

    return redirect(url_for("clients.view", id=id))


@bp.route("/<int:id>/remove-lawyer/<int:lawyer_id>", methods=["POST"])
@login_required
@subscription_required
def remove_lawyer(id, lawyer_id):
    """Remove um advogado do cliente."""
    result = client_service.remove_lawyer_from_client(id, lawyer_id, current_user)

    if not result.success:
        flash(result.error, result.error_type)
    else:
        flash(f"Advogado {result.data['lawyer_name']} removido com sucesso!", "success")

    return redirect(url_for("clients.view", id=id))
