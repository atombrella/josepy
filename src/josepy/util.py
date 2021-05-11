"""JOSE utilities."""
from collections.abc import Hashable, Mapping
from typing import Union

import OpenSSL
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import (
    ec,
    ed25519, ed448,
    rsa,
    x25519, x448,
)


class abstractclassmethod(classmethod):
    # pylint: disable=invalid-name,too-few-public-methods
    """Descriptor for an abstract classmethod.

    It augments the :mod:`abc` framework with an abstract
    classmethod. This is implemented as :class:`abc.abstractclassmethod`
    in the standard Python library starting with version 3.2.

    This implementation is from a StackOverflow answer that was derived from
    the implementation in the Python 3.3 abc library.
    http://stackoverflow.com/questions/11217878/python-2-7-combine-abc-abstractmethod-and-classmethod.

    """
    __isabstractmethod__ = True

    def __init__(self, target):
        target.__isabstractmethod__ = True
        super().__init__(target)


class ComparableX509:  # pylint: disable=too-few-public-methods
    """Wrapper for OpenSSL.crypto.X509** objects that supports __eq__.

    :ivar wrapped: Wrapped certificate or certificate request.
    :type wrapped: `OpenSSL.crypto.X509` or `OpenSSL.crypto.X509Req`.

    """

    def __init__(self, wrapped):
        assert isinstance(wrapped, OpenSSL.crypto.X509) or isinstance(
            wrapped, OpenSSL.crypto.X509Req)
        self.wrapped = wrapped

    def __getattr__(self, name):
        return getattr(self.wrapped, name)

    def _dump(self, filetype=OpenSSL.crypto.FILETYPE_ASN1):
        """Dumps the object into a buffer with the specified encoding.

        :param int filetype: The desired encoding. Should be one of
            `OpenSSL.crypto.FILETYPE_ASN1`,
            `OpenSSL.crypto.FILETYPE_PEM`, or
            `OpenSSL.crypto.FILETYPE_TEXT`.

        :returns: Encoded X509 object.
        :rtype: str

        """
        if isinstance(self.wrapped, OpenSSL.crypto.X509):
            func = OpenSSL.crypto.dump_certificate
        else:  # assert in __init__ makes sure this is X509Req
            func = OpenSSL.crypto.dump_certificate_request
        return func(filetype, self.wrapped)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        # pylint: disable=protected-access
        return self._dump() == other._dump()

    def __hash__(self):
        return hash((self.__class__, self._dump()))

    def __repr__(self):
        return '<{0}({1!r})>'.format(self.__class__.__name__, self.wrapped)


class ComparableKey:  # pylint: disable=too-few-public-methods
    """Comparable wrapper for ``cryptography`` keys.

    See https://github.com/pyca/cryptography/issues/2122.

    """
    __hash__ = NotImplemented

    def __init__(self, wrapped):
        self._wrapped = wrapped

    def __getattr__(self, name):
        return getattr(self._wrapped, name)

    def __eq__(self, other):
        # pylint: disable=protected-access
        if (not isinstance(other, self.__class__) or
                self._wrapped.__class__ is not other._wrapped.__class__):
            return NotImplemented
        elif hasattr(self._wrapped, 'private_numbers'):
            return self.private_numbers() == other.private_numbers()
        elif hasattr(self._wrapped, 'public_numbers'):
            return self.public_numbers() == other.public_numbers()
        else:
            return NotImplemented

    def __repr__(self):
        return '<{0}({1!r})>'.format(self.__class__.__name__, self._wrapped)

    def public_key(self):
        """Get wrapped public key."""
        return self.__class__(self._wrapped.public_key())


class ComparableRSAKey(ComparableKey):  # pylint: disable=too-few-public-methods
    """Wrapper for ``cryptography`` RSA keys.

    Wraps around:

    - :class:`~cryptography.hazmat.primitives.asymmetric.rsa.RSAPrivateKey`
    - :class:`~cryptography.hazmat.primitives.asymmetric.rsa.RSAPublicKey`

    """

    def __hash__(self):
        # public_numbers() hasn't got stable hash!
        # https://github.com/pyca/cryptography/issues/2143
        if isinstance(self._wrapped, rsa.RSAPrivateKeyWithSerialization):
            priv = self.private_numbers()
            pub = priv.public_numbers
            return hash((self.__class__, priv.p, priv.q, priv.dmp1,
                         priv.dmq1, priv.iqmp, pub.n, pub.e))
        elif isinstance(self._wrapped, rsa.RSAPublicKeyWithSerialization):
            pub = self.public_numbers()
            return hash((self.__class__, pub.n, pub.e))


class ComparableECKey(ComparableKey):  # pylint: disable=too-few-public-methods
    """Wrapper for ``cryptography`` EC keys.
    Wraps around:
    - :class:`~cryptography.hazmat.primitives.asymmetric.ec.EllipticCurvePrivateKey`
    - :class:`~cryptography.hazmat.primitives.asymmetric.ec.EllipticCurvePublicKey`
    """

    def __hash__(self):
        # public_numbers() hasn't got stable hash!
        # https://github.com/pyca/cryptography/issues/2143
        if isinstance(self._wrapped, ec.EllipticCurvePrivateKeyWithSerialization):
            priv = self.private_numbers()
            pub = priv.public_numbers
            return hash((self.__class__, pub.curve.name, pub.x, pub.y, priv.private_value))
        elif isinstance(self._wrapped, ec.EllipticCurvePublicKeyWithSerialization):
            pub = self.public_numbers()
            return hash((self.__class__, pub.curve.name, pub.x, pub.y))

    def public_key(self):
        """Get wrapped public key."""
        # Unlike RSAPrivateKey, EllipticCurvePrivateKey does not have public_key()
        if hasattr(self._wrapped, 'public_key'):
            key = self._wrapped.public_key()
        else:
            key = self._wrapped.public_numbers().public_key(default_backend())
        return self.__class__(key)


class ComparableOKPKey(ComparableKey):
    """Wrapper for ``cryptography`` OKP keys.

    Wraps around:
    - :class:`~cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PrivateKey`
    - :class:`~cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PublicKey`
    - :class:`~cryptography.hazmat.primitives.asymmetric.ed448.Ed448PrivateKey`
    - :class:`~cryptography.hazmat.primitives.asymmetric.ed448.Ed448PublicKey`
    - :class:`~cryptography.hazmat.primitives.asymmetric.x25519.X25519PrivateKey`
    - :class:`~cryptography.hazmat.primitives.asymmetric.x25519.X25519PublicKey`
    - :class:`~cryptography.hazmat.primitives.asymmetric.x448.X448PrivateKey`
    - :class:`~cryptography.hazmat.primitives.asymmetric.x448.X448PublicKey`
    """

    def __hash__(self):
        return hash((self.__class__, self._wrapped.curve.name, self._wrapped.x))

    def is_private(self):
        return isinstance(
            self._wrapped, (
                ed25519.Ed25519PrivateKey, ed448.Ed448PrivateKey,
                x25519.X25519PrivateKey, x448.X448PrivateKey
            )
        )

    def public_key(self) -> Union[ed25519.Ed25519PrivateKey]:
        """Get wrapped public key."""
        key = self._wrapped.public_key(
        )
        return type(key)()


class ImmutableMap(Mapping, Hashable):
    # pylint: disable=too-few-public-methods
    """Immutable key to value mapping with attribute access."""

    __slots__ = ()
    """Must be overridden in subclasses."""

    def __init__(self, **kwargs):
        if set(kwargs) != set(self.__slots__):
            raise TypeError(
                '__init__() takes exactly the following arguments: {0} '
                '({1} given)'.format(', '.join(self.__slots__),
                                     ', '.join(kwargs) if kwargs else 'none'))
        for slot in self.__slots__:
            object.__setattr__(self, slot, kwargs.pop(slot))

    def update(self, **kwargs):
        """Return updated map."""
        items = {**self, **kwargs}
        return type(self)(**items)  # pylint: disable=star-args

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __iter__(self):
        return iter(self.__slots__)

    def __len__(self):
        return len(self.__slots__)

    def __hash__(self):
        return hash(tuple(getattr(self, slot) for slot in self.__slots__))

    def __setattr__(self, name, value):
        raise AttributeError("can't set attribute")

    def __repr__(self):
        return '{0}({1})'.format(self.__class__.__name__, ', '.join(
            '{0}={1!r}'.format(key, value)
            for key, value in self.items()))


class frozendict(Mapping, Hashable):
    # pylint: disable=invalid-name,too-few-public-methods
    """Frozen dictionary."""
    __slots__ = ('_items', '_keys')

    def __init__(self, *args, **kwargs):
        if kwargs and not args:
            items = dict(kwargs)
        elif len(args) == 1 and isinstance(args[0], Mapping):
            items = args[0]
        else:
            raise TypeError()
        # TODO: support generators/iterators

        object.__setattr__(self, '_items', items)
        object.__setattr__(self, '_keys', tuple(sorted(items.keys())))

    def __getitem__(self, key):
        return self._items[key]

    def __iter__(self):
        return iter(self._keys)

    def __len__(self):
        return len(self._items)

    def _sorted_items(self):
        return tuple((key, self[key]) for key in self._keys)

    def __hash__(self):
        return hash(self._sorted_items())

    def __getattr__(self, name):
        try:
            return self._items[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        raise AttributeError("can't set attribute")

    def __repr__(self):
        return 'frozendict({0})'.format(', '.join('{0}={1!r}'.format(
            key, value) for key, value in self._sorted_items()))
