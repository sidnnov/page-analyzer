from flask import (
    Flask,
    render_template,
    request,
    flash,
    get_flashed_messages,
    url_for,
    redirect,
)
from dotenv import load_dotenv
from page_analyzer import db
from page_analyzer import utils
import os


load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["DATABASE_URL"] = os.getenv("DATABASE_URL")


@app.errorhandler(404)
def page_not_found(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("errors/500.html"), 500


@app.route("/")
def index():
    return render_template("/index.html")


@app.route("/urls", methods=["POST"])
def add_url():
    url_with_form = request.form["url"].lower()
    error = utils.check_error(url_with_form)

    if error:
        return render_template(
            "/index.html",
            url=url_with_form,
            messages=error), 422

    correct_url = utils.normalize_url(url_with_form)
    conn = db.create_connection(app)
    id = db.get_id_if_exist(conn, correct_url)

    if id:
        db.close(conn)
        flash("Страница уже существует", "info")
        return redirect(url_for("get_url", id=id))

    data = db.save_url(conn, correct_url)
    db.close(conn)
    if data is None:
        return render_template("errors/500.html"), 500

    flash("Страница успешно добавлена", "success")
    return redirect(url_for("get_url", id=data.id))


@app.route("/urls", methods=["GET"])
def get_urls():
    conn = db.create_connection(app)
    data = db.get_urls_with_checks(conn)
    db.close(conn)
    if data == "error":
        return render_template("errors/500.html"), 500

    return render_template("urls.html", data=data)


@app.route("/urls/<id>", methods=["GET"])
def get_url(id):
    conn = db.create_connection(app)
    urls_data = db.get_url(conn, id)

    if not urls_data:
        db.close(conn)
        return render_template("errors/404.html"), 404

    check_data = db.get_check(conn, id)
    messages = get_flashed_messages(with_categories=True)
    db.close(conn)
    return render_template(
        "url.html",
        urls_id=urls_data.id,
        name=urls_data.name,
        urls_date=urls_data.created_at,
        checks_data=check_data,
        messages=messages,
    )


@app.route("/urls/<id>/checks", methods=["POST", "GET"])
def check_url(id):
    conn = db.create_connection(app)
    url = db.get_url_name(conn, id)
    data = utils.get_data_from_url(url)

    if data is None:
        db.close(conn)
        flash("Произошла ошибка при проверке", "danger")
        return redirect(url_for("get_url", id=id))

    status_code, data_html = data
    content = utils.get_content(data_html)
    db.save_check(conn, id, status_code, content)
    db.close(conn)
    flash("Страница успешно проверена", "success")
    return redirect(url_for("get_url", id=id))
