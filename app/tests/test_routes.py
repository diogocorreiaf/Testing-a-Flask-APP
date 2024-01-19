import pytest
from flask import Flask, url_for
from main import User, app, Movie
from database import db
import re
import requests
from bs4 import BeautifulSoup


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_db.db'
app.secret_key = 'test123'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['DEBUG'] = True
app.config['TESTING'] = True
app.config['SERVER_NAME'] = 'localhost:5000'

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

@pytest.fixture
def app_with_context():
    with app.app_context():
        db.create_all()
        user = User(username='testuser', email='test@example.com', password='testpassword')
        db.session.add(user)
        db.session.commit() 
        yield app


def get_csrf_token(client, endpoint):
    response = client.get(endpoint)
    soup = BeautifulSoup(response.data, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrf_token'})['value']
    return csrf_token

def login(client):
    response = client.post('/login', data=dict(
        email='test@example.com',
        password='testpassword',
        submit='Sign in',
        csrf_token=get_csrf_token(client, '/login')
    ), follow_redirects=True)
    assert response.status_code == 200

def test_home_route(client):
    response = client.get('/')
    assert response.status_code == 200

from bs4 import BeautifulSoup

def find_link(response, href):
    soup = BeautifulSoup(response.data, 'html.parser')
    link = soup.find('a', {'href': href})
    return link

def test_register_button_on_home_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Register" in response.data
    
    register_page_response = client.get('/register')
    assert register_page_response.status_code == 200
    assert b"Registration Page" in register_page_response.data


def test_login_button_on_home_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Login" in response.data
    
    login_page_response = client.get('/login')
    assert login_page_response.status_code == 200
    assert b"loginForm" in login_page_response.data


def test_movie_catalog_button_on_home_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Movie Catalog" in response.data
    
    movie_catalog_link = response.data.decode('utf-8').split('href="/movies"')[1].split('</a>')[0]
    movie_catalog_page_response = client.get('/movies')
    
    assert movie_catalog_page_response.status_code == 200
    assert b"Movie Catalog" in movie_catalog_page_response.data



def test_access_movie_details_not_logged_in(client):
    movie_id = 1
    response = client.get(f'/movie_details/{movie_id}', follow_redirects=True)  
    assert response.status_code == 200  
    assert b"Login" in response.data 

def test_register_with_valid_information(client):
    csrf_token = get_csrf_token(client, '/register')

    response = client.post('/register', data=dict(
        username='testuser',
        email='test@example.com',
        password='testpassword',
        confirm='testpassword',
        csrf_token=csrf_token
    ), follow_redirects=True)

    assert response.status_code == 200
    assert b"Login" in response.data


def test_register_with_invalid_information(client):
    csrf_token = get_csrf_token(client, '/register')

    response = client.post('/register', data=dict(
        username='testuser',
        email='invalid-email',
        password='testpassword',
        confirm='testpassword',
        csrf_token=csrf_token
    ), follow_redirects=True)

    assert response.status_code == 200
    assert b"Register" in response.data


def test_register_with_existing_email(client):
    csrf_token = get_csrf_token(client, '/register')
    user = User(username='existinguser', email='existing@example.com', password='testpassword')
    user.set_password('testpassword')
    db.session.add(user)
    db.session.commit()
    response = client.post('/register', data=dict(
        username='newuser',
        email='existing@example.com',
        password='testpassword',
        confirm='testpassword',
        csrf_token=csrf_token
    ), follow_redirects=True)

    assert response.status_code == 200
    assert b"Email address already in use" in response.data
    assert b"Register" in response.data


def test_login_valid_credentials(client):
    csrf_token = get_csrf_token(client, '/login')
    response = client.post('/login', data=dict(
        email='test@example.com',
        password='testpassword',
        submit='Sign in',
        csrf_token=csrf_token
    ), follow_redirects=True)

    assert response.status_code == 200
    assert response.request.path == '/'


def test_login_invalid_credentials(client):
    response = client.post('/login', data=dict(
        email='test@example.com',
        password='wrongpassword'
    ), follow_redirects=True)

    assert response.status_code == 200
    assert b"Login" in response.data

def test_logout(client):
    client.post('/login', data=dict(
        email='test@example.com',
        password='testpassword'
    ), follow_redirects=True)

    response = client.get('/logout', follow_redirects=True)

    assert response.status_code == 200
    assert b"Login" in response.data
    assert b"Logout" not in response.data


def test_view_user_profile(client):
    login_response = client.post('/login', data=dict(
        email='test@example.com',
        password='testpassword',
        submit='Sign in',
        csrf_token=get_csrf_token(client, '/login')
    ), follow_redirects=True)

    assert login_response.status_code == 200
    profile_response = client.get('/user/profile/1') 

    assert profile_response.status_code == 200
    assert profile_response.request.path == '/user/profile/1'


def test_view_another_user_profile(client):
    login_response = client.post('/login', data=dict(
        email='test@example.com',
        password='testpassword',
        submit='Sign in',
        csrf_token=get_csrf_token(client, '/login')
    ), follow_redirects=True)
    assert login_response.status_code == 200
    another_user_profile_response = client.get('/user/profile/2')
    assert another_user_profile_response.status_code == 302
    assert '/user/profile/1' in another_user_profile_response.location


def test_search_movie_with_valid_query(client):
    response = client.post('/search', data=dict(
        query='Lord',
        csrf_token=get_csrf_token(client, '/search')
    ))

    print(response.data)
    assert response.status_code == 200
    assert response.request.path == '/search'

    
def test_search_movie_with_empty_query(client):
    response = client.post('/search', data=dict(
        query='',
        csrf_token=get_csrf_token(client, '/search')
    ))

    assert response.status_code == 200
    assert response.request.path == '/search'



def test_renting_button_visible(client):
    login(client)
    
    response = client.get(url_for('movie_details', movie_id=1))
    assert response.status_code == 200
    assert b"Rent Movie" in response.data

def test_renting_form_visible(client):
    login(client)
    
    response = client.get(url_for('movie_details', movie_id=1))
    assert response.status_code == 200
    assert b'id="rentForm"' in response.data


def test_confirm_renting_update_database(client):
    login(client)
    
    response = client.post('/confirm_rental', data=dict(
        movie_id=1,
        duration=3,
    ))
    assert b"You have already rented this movie"


def test_view_already_rented_movie(client):
    login(client)

    client.post('/confirm_rental', data=dict(
        movie_id=1,
        duration=3,
    ))
    response = client.get(url_for('movie_details', movie_id=1))
    assert response.status_code == 200
    assert b"You have already rented this movie"

def test_access_invalid_movie_details(client):
    login(client)
    response = client.get(url_for('movie_details', movie_id=400))
    assert response.status_code == 404


def test_navigate_to_next_page(client):
    current_page_url = '/movies?page=1'
    response = client.get(current_page_url)
    assert response.status_code == 200
    next_page_url = '/movies?page=2'
    response_next_page = client.get(next_page_url, follow_redirects=True)
    assert response_next_page.status_code == 200
    assert b"Previous" in response_next_page.data


def test_navigate_to_previous_page(client):
    current_page_url = '/movies?page=2'
    response = client.get(current_page_url)
    assert response.status_code == 200
    previous_page_url = '/movies?page=1'
    response_previous_page = client.get(previous_page_url, follow_redirects=True)
    assert response_previous_page.status_code == 200
    assert b"Next" in response_previous_page.data


def test_click_home_button(client):
    movie_catalog_url = '/movies'
    response = client.get(movie_catalog_url)
    assert response.status_code == 200
    home_button_url = '/'
    response_home_button = client.get(home_button_url, follow_redirects=True)
    assert response_home_button.status_code == 200
    assert b"Movie Rental Website" in response_home_button.data

def test_click_login_button(client):
    movie_catalog_url = '/movies'
    response = client.get(movie_catalog_url)
    assert response.status_code == 200
    login_button_url = '/login'
    response_login_button = client.get(login_button_url, follow_redirects=True)
    assert response_login_button.status_code == 200
    assert b"Login" in response_login_button.data


def test_click_register_button(client):
    movie_catalog_url = '/movies'
    response = client.get(movie_catalog_url)
    assert response.status_code == 200
    register_button_url = '/register'
    response_register_button = client.get(register_button_url, follow_redirects=True)
    assert response_register_button.status_code == 200
    assert b"Register" in response_register_button.data

def test_click_home_button_on_login_page(client):
    login_page_url = '/login'
    response = client.get(login_page_url)
    assert response.status_code == 200
    home_button_url = '/'
    response_home_button = client.get(home_button_url, follow_redirects=True)
    assert response_home_button.status_code == 200
    assert b"Movie Rental Website" in response_home_button.data


def test_click_register_button_on_login_page(client):
    login_page_url = '/login'
    response = client.get(login_page_url)
    assert response.status_code == 200
    register_button_url = '/register'
    response_register_button = client.get(register_button_url, follow_redirects=True)
    assert response_register_button.status_code == 200
    assert b"Register" in response_register_button.data


def test_absence_of_next_button_on_last_page(client):
    last_page_url = '/movies?page=13'
    response = client.get(last_page_url)
    assert response.status_code == 200
    assert b"Next" not in response.data

def test_absence_of_previous_button_on_first_page(client):
    first_page_url = '/movies?page=1'
    response = client.get(first_page_url)
    assert response.status_code == 200
    assert b"Previous" not in response.data

def test_access_non_existent_page(client):
    non_existent_page_url = '/movies?page=14'
    response = client.get(non_existent_page_url)
    assert response.status_code == 404
