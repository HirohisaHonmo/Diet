import random
from datetime import date, datetime, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .forms import LogBodyCompositionForm, SigninForm, SignupForm
from .models import BodyComposition, User, db

main = Blueprint("main", __name__)


@main.route("/")
def index():
    return render_template("index.html", current_user=current_user)


@main.route("/log_body_composition", methods=["GET", "POST"])
@login_required
def log_body_composition():
    user_id = current_user.id
    form = LogBodyCompositionForm()

    # フォーム入力時処理
    if form.validate_on_submit():
        log_date = form.date.data
        weight = form.weight.data
        body_fat = form.body_fat.data

        specified_date_log = BodyComposition.query.filter_by(
            date=form.date.data, user_id=user_id
        ).first()

        if specified_date_log:
            specified_date_log.weight = weight
            specified_date_log.body_fat = body_fat
        else:
            try:
                log = BodyComposition(
                    date=log_date, weight=weight, body_fat=body_fat, user_id=user_id
                )
                db.session.add(log)
            except Exception as e:
                flash(f"{str(e)}", "danger")
                return render_template(
                    "log_body_composition.html",
                    form=form,
                )

        try:
            db.session.commit()
            return redirect(url_for("main.index"))
        except Exception as e:
            db.session.rollback()
            flash(f"予期せぬエラーが発生しました。: {str(e)}", "danger")
            return render_template("log_body_composition.html", form=form)

    # フォーム初期値設定
    today = date.today()
    todays_log = BodyComposition.query.filter_by(date=today, user_id=user_id).first()

    if todays_log:
        form.weight.data = todays_log.weight
        form.body_fat.data = todays_log.body_fat
    else:
        last_registered_log = (
            BodyComposition.query.filter_by(user_id=user_id)
            .order_by(BodyComposition.date.desc())
            .first()
        )
        if last_registered_log:
            form.weight.data = last_registered_log.weight
            form.body_fat.data = last_registered_log.body_fat

    return render_template("log_body_composition.html", form=form)


@main.route("/signup", methods=["GET", "POST"])
def signup():
    form = SignupForm()

    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        log_date = form.date.data
        weight = form.weight.data
        body_fat = form.body_fat.data

        existing_user = User.query.filter_by(username=username).first()
        existing_email = User.query.filter_by(email=email).first()

        if existing_user:
            flash("別のユーザー名を入力してください。このユーザー名は既に登録されています。", "danger")
        elif existing_email:
            flash("別のメールアドレスを入力してください。このメールアドレスは既に登録されています。", "danger")
        else:
            user = User(username=username, email=email, password=password)
            db.session.add(user)
            db.session.commit()

            body_composition = BodyComposition(
                date=log_date, weight=weight, body_fat=body_fat, user_id=user.id
            )
            db.session.add(body_composition)
            db.session.commit()

            login_user(user)
            flash("アカウントが作成され、体重が登録されました。", "success")
            return redirect(url_for("main.index"))

    return render_template("signup.html", form=form, current_user=current_user)


@main.route("/signin", methods=["GET", "POST"])
def signin():
    form = SigninForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash("ログインに成功しました。", "success")
            return redirect(url_for("main.index"))
        else:
            flash("ログインに失敗しました。ユーザー名またはパスワードが誤っています。", "danger")

    return render_template("signin.html", form=form, current_user=current_user)


@main.route("/logout")
@login_required
def logout():
    logout_user()
    flash("ログアウトに成功しました。ご利用ありがとうございました。", "success")
    return redirect(url_for("main.index"))


@main.route("/get_body_composition_data", methods=["GET"])
def fetch_body_composition_data():
    if current_user.is_authenticated:
        user_id = current_user.id
        weight_data, body_fat_data, dates = get_body_composition_data(user_id)
    else:
        weight_data, body_fat_data, dates = generate_dummy_data()

    return jsonify(
        {"weight_data": weight_data, "body_fat_data": body_fat_data, "dates": dates}
    )


def get_body_composition_data(user_id):
    weight_data = []
    body_fat_data = []
    dates = []

    body_compositions = (
        BodyComposition.query.filter_by(user_id=user_id)
        .order_by(BodyComposition.date.asc())
        .all()
    )

    for body_composition in body_compositions:
        weight_data.append(body_composition.weight)
        body_fat_data.append(body_composition.body_fat)
        dates.append(body_composition.date.strftime("%Y-%m-%d"))

    return weight_data, body_fat_data, dates


def generate_dummy_data():
    duration = 365 * 1.5
    today = datetime.now()
    dummy_date = today - timedelta(days=int(duration))

    initial_weight = round(random.uniform(120, 150), 2)
    initial_body_fat = round(random.uniform(30, 40), 2)

    current_weight = initial_weight
    current_body_fat = initial_body_fat

    dates = []
    weight_data = []
    body_fat_data = []
    while dummy_date <= today:
        dates.append(dummy_date.strftime("%Y-%m-%d"))
        dummy_date += timedelta(days=1)

        weight_variation = round(random.uniform(-0.5, 0.3), 2)
        updated_weight = round(max(current_weight + weight_variation, 50), 2)
        weight_data.append(updated_weight)
        current_weight = updated_weight

        body_fat_variation = round(random.uniform(-0.4, 0.32), 2)
        updated_body_fat = round(max(current_body_fat + body_fat_variation, 5), 2)
        body_fat_data.append(updated_body_fat)
        current_body_fat = updated_body_fat

    return weight_data, body_fat_data, dates
