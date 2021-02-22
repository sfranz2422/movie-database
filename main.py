from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField, TextAreaField, ValidationError
import requests
import os
from dotenv import load_dotenv

load_dotenv('.env')
app = Flask(__name__)
SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY
Bootstrap(app)
API_KEY = os.getenv('API_KEY')

# CREATE DATABASE
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///my-top-ten-movies.db"
# Optional: But it will silence the deprecation warning in the console.
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# CREATE TABLE
class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=False, nullable=False)
    year = db.Column(db.String(250), nullable=True)
    description = db.Column(db.String(250), nullable=True)
    rating = db.Column(db.Float, nullable=True)
    ranking = db.Column(db.Integer, nullable=True)
    review = db.Column(db.String(250), nullable=True)
    img_url = db.Column(db.String(250), nullable=True)

    def __repr__(self):
        return f'<Movie {self.title}>'


db.create_all()


def ranking_check(form, field):
    print(form)
    print(field)

    all_movies = Movie.query.order_by(Movie.ranking).all()
    list_of_ranks = [int(mov.ranking) for mov in all_movies]
    print(list_of_ranks)
    print(f"This is the rank data from the form {field.data}")
    for rank in list_of_ranks:
        print(f"in for loop current rank: {rank}")
        if int(rank) == int(field.data):
            print("rank match")
            raise ValidationError('Rank Already Used! Rank This Movie Differently!')


class AddMovie(FlaskForm):
    title = StringField('Movie Title')
    submit = SubmitField('Done')


class MovieEditForm(FlaskForm):
    rating = FloatField('Your Rating Out of 10')
    review = TextAreaField('Your Short Review')
    ranking = FloatField('Your Rank', [ranking_check])
    submit = SubmitField('Done')


@app.route("/data", methods=["GET", "POST"])
def data():
    web_id = request.args.get('id')
    parameters_movie = {
        "api_key": API_KEY
    }
    response = requests.get(f"https://api.themoviedb.org/3/movie/{web_id}", params=parameters_movie)
    response.raise_for_status()
    movie_data = response.json()
    print(movie_data)
    print(movie_data['original_title'])
    # add movie to database
    new_movie = Movie(
        title=movie_data['original_title'],
        year=movie_data['release_date'],
        img_url=f"https://image.tmdb.org/t/p/w500/{movie_data['poster_path']}",
        description=movie_data['overview'],
        ranking=0,
        review="",
        rating=0,
        id=web_id
    )
    db.session.add(new_movie)
    db.session.commit()

    return redirect(url_for('edit', id=web_id))


@app.route("/edit", methods=["GET", "POST"])
def edit():
    form = MovieEditForm()

    if form.validate_on_submit():
        # UPDATE RECORD
        movie_id = request.args.get('id')
        movie_to_update = Movie.query.get(movie_id)
        movie_to_update.rating = float(form.rating.data)
        movie_to_update.review = form.review.data
        movie_to_update.ranking = form.ranking.data
        db.session.commit()
        return redirect(url_for('home'))

    movie_id = request.args.get('id')
    movie_selected = Movie.query.get(movie_id)

    if movie_selected.review:
        form.rating.default = movie_selected.rating
        form.process()
        form.review.default = movie_selected.review
        form.process()
        form.ranking.default = movie_selected.ranking
        form.process()

    return render_template("edit.html", movie=movie_selected, form=form, id=movie_id)


@app.route("/delete")
def delete():
    # delete RECORD
    movie_id = request.args.get('id')
    movie_to_delete = Movie.query.get(movie_id)
    db.session.delete(movie_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


@app.route("/add", methods=["GET", "POST"])
def add_movie():
    form = AddMovie()
    if form.validate_on_submit():
        parameters = {
            "api_key": API_KEY,
            "query": form.title.data
        }
        response = requests.get("https://api.themoviedb.org/3/search/movie", params=parameters)
        response.raise_for_status()
        movie_data = response.json()
        # print(data)

        returned_movies = []
        for movie in movie_data["results"]:
            returned_movies.append(movie)

        return render_template("select.html", movies=returned_movies)

    return render_template("add.html", form=form)


@app.route("/")
def home():
    # This line creates a list of all the movies sorted by ranking
    all_movies = Movie.query.order_by(Movie.ranking).all()

    list_of_ranks = [int(mov.ranking) for mov in all_movies]
    # print(list_of_ranks)

    sorted_movies = [x for _, x in sorted(zip(list_of_ranks, all_movies))]
    # list_of_ranks_sorted = [int(mov.ranking) for mov in sorted_movies]
    # print(list_of_ranks_sorted)

    return render_template("index.html", movies=sorted_movies)


if __name__ == '__main__':
    app.run(debug=True)
