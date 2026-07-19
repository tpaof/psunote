import flask
import os
from datetime import datetime, timezone

import models
import forms


app = flask.Flask(__name__)
app.config["SECRET_KEY"] = "This is secret key"
app.config[
    "SQLALCHEMY_DATABASE_URI"
] = os.environ.get(
    "DATABASE_URL", "postgresql://coe:CoEpasswd@localhost:5432/coedb"
)

models.init_app(app)


@app.route("/")
def index():
    db = models.db
    notes = db.session.execute(
        db.select(models.Note).order_by(models.Note.title)
    ).scalars().all()
    return flask.render_template(
        "index.html",
        notes=notes,
        delete_form=forms.DeleteForm(),
    )


def update_note_from_form(note, form):
    note.title = form.title.data
    note.description = form.description.data

    db = models.db
    tags = []
    for tag_name in form.tags.data:
        tag = db.session.execute(
            db.select(models.Tag).where(models.Tag.name == tag_name)
        ).scalar_one_or_none()

        if tag is None:
            tag = models.Tag(name=tag_name)
            db.session.add(tag)

        tags.append(tag)

    note.tags = tags


@app.route("/notes/create", methods=["GET", "POST"])
def notes_create():
    form = forms.NoteForm()
    if form.validate_on_submit():
        db = models.db
        note = models.Note()
        update_note_from_form(note, form)
        db.session.add(note)
        db.session.commit()

        flask.flash("Note created successfully.", "success")
        return flask.redirect(flask.url_for("index"))

    return flask.render_template(
        "notes-create.html",
        form=form,
    )


@app.route("/notes/<int:note_id>/edit", methods=["GET", "POST"])
def notes_edit(note_id):
    db = models.db
    note = db.get_or_404(models.Note, note_id)
    form = forms.NoteForm(obj=note)

    if flask.request.method == "GET":
        form.tags.data = [tag.name for tag in note.tags]

    if form.validate_on_submit():
        update_note_from_form(note, form)
        note.updated_date = datetime.now(timezone.utc)
        db.session.commit()
        flask.flash("Note updated successfully.", "success")
        return flask.redirect(flask.url_for("index"))

    return flask.render_template(
        "notes-create.html",
        form=form,
        heading="Edit Note",
        submit_label="Save",
    )


@app.route("/notes/<int:note_id>/delete", methods=["POST"])
def notes_delete(note_id):
    form = forms.DeleteForm()
    if not form.validate_on_submit():
        flask.abort(400)

    db = models.db
    note = db.get_or_404(models.Note, note_id)
    note.tags.clear()
    db.session.delete(note)
    db.session.commit()
    flask.flash("Note deleted successfully.", "success")
    return flask.redirect(flask.url_for("index"))


@app.route("/tags/<tag_name>")
def tags_view(tag_name):
    db = models.db
    tag = (
        db.session.execute(db.select(models.Tag).where(models.Tag.name == tag_name))
        .scalar_one_or_none()
    )
    if tag is None:
        flask.abort(404)

    notes = db.session.execute(
        db.select(models.Note).where(models.Note.tags.any(id=tag.id))
    ).scalars().all()

    return flask.render_template(
        "tags-view.html",
        tag=tag,
        tag_name=tag_name,
        notes=notes,
        delete_form=forms.DeleteForm(),
    )


@app.route("/tags/<int:tag_id>/edit", methods=["GET", "POST"])
def tags_edit(tag_id):
    db = models.db
    tag = db.get_or_404(models.Tag, tag_id)
    form = forms.TagForm(obj=tag)

    if form.validate_on_submit():
        tag_name = form.name.data
        duplicate = db.session.execute(
            db.select(models.Tag).where(
                models.Tag.name == tag_name, models.Tag.id != tag.id
            )
        ).scalar_one_or_none()

        if duplicate is not None:
            form.name.errors.append("This tag already exists.")
        else:
            tag.name = tag_name
            db.session.commit()
            flask.flash("Tag updated successfully.", "success")
            return flask.redirect(flask.url_for("tags_view", tag_name=tag.name))

    return flask.render_template("tags-edit.html", form=form, tag=tag)


@app.route("/tags/<int:tag_id>/delete", methods=["POST"])
def tags_delete(tag_id):
    form = forms.DeleteForm()
    if not form.validate_on_submit():
        flask.abort(400)

    db = models.db
    tag = db.get_or_404(models.Tag, tag_id)
    tag.notes.clear()
    db.session.delete(tag)
    db.session.commit()
    flask.flash("Tag deleted successfully.", "success")
    return flask.redirect(flask.url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
