from main import app, db, User, Movie
import json
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()

    # Populate database with some entries
    admin = User(username='admin', email='admin@example.com', password='12345')
    admin.set_password("12345")  # Pass the password here
    regular_user = User(username='user', email='user@example.com', password='12345')
    regular_user.set_password("12345")  # Pass the password here

    db.session.add(admin)
    db.session.add(regular_user)

    def load_data_from_json(filename):
        with open(filename, 'r') as file:
            data = json.load(file)
        return data.get('movies', [])
    
    movie_data = load_data_from_json('db.json')
    
    for movie_info in movie_data:
        movie = Movie(
        title=movie_info['title'],
        year=movie_info['year'],
        runtime=movie_info['runtime'],
        genres=', '.join(movie_info['genres']),
        director=movie_info['director'],
        actors=movie_info['actors'],
        plot=movie_info['plot'],
        poster_url=movie_info['posterUrl'],
        trailer_url=movie_info.get('trailerUrl', None)
        )
        db.session.add(movie)
    db.session.commit()
