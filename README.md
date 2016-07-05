Flask-SQLAlchemy-Cache
======================

A CachingQuery implementation to Flask using Flask-SQLAlchemy and Flask-Cache.

To start using caching queries, you just have to replace Flask-SQLAlchemy
`Model.query_class`.

```python
from flask_sqlalchemy import SQLAlchemy, Model
from flask_sqlalchemy_cache import CachingQuery
from flask_cache import Cache

# for Flask-SQLAlchemy < 3.0, set `Model.query_class` and `session_options['query_cls']`
Model.query_class = CachingQuery
db = SQLAlchemy(session_options={'query_cls': CachingQuery})

# for Flask-SQLAlchemy >= 3.0, `query_class` is a built-in argument.
db = SQLAlchemy(app, query_class=CachingQuery)

cache = Cache(app)
```

After that, you can just make queries to a model `YourModel`:

```python
from flask_sqlalchemy_cache import FromCache

# cache is a Flask-Cache instance
YourModel.query.options(FromCache(cache)).first()
```

You also have `RelationshipCache` to enable lazy loading relationships from
cache.

```python
from sqlalchemy.orm import lazyload
from flask_sqlalchemy_cache import RelationshipCache

rc = RelationshipCache(YourModel.some_relationship, cache)
obj = YourModel.query.options(lazyload(YourModel.some_relationship), rc).first()

# make the query and cache the results for future queries
print(obj.some_relationship)
```

Take a look at [Dogpile Caching example][] to more details about how
`CachingQuery` works. Most changes to their were made just to integrate it
with Flask, Flask-SQLAlchemy and Flask-Cache instead of Dogpile.

[Dogpile Caching example]: http://docs.sqlalchemy.org/en/latest/orm/examples.html?highlight=dogpile#module-examples.dogpile_caching
