
"""
Provides an 'attribute' class for one-use descriptors.
"""

attribute = None

class _MetaAttribute(type):
    def __new__(meta, name, bases, dict):
        # for reals, yo.
        for kw in ['get', 'set', 'delete']:
            if kw in dict:
                dict[kw] = staticmethod(dict[kw])
        secretClass = type.__new__(meta, name, bases, dict)
        if attribute is None:
            return secretClass
        return secretClass()

class attribute(object):
    """
    Convenience class for providing one-shot descriptors, similar to
    'property'.  For example:

        >>> from epsilon.descriptor import attribute
        >>> class Dynamo(object):
        ...  class dynamic(attribute):
        ...   def get(self):
        ...    self.dynCount += 1
        ...    return self.dynCount
        ...   def set(self, value):
        ...    self.dynCount += value
        ...  dynCount = 0
        ...
        >>> d = Dynamo()
        >>> d.dynamic
        1
        >>> d.dynamic
        2
        >>> d.dynamic = 6
        >>> d.dynamic
        9
        >>> d.dynamic
        10
        >>> del d.dynamic
        Traceback (most recent call last):
            ...
        AttributeError: attribute cannot be removed
    """

    __metaclass__ = _MetaAttribute

    def __get__(self, oself, type):
        """
        Private implementation of descriptor interface.
        """
        if oself is None:
            return self
        return self.get(oself)

    def __set__(self, oself, value):
        """
        Private implementation of descriptor interface.
        """
        return self.set(oself, value)

    def __delete__(self, oself):
        """
        Private implementation of descriptor interface.
        """
        return self.delete(oself)

    def set(self, value):
        """
        Implement this method to provide attribute setting.  Default behavior
        is that attributes are not settable.
        """
        raise AttributeError('read only attribute')

    def get(self):
        """
        Implement this method to provide attribute retrieval.  Default behavior
        is that unset attributes do not have any value.
        """
        raise AttributeError('attribute has no value')

    def delete(self):
        """
        Implement this method to provide attribute deletion.  Default behavior
        is that attributes cannot be deleted.
        """
        raise AttributeError('attribute cannot be removed')


__all__ = ['attribute']
