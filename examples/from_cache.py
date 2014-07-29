from flask.ext.sqlalchemy import get_debug_queries
from flask.ext.sqlalchemy_cache import FromCache

from _base import app, cache, Country

with app.app_context():
    q = Country.query.order_by(Country.id.asc())
    caching_q = q.options(FromCache(cache))

    country = caching_q.first()
    assert 'Brazil' == country.name
    #assert 'Germany' == countries[1].name
    print '%d queries executed.' % len(get_debug_queries())
