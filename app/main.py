from flask_sqlalchemy import SQLAlchemy

import os

from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, flash, url_for
from flask import request, json

from flask_wtf import FlaskForm
import email_validator

from wtforms import BooleanField, StringField, PasswordField, SubmitField, validators

from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from database import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_db.db'
app.secret_key = 'test123'
app.config['SESSION_TYPE'] = 'filesystem'

db.init_app(app)  

login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'main.login'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25))
    email = db.Column(db.String(35))
    password_hash = db.Column(db.String(120))

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.set_password(password)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
        

class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    year = db.Column(db.String(4))
    runtime = db.Column(db.String(10))
    genres = db.Column(db.String(255))
    director = db.Column(db.String(50))
    actors = db.Column(db.Text)
    plot = db.Column(db.Text)
    poster_url = db.Column(db.String(255))
    trailer_url = db.Column(db.String(255))


    def __init__(self, title, year, runtime, genres, director, actors, plot, poster_url, trailer_url):
        self.title = title
        self.year = year
        self.runtime = runtime
        self.genres = genres
        self.director = director
        self.actors = actors
        self.plot = plot
        self.poster_url = poster_url
        self.trailer_url = trailer_url
    
class RegistrationForm(FlaskForm):
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email Address', [validators.Length(min=6, max=35), validators.Email()])
    password = PasswordField('New Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')


class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[validators.DataRequired(),
                                    validators.Length(1, 64),
                                    validators.Email()])
    password = PasswordField('Password', validators=[validators.DataRequired()])
    submit = SubmitField('Log In')
    

    def validate(self, extra_validators):
        initial_validation = super(LoginForm, self).validate()
        if not initial_validation:
            return False
        user = User.query.filter_by(email=self.email.data).first()
        if not user:
            self.email.errors.append('Unknown email')
            return False
        if not user.verify_password(self.password.data):
            self.password.errors.append('Invalid password')
            return False
        return True


class Rental(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)
    rented_at = db.Column(db.DateTime, default=datetime.utcnow)
    returned_at = db.Column(db.DateTime)
    
class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)

class SearchForm(FlaskForm):
    search_query = StringField('Search Movies')
    submit = SubmitField('Search')


# Update the movie_not_rented_by_user function
def movie_not_rented_by_user(movie, user):
    if user.is_authenticated:
        rented_movies = Rental.query.filter_by(user_id=user.id, movie_id=movie.id).all()
        return not rented_movies
    return True

app.jinja_env.globals.update(movie_not_rented_by_user=movie_not_rented_by_user, current_user=lambda: None if 'current_user' not in locals() else current_user)


@app.route('/', methods=['GET', 'POST'])
def display_content(content=None):
    form = SearchForm()
    movies = []

    if request.method == 'POST' and form.validate():
        search_query = form.search_query.data
        movies = Movie.query.filter(Movie.title.ilike(f"%{search_query}%")).all()

    return render_template('index.html', form=form, movies=movies)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate():
        print(f"Received data: {form.username.data}, {form.email.data}, {form.password.data}")
        user = User(form.username.data, form.email.data,
                    form.password.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Thanks for registering')
        return redirect(url_for('login'))
    else: 
        print(f"Form validation errors: {form.errors}")
    return render_template('register.html', form=form)




@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user)
            flash(f'Welcome, {user.username}!', 'success')
            return redirect('/')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/confirm_rental/<int:movie_id>', methods=['POST'])
def confirm_rental(movie_id):
    selected_duration = int(request.form.get('selectedDuration'))
    rental = Rental(
        user_id=current_user.id,
        movie_id=movie_id,
        rented_at=datetime.utcnow(),
    )
    return_date = rental.rented_at + timedelta(days=selected_duration)
    db.session.add(rental)
    db.session.commit()

    return redirect(url_for('movie_details', movie_id=movie_id))


#TODO: Favorite Movies
@app.route('/favorites')
def favorites():
    return "Hello world"

@app.route('/search', methods=['GET', 'POST'])
def search():
    form = SearchForm()
    movies = [] 

    if request.method == 'POST' and form.validate():
        search_query = form.search_query.data
        print(f"Search Query: {search_query}")
        movies = Movie.query.filter(Movie.title.ilike(f"%{search_query}%")).all()

    return render_template('search_results.html', form=form, movies=movies)

@app.route('/users')
def dispay_all_users():
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/movies', methods=['GET', 'POST'])
def movie_catalog():
    form = SearchForm()
    movies = []

    if request.method == 'POST' and form.validate():
        search_query = form.search_query.data
        movies = Movie.query.filter(Movie.title.ilike(f"%{search_query}%")).all()
    else:
        page = request.args.get('page', 1, type=int)
        per_page = 20

        total_movies = Movie.query.count()
        start_index = (page - 1) * per_page
        end_index = start_index + per_page

        movies = Movie.query.offset(start_index).limit(per_page).all()

    return render_template('movie_catalog.html', movies=movies, form=form, page=page, total_movies=total_movies)


@app.route('/movie_details/<int:movie_id>')
def movie_details(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    if current_user.is_authenticated:
        return render_template('movie_details.html', movie=movie)
    else:
        flash('Please log in to rent movies.', 'info')
        return redirect(url_for('login'))


@app.route('/user/profile/<int:user_id>')
def user_profile(user_id):
    user = User.query.get(user_id)

    if user:
        rented_movies_count = Rental.query.filter_by(user_id=user.id).count()
        return render_template('user_profile.html', user=user, rented_movies_count=rented_movies_count)
    else:
        flash('User not found.')
        return redirect(url_for('register'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

login_manager.init_app(app)


if __name__ == '__main__':
    app.run()