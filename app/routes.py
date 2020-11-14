from mobile_de.methods import surface_search, checker
from json import loads
from flask import (
    request,
    render_template,
    url_for,
    redirect,
    flash,
    get_flashed_messages,
    jsonify,
)
from app import app, db, bcrypt
from app.forms import LoginForm, RegisterForm, SearchForm
from app.models import User, Vehicle
from flask_login import login_user, current_user, logout_user, login_required

db.create_all()
db.session.commit()

def add_favorites(fav):
    find_dup = Vehicle.query.filter_by(
        image=fav["image"],
        title=fav["title"],
        price=fav["price"],
        reg=fav["reg"],
        mileage=fav["mileage"],
    ).first()
    if find_dup != None:
        current_favs = current_user.favorites
        if not str(find_dup.id) in current_favs.split("|"):
            if current_favs == "":
                current_user.favorites = current_favs + str(find_dup.id)
            else:
                current_user.favorites = current_favs + "|" + str(find_dup.id)
            db.session.commit()
        else:
            return False
    else:
        fav_db = Vehicle(
            url=fav["url"],
            image=fav["image"],
            title=fav["title"],
            price=fav["price"],
            reg=fav["reg"],
            mileage=fav["mileage"],
            user_added=current_user.id,
        )
        db.session.add(fav_db)
        db.session.flush()

        current_favs = current_user.favorites
        if current_favs == "":
            current_user.favorites = current_favs + str(fav_db.id)
        else:
            current_user.favorites = current_favs + "|" + str(fav_db.id)

        db.session.commit()

    return True

def get_favorites(last=False):
    if current_user.favorites == "":
        return ['']
    else:
        favorites = current_user.favorites.split("|")
        favs = []
        for i in favorites:
            fav = Vehicle.query.get(i)
            favs.append([
                    fav.url,
                    fav.title,
                    fav.price,
                    fav.reg,
                    fav.mileage,
                    fav.image,
                    fav.id,
                ])

    return [favs[-1]] if last else favs

def remove_favorite(id):
    current_favs = current_user.favorites

    favs_split = current_favs.split("|")
    favs_split.pop(favs_split.index(id))

    current_user.favorites = "|".join(favs_split)
    db.session.commit()

@app.route("/")
def home():
    return redirect(url_for("doorway"))


@app.route("/doorway")
def doorway():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    login_form = LoginForm()
    register_form = RegisterForm()
    return render_template(
        "doorway.html",
        page="enter",
        title="Enter",
        register_form=register_form,
        login_form=login_form,
    )


@app.route("/login", methods=["POST"])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        user = User.query.filter_by(email=login_form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, login_form.password.data):
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page) if next_page else redirect(url_for("dashboard"))
        else:
            flash(u"Incorrect password - email combination!", "login_error")
            return redirect(url_for("doorway"))
    flash(u"User not found!", "login_error")
    return redirect(url_for("doorway"))


@app.route("/register", methods=["POST"])
def register():
    register_form = RegisterForm()
    login_form = RegisterForm()
    if register_form.validate_on_submit():
        hashed_pass = bcrypt.generate_password_hash(login_form.password.data).decode(
            "utf-8"
        )
        user = User(
            name=register_form.name.data,
            email=register_form.email.data,
            password=hashed_pass,
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        next_page = request.args.get("next")
        return redirect(next_page) if next_page else redirect(url_for("dashboard"))
    flash(u"Invalid credentials provided!", "register_error")
    return redirect(url_for("doorway"))


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    title = "Dashboard - " + str(current_user.name)
    favs = get_favorites()
    search_form = SearchForm()
    return render_template(
        "dashboard.html", page="dash", title=title, search_form=search_form, favs=favs
    )


@app.route("/search", methods=["POST"])
@login_required
def search():
    try:
        results = surface_search(
            [
                request.form["manufacturer"],
                request.form["model"],
                request.form["price_from"],
                request.form["price_to"],
                request.form["reg_from"],
                request.form["reg_to"],
                request.form["mileage_from"],
                request.form["mileage_to"],
            ]
        )
    except AssertionError:
        results = []
        flash(
            u"Your search did not yield any results. Try changing the parameters.",
            "no_search_results",
        )
    return render_template(
        "results.html",
        results=results,
    )


@app.route("/add_to_favorites", methods=["POST"])
@login_required
def add_to_favorites():
    fav = loads(request.form.to_dict()["qSet"])
    status = add_favorites(fav)

    return render_template("favorites.html", favs=get_favorites(last=True)) if status else render_template("favorites.html", empty=True)

@app.route("/remove_from_favorites", methods=["POST"])
@login_required
def remove_from_favorites():
    id = request.form.to_dict()["id"].split("-")[1]
    remove_favorite(id)

    return render_template("favorites.html", favs=get_favorites())

@app.route("/check_changes", methods=["POST"])
@login_required
def check_changes():
    favs = get_favorites()
    links = [fav[0] for fav in favs]
    try:
        changes = checker(favs)
    except AssertionError:
        changes = [""]

    return render_template("changes.html", changes=changes)

@app.route("/update_database_changes", methods=["POST"])
@login_required
def update_database_changes():
    changed = request.form.to_dict()
    for i in range(int(len(changed)/2)):
        item = changed["data[%i][item]"%i]
        value = changed["data[%i][value]"%i]

        old_price = Vehicle.query.get(item).price
        Vehicle.query.get(item).price = int(old_price) + int(value)
        db.session.commit()

    return render_template("favorites.html", favs=get_favorites())
