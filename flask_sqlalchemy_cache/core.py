# coding: utf-8
"""Flask-SQLAlchemy-Cache

A SQLAlchemy CachingQuery implementation for Flask, using Flask-Cache.

It is based in SQLAlchemy docs example:
http://docs.sqlalchemy.org/en/latest/orm/examples.html#module-examples.dogpile_caching
"""
from hashlib import md5

from sqlalchemy.orm.interfaces import MapperOption
from flask.ext.sqlalchemy import BaseQuery


class CachingQuery(BaseQuery):
    """
    A Query subclass which optionally loads full results from cache.

    The CachingQuery optionally stores additional state that allows it to
    consult a cache before accessing the database, in the form of a FromCache
    or RelationshipCache object.

    Each of these objects refer to a cache. When such an object has associated
    itself with the CachingQuery, it is used to locate a cached result.
    If none is present, then the Query is invoked normally, the results
    being cached.

    The FromCache and RelationshipCache mapper options below represent
    the "public" method of configuring this state upon the CachingQuery.
    """

    def __iter__(self):
        """
        Override __iter__ to pull results from cache if particular
        attributes have been configured.

        This approach does *not* detach the loaded objects from the current
        session. If the cache backend is an in-process cache (like "memory")
        and lives beyond the scope of the current session's transaction, those
        objects may be expired.

        The method here can be modified to first expunge() each loaded item
        from the current session before returning the list of items, so that
        the items in the cache are not the same ones in the current Session.
        """
        if hasattr(self, '_cache'):
            func = lambda: list(BaseQuery.__iter__(self))
            return iter(self.get_value(createfunc=func))
        else:
            return BaseQuery.__iter__(self)

    def _get_cache_plus_key(self):
        """Return a cache region plus key."""
        key = getattr(self, '_cache_key', self.key_from_query())
        return self._cache.cache, key

    def invalidate(self):
        """Invalidate the cache value represented by this Query."""
        cache, cache_key = self._get_cache_plus_key()
        cache.delete(cache_key)

    def get_value(self, merge=True, createfunc=None,
                  expiration_time=None, ignore_expiration=False):
        """
        Return the value from the cache for this query.
        """
        cache, cache_key = self._get_cache_plus_key()

        # ignore_expiration means, if the value is in the cache
        # but is expired, return it anyway.   This doesn't make sense
        # with createfunc, which says, if the value is expired, generate
        # a new value.
        assert not ignore_expiration or not createfunc, \
            "Can't ignore expiration and also provide createfunc"

        if ignore_expiration or not createfunc:
            cached_value = cache.get(cache_key,
                                     expiration_time=expiration_time,
                                     ignore_expiration=ignore_expiration)
        else:
            cached_value = cache.get(cache_key)
            if not cached_value:
                cached_value = createfunc()
                cache.set(cache_key, cached_value, timeout=expiration_time)

        if cached_value and merge:
            cached_value = self.merge_result(cached_value, load=False)

        return cached_value

    def set_value(self, value):
        """Set the value in the cache for this query."""
        cache, cache_key = self._get_cache_plus_key()
        cache.set(cache_key, value)

    def key_from_query(self, qualifier=None):
        """
        Given a Query, create a cache key.

        There are many approaches to this; here we use the simplest, which is
        to create an md5 hash of the text of the SQL statement, combined with
        stringified versions of all the bound parameters within it.

        There's a bit of a performance hit with compiling out "query.statement"
        here; other approaches include setting up an explicit cache key with a
        particular Query, then combining that with the bound parameter values.
        """
        stmt = self.with_labels().statement
        compiled = stmt.compile()
        params = compiled.params

        values = [str(compiled)]
        for k in sorted(params):
            values.append(repr(params[k]))
        key = u" ".join(values)
        return md5(key.encode('utf8')).hexdigest()


class _CacheableMapperOption(MapperOption):

    def __init__(self, cache, cache_key=None):
        """
        Construct a new `_CacheableMapperOption`.

        :param cache: the cache.  Should be a Flask-Cache instance.

        :param cache_key: optional.  A string cache key that will serve as
        the key to the query. Use this if your query has a huge amount of
        parameters (such as when using in_()) which correspond more simply to
        some other identifier.
        """
        self.cache = cache
        self.cache_key = cache_key

    def __getstate__(self):
        """
        Flask-Cache instance is not picklable because it has references
        to Flask.app. Also, I don't want it cached.
        """
        d = self.__dict__.copy()
        d.pop('cache', None)
        return d


class FromCache(_CacheableMapperOption):
    """Specifies that a Query should load results from a cache."""

    propagate_to_loaders = False

    def process_query(self, query):
        """Process a Query during normal loading operation."""
        query._cache = self


class RelationshipCache(_CacheableMapperOption):
    """
    Specifies that a Query as called within a "lazy load" should load
    results from a cache.
    """

    propagate_to_loaders = True

    def __init__(self, attribute, cache, cache_key=None):
        """
        Construct a new RelationshipCache.

        :param attribute: A Class.attribute which indicates a particular
        class relationship() whose lazy loader should be pulled from the cache.

        :param cache_key: optional.  A string cache key that will serve as the
        key to the query, bypassing the usual means of forming a key from the
        Query itself.
        """
        super(RelationshipCache, self).__init__(cache, cache_key)
        self._relationship_options = {
            (attribute.property.parent.class_, attribute.property.key): self
        }

    def process_query_conditionally(self, query):
        """
        Process a Query that is used within a lazy loader.

        (the process_query_conditionally() method is a SQLAlchemy
        hook invoked only within lazyload.)
        """
        if query._current_path:
            mapper, prop = query._current_path[-2:]
            for cls in mapper.class_.__mro__:
                k = (cls, prop.key)
                relationship_option = self._relationship_options.get(k)
                if relationship_option:
                    query._cache = relationship_option
                    break

    def and_(self, option):
        """
        Chain another RelationshipCache option to this one.

        While many RelationshipCache objects can be specified on a single
        Query separately, chaining them together allows for a more efficient
        lookup during load.
        """
        self._relationship_options.update(option._relationship_options)
        return self
