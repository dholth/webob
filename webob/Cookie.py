import string, re

__all__ = ['Cookie']

_legal_chars = string.ascii_letters + string.digits + "!#$%&'*+-.^_`|~"
_trans_noop = ''.join(chr(x) for x in xrange(256))


_escape_map = dict((chr(i), '\\%03o' % i) for i in xrange(256))
_escape_map.update(zip(_legal_chars, _legal_chars))
_escape_map['"'] = '\\"'
_escape_map['\\'] = '\\\\'
_escape_char = _escape_map.__getitem__

def needs_quoting(v):
    return string.translate(v, _trans_noop, _legal_chars)

def _quote(v):
    if needs_quoting(v):
        return '"' + ''.join(map(_escape_char, v)) + '"'
    return v

_rx_unquote = re.compile(r'\\([0-3][0-7][0-7]|.)')

def _unquote(v):
    if v and v[0] == v[-1] == '"':
        v = v[1:-1]
        def _ch_unquote(m):
            v = m.group(1)
            if v.isdigit():
                return chr(int(v, 8))
            return v
        v = _rx_unquote.sub(_ch_unquote, v)
    return v


#assert _quote('a"\xff') == r'"a\"\377"'
#assert _unquote(r'"a\"\377"') == 'a"\xff'



import time
from datetime import datetime, date, timedelta

weekdays = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
months = (None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')


def serialize_cookie_date(v):
    if isinstance(v, int):
        v = timedelta(seconds=v)
    #if isinstance(v, unicode):
    #    v = v.encode('ascii')
    if isinstance(v, timedelta):
        v = datetime.utcnow() + v
    if isinstance(v, (datetime, date)):
        v = v.timetuple()
    r = time.strftime('%%s, %d-%%s-%Y %H:%M:%S GMT', v)
    return r % (weekdays[v[6]], months[v[1]])


# A class to hold ONE key,value pair.
# In a cookie, each such pair may have several attributes.
#       so this class is used to keep the attributes associated
#       with the appropriate key,value pair.


_cookie_props = {
    "expires" : "expires",
    "path" : "Path",
    "comment" : "Comment",
    "domain" : "Domain",
    "max-age" : "Max-Age",
    "secure" : "secure",
    "httponly" : "HttpOnly",
}

class Morsel(dict):
    def __init__(self, name, value):
        assert name.lower() not in _cookie_props
        assert not needs_quoting(name)
        self.name = name
        self.value = value

    def __setitem__(self, k, v):
        k = k.lower()
        if k in _cookie_props:
            if isinstance(v, str) or v is None:
                pass
            elif isinstance(v, bool):
                v = '1'*v
            elif k == 'expires':
                v = serialize_cookie_date(v)
            elif isinstance(v, int):
                v = str(v)
            else:
                raise TypeError(type(v))
            if not v:
                self.pop(k, None)
                return
            dict.__setitem__(self, k, v)

    def __str__(self):
        result = []
        suffixes = []
        RA = result.append
        RA("%s=%s" % (self.name, _quote(self.value)))
        for k,v in sorted(self.items()):
            if v and k in _cookie_props:
                assert isinstance(v, str)
                if k in ('secure', 'httponly'):
                    suffixes.append(_cookie_props[k])
                else:
                    if k == 'expires':
                        v = '"%s"' % v
                    RA("%s=%s" % (_cookie_props[k], v))
        return '; '.join(result+suffixes)

    def __repr__(self):
        return '<%s: %s=%s>' % (self.__class__.__name__, self.name, repr(self.value))


_re_quoted = r'"(?:[^\"]|\.)*"'  # any doublequoted string
_re_legal_char  = r"[\w\d!#%&'~_`><@,:/\$\*\+\-\.\^\|\)\(\?\}\{\=]"
_re_expires_val = r"\w{3},\s[\w\d-]{9,11}\s[\d:]{8}\sGMT"
_rx_cookie = re.compile(
    # key
    (r"(%s+?)" % _re_legal_char)
    # =
    + r"\s*=\s*"
    # val
    + r"(%s|%s|%s*)" % (_re_quoted, _re_expires_val, _re_legal_char)
)


class Cookie(dict):
    def __init__(self, input=None):
        if input:
            self.load(input)

    def load(self, data):
        ckey = None
        for key, val in _rx_cookie.findall(data):
            if key.lower() in _cookie_props:
                if ckey:
                    self[ckey][key] = _unquote(val)
            elif key[0] == '$':
                continue
            else:
                self[key] = _unquote(val)
                ckey = key

    def __setitem__(self, key, val):
        if needs_quoting(key):
            return
        dict.__setitem__(self, key, Morsel(key, val))

    def __str__(self):
        return '; '.join(str(m) for _,m in sorted(self.items()))

    def __repr__(self):
        items = ['%s=%s' % (k, v.value) for k,v in sorted(self.items())]
        return '<%s: %s>' % (self.__class__.__name__, ' '.join(items))


#print repr(Cookie('foo=bar'))
# c = Cookie('bad_cookie=; expires="... GMT"; Max-Age=0; Path=/')
# print c
#print c['bad_cookie'].items()