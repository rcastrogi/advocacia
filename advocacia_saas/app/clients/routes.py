from datetime import datetime

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.clients import bp
from app.clients.forms import ClientForm
from app.models import Client, Dependent, Estado


@bp.route("/")
@login_required
def index():
    page = request.args.get("page", 1, type=int)
    clients = (
        Client.query.filter_by(lawyer_id=current_user.id)
        .order_by(Client.created_at.desc())
        .paginate(page=page, per_page=10, error_out=False)
    )
    return render_template("clients/index.html", title="Clientes", clients=clients)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    form = ClientForm()
    
    # Populate estado choices from database
    estados = Estado.query.order_by(Estado.nome).all()
    form.uf.choices = [("", "Selecione...")] + [(e.sigla, e.nome) for e in estados]
    
    if form.validate_on_submit():
        client = Client(
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
            disability_types=",".join(form.disability_types.data)
            if form.disability_types.data
            else None,
            is_pregnant_postpartum=form.is_pregnant_postpartum.data,
            delivery_date=form.delivery_date.data,
        )

        db.session.add(client)
        db.session.flush()  # Get the client ID

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
        return redirect(url_for("clients.index"))

    return render_template("clients/form.html", title="Novo cliente", form=form)


@bp.route("/<int:id>")
@login_required
def view(id):
    client = Client.query.filter_by(id=id, lawyer_id=current_user.id).first_or_404()
    return render_template(
        "clients/view.html", title=f"Cliente: {client.full_name}", client=client
    )


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    client = Client.query.filter_by(id=id, lawyer_id=current_user.id).first_or_404()
    form = ClientForm(obj=client)
    
    # Populate estado choices from database
    estados = Estado.query.order_by(Estado.nome).all()
    form.uf.choices = [("", "Selecione...")] + [(e.sigla, e.nome) for e in estados]

    if form.validate_on_submit():
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


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    client = Client.query.filter_by(id=id, lawyer_id=current_user.id).first_or_404()
    db.session.delete(client)
    db.session.commit()
    flash("Cliente excluído com sucesso!", "success")
    return redirect(url_for("clients.index"))
