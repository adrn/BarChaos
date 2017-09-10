# coding: utf-8

# Standard library
import os
from os import path
from abc import abstractproperty

# Third-party
# import yaml
import ruamel.yaml as yaml # supports comments

__all__ = ['ConfigNamespace']

class ConfigItem(object):

    def __init__(self, default_value, description="", allowed_types=None):
        """A single configuration item or setting value.

        These objects should be created and accessed as members of a
        `ConfigNamespace` subclass, for example::

            class Config(ConfigNamespace):
                n_periods = ConfigItem(128, "The number of orbital periods to "
                                            "integrate for.")

            config = Config()
            config.n_periods

        Parameters
        ----------
        default_value : object
            This is the default value of the setting.
        description : str, optional
            An optional description of the setting.
        allowed_types : list, optional
            The allowed data types for this setting. This is used to validate
            the input when this is set. If no allowed types are given, this is
            set to the type of the default value.
        """
        self.default_value = default_value

        if allowed_types is None:
            self.allowed_types = [type(self.default_value)]
        else:
            self.allowed_types = allowed_types

        if type(self.default_value) not in self.allowed_types:
            raise TypeError('Specified default is not consistent with allowed '
                            'types')

        self.description = str(description)

        self.name = None # not set yet - set by ConfigNamespace metaclass
        self._value = self.default_value

    def set(self, value):
        if type(value) in self.allowed_types:
            self._value = value
        else:
            raise TypeError("{0} must have type {1}, not {2}".format(self.name,
                                                                     self.allowed_types,
                                                                     type(value)))

    def __call__(self):
        return self._value

    def __repr__(self):
        out = '<{0}: name={1!r} value={2!r}>'.format(
            self.__class__.__name__, self.name, self())
        return out

    def __str__(self):
        out = '\n'.join(('{0}: {1}',
                         '  default={2!r}',
                         '  value={3!r}'))
        out = out.format(self.__class__.__name__, self.name,
                         self.default_value, self())
        return out


class _ConfigNamespaceMeta(type):

    def __new__(cls, name, bases, dict_):
        if cls.__bases__[0] is object:
            return

        new_dict = {}

        new_dict['_items'] = []
        for key, val in dict_.items():
            if not key.startswith('_') and isinstance(val, ConfigItem):
                val.name = key
                new_dict['_'+key] = val

                new_dict[key] = property(
                    fget=lambda self, k=key: getattr(self, '_'+k)(),
                    fset=lambda self, v, k=key: getattr(self, '_'+k).set(v))

                new_dict['_items'].append(key)

            else:
                new_dict[key] = val

        inst = super(_ConfigNamespaceMeta, cls).__new__(cls, name, bases, new_dict)

        return inst


class ConfigNamespace(object, metaclass=_ConfigNamespaceMeta):
    """A namespace baseclass for storing configuration settings.

    Subpackages or module should define subclasses of this object to store
    configuration settings for that subpackage or module. The object then acts
    like a singleton: changes to the configuration settings propagate to all
    instances.
    """

    @abstractproperty
    def name(self):
        """ The name of this configuration setting block. """

    def __repr__(self):
        items = ["{0}={1!r}".format(k, v) for k,v in self.to_dict().items()]
        out = '<{0}: {1}>'.format(self.__class__.__name__,
                                  ' '.join(items))
        return out

    def to_dict(self):
        items = dict([(n, getattr(self, n)) for n in self._items])
        return items

    def save(self, filename):
        """Save the configuration state to the specified YAML file.

        Parameters
        ----------
        filename : str
            Path to the filename to save to.
        """

        if path.exists(filename):
            with open(filename, 'r') as f:
                dict_ = yaml.load(f, yaml.RoundTripLoader)
        else:
            dict_ = dict()

        commented_dict = yaml.comments.CommentedMap(self.to_dict())

        for name in self._items:
            item = getattr(self, '_'+name)

            if item.description:
                commented_dict.yaml_add_eol_comment(item.description, name, 32)

        dict_[self.name] = commented_dict

        with open(filename, 'w') as f:
            yaml.round_trip_dump(dict_, f, default_flow_style=False)

    def load(self, filename):
        """Load the configuration state from a given YAML file.

        Parameters
        ----------
        filename : str
            Path to the filename to save to.
        """

        if filename is None:
            return

        with open(filename, 'r') as f:
            dict_ = yaml.load(f, yaml.RoundTripLoader)

        try:
            dict_ = dict_[self.name]
        except KeyError: # no config to load
            return

        for k in dict_:
            setattr(self, k, dict_[k])


