import os

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy, Model
from flask.ext.cache import Cache
from flask.ext.sqlalchemy_cache import CachingQuery


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///example.db'
app.config['DEBUG'] = True
app.config['CACHE_TYPE'] = 'memcached'

# set up Flask-SQLAlchemy with Caching Query
Model.query_class = CachingQuery
db = SQLAlchemy(app, session_options={'query_cls': CachingQuery})


class Country(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


class State(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    country_id = db.Column(db.ForeignKey(Country.id))
    country = db.relationship(Country, backref='states')


class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    state_id = db.Column(db.ForeignKey(State.id))
    state = db.relationship(State, backref='cities')


def make_db():
    if os.path.isfile('example.db'):
        return
    db.create_all()

    brazil = Country(name='Brazil')
    db.session.add(brazil)
    germany = Country(name='Germany')
    db.session.add(germany)

    sp = State(name='SP', country=brazil)
    db.session.add(sp)

    cotia = City(name='Cotia', state=sp)
    db.session.add(cotia)
    db.session.commit()


with app.app_context():
    make_db()

cache = Cache(app)
#cache.clear()