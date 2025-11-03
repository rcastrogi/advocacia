import os
from urllib.parse import urlparse

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename

from app import db
from app.auth import bp
from app.auth.forms import LoginForm, ProfileForm, RegistrationForm
from app.models import User


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get("next")
            if not next_page or urlparse(next_page).netloc != "":
                next_page = url_for("main.dashboard")
            return redirect(next_page)
        flash("Email ou senha inválidos", "error")
    return render_template("auth/login.html", title="Login", form=form)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
            oab_number=form.oab_number.data,
            phone=form.phone.data,
            user_type=form.user_type.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Cadastro realizado com sucesso!", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", title="Cadastro", form=form)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(current_user.email)
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data
        current_user.email = form.email.data
        current_user.oab_number = form.oab_number.data
        current_user.phone = form.phone.data
        db.session.commit()
        flash("Perfil atualizado com sucesso!", "success")
        return redirect(url_for("auth.profile"))
    elif request.method == "GET":
        form.full_name.data = current_user.full_name
        form.email.data = current_user.email
        form.oab_number.data = current_user.oab_number
        form.phone.data = current_user.phone
    return render_template("auth/profile.html", title="Perfil", form=form)


@bp.route("/upload_logo", methods=["POST"])
@login_required
def upload_logo():
    if "logo" not in request.files:
        flash("Nenhum arquivo selecionado", "error")
        return redirect(url_for("auth.profile"))

    file = request.files["logo"]
    if file.filename == "":
        flash("Nenhum arquivo selecionado", "error")
        return redirect(url_for("auth.profile"))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add user id to filename to avoid conflicts
        name, ext = os.path.splitext(filename)
        filename = f"{current_user.id}_{name}{ext}"

        file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        # Remove old logo if exists
        if current_user.logo_filename:
            old_path = os.path.join(
                current_app.config["UPLOAD_FOLDER"], current_user.logo_filename
            )
            if os.path.exists(old_path):
                os.remove(old_path)

        current_user.logo_filename = filename
        db.session.commit()
        flash("Logo atualizado com sucesso!", "success")
    else:
        flash("Formato de arquivo não permitido. Use PNG, JPG ou JPEG.", "error")

    return redirect(url_for("auth.profile"))


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
