from flask.ext.sqlalchemy import get_debug_queries
from flask.ext.sqlalchemy_cache import RelationshipCache

from _base import app, cache, db, State, City

with app.app_context():
    rc = RelationshipCache(State.country, cache)
    q = City.query.options(db.joinedload(City.state), rc)
    for item in q:
        assert "Brazil" == item.state.country.name
    print '%d queries executed.' % len(get_debug_queries())
