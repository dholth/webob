import re
from webob.updatedict import UpdateDict

token_re = re.compile(
    r'([a-zA-Z][a-zA-Z_-]*)\s*(?:=(?:"([^"]*)"|([^ \t",;]*)))?')
need_quote_re = re.compile(r'[^a-zA-Z0-9._-]')

class exists_property(object):
    def __init__(self, prop, type=None):
        self.prop = prop
        self.type = type

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return self.prop in obj.properties
    def __set__(self, obj, value):
        if (self.type is not None
            and self.type != obj.type):
            raise AttributeError(
                "The property %s only applies to %s Cache-Control" % (self.prop, self.type))
        if value:
            obj.properties[self.prop] = None
        else:
            if self.prop in obj.properties:
                del obj.properties[self.prop]
    def __del__(self, obj):
        self.__set__(obj, False)

class value_property(object):
    def __init__(self, prop, default=None, none=None, type=None):
        self.prop = prop
        self.default = default
        self.none = none
        self.type = type
    def __get__(self, obj, type=None):
        if obj is None:
            return self
        if self.prop in obj.properties:
            value = obj.properties[self.prop]
            if value is None:
                return self.none
        else:
            return self.default
    def __set__(self, obj, value):
        if (self.type is not None
            and self.type != obj.type):
            raise AttributeError(
                "The property %s only applies to %s Cache-Control" % (self.prop, self.type))
        if value == self.default:
            if self.prop in obj.properties:
                del obj.properties[self.prop]
        else:
            obj.properties[self.prop] = value
    def __del__(self, obj):
        if self.prop in obj.properties:
            del obj.properties[self.prop]

class CacheControl(object):

    def __init__(self, properties, type):
        self.properties = properties
        self.type = type

    #@classmethod
    def parse(cls, header, updates_to=None, type=None):
        if updates_to:
            props = UpdateDict()
            props.updated = updates_to
        else:
            props = {}
        for match in token_re.finditer(header):
            name = match.group(1)
            value = match.group(2) or match.group(3) or None
            if value:
                try:
                    value = int(value)
                except ValueError:
                    pass
            props[name] = value
        obj = cls(props, type=type)
        if updates_to:
            props.updated_args = (obj,)
        return obj

    parse = classmethod(parse)

    def __repr__(self):
        return '<CacheControl %r>' % str(self)

    # Request values:
    # no-cache shared
    # no-store shared
    # max-age shared
    max_stale = value_property('max-stale', none='*', type='request')
    min_fresh = value_property('min-fresh', type='request')
    # no-transform shared
    only_if_cached = exists_property('only-if-cached', type='request')

    # Response values:
    public = exists_property('public', type='response')
    private = value_property('private', none='*', type='response')
    no_cache = value_property('no-cache', none='*')
    no_store = exists_property('no-store')
    no_transform = exists_property('no-transform')
    must_revalidate = exists_property('must-revalidate', type='response')
    proxy_revalidate = exists_property('proxy-revalidate', type='response')
    max_age = value_property('max-age')
    s_maxage = value_property('s-maxage', type='response')
    s_max_age = s_maxage

    def __str__(self):
        parts = []
        for name, value in sorted(self.properties.items()):
            if value is None:
                parts.append(name)
                continue
            value = str(value)
            if need_quote_re.search(value):
                value = '"%s"' % value
            parts.append('%s=%s' % (name, value))
        return ', '.join(parts)

    def copy(self):
        return self.__class__(self.properties.copy(), type=self.type)
