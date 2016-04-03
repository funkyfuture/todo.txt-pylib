"""
This module provides a pythonic interface to Gina Trapani's todo.txt_-format for Python 3.

.. _todo.txt: http://todotxt.com
"""

from collections import defaultdict, Iterable
import datetime
import inspect
import operator
import re
from weakref import WeakSet


__version__ = '0.1-1'
SOURCE_URL = 'https://github.com/funkyfuture/todo.txt-pylib'


__operators = {}


def get_operator_function(name):
    if name == 'in':
        return operator.contains
    if name not in __operators:
        __operators[name] = dict(inspect.getmembers(operator))[name]
    return __operators[name]


class TaskManager(WeakSet):
    """ A set of tasks that can be filtered. """
    @property
    def list(self):
        # TODO
        return sorted(self)

    def filter(self, **criterias):
        """ Filter all tasks that match the criterias passed as keyword-arguments.

        Each keyword must be the name of a property and can have an operator appended seperated by `__` (that's two
        underscores).
        If the singular form of a property with a plural name is given as keyword, it is tested whether the argument is
        contained ``in`` that property.

        >>> Task.all_tasks().filter(is_overdue=False)
        >>> Task.all_tasks().filter(priority__in=(1, 2, 3))
        >>> Task.all_tasks().filter(context='workshop', projects=[])

        :return: A new set of tasks.
        :rtype: :class:`TaskManager`
        """
        matches = self.copy()
        for criteria, argument in criterias.items():
            criteria_matches = set()
            attribute, op, swap_operands = self.__figure_out_task_attribute_and_operator(criteria)
            for task in self:
                value = getattr(task, attribute)
                if value is None:
                    continue
                a, b = (argument, value) if swap_operands else (value, argument)
                if op(a, b):
                    criteria_matches.add(task)
            matches &= criteria_matches
        return matches

    def tuple(self):
        return tuple(self.list)

    @staticmethod
    def __figure_out_task_attribute_and_operator(criteria):
        swap_operands = False

        if '__' in criteria:
            attribute, op = criteria.split('__')
            op = get_operator_function(op)
        else:
            attribute, op = criteria, operator.eq

        if not hasattr(Task, attribute):
            if hasattr(Task, attribute + 's'):
                op = operator.contains
                attribute += 's'
            else:
                raise RuntimeError("Task doesn't have such attribute.")
        elif op is operator.contains:
            swap_operands = True

        return attribute, op, swap_operands

    def __str__(self):
        return self


class Task:
    """
    This class describes a task and provides several methods to access and modify it.
    It also provides class-attributes and -methods to retrieve all or a subset of tasks.

    :param line: A task in todo.txt-format.
    :type line: :class:`str`

    These are expressions that create and modify a Task-instance:

    >>> task = Task('some task')
    >>> task += token
    >>> task -= token

    A token can be any instance of those defined in this module, registered with the :func:`task_token`-decorator or a
    string. Any other type will be converted to a string before parsing. The string will then be parsed into the proper
    token-class.

    An instance of Task provides several properties to query aspects of a task.
    Those aspects that are singletons can also be modified through a property, e.g.:

    >>> task.priority += 1
    >>> task.due_date = datetime.date.today()

    These are expressions to test a Task-instance:

    >>> token in task
    >>> task1 == task2
    >>> task1 != task2
    >>> task1 > task2
    >>> task1 < task2

    Tasks can be rendered as unicode-strings or html:

    >>> print(task)
    >>> print(task.html)

    To obtain a :class:`TaskManager` with preset filters , invoke these methods:
    :meth:`all_tasks`, :meth:`active_tasks`, :meth:`completed_tasks`, :meth:`future_tasks`, :meth:`overdue_tasks`
    """

    _all_tasks = WeakSet()
    html_element = 'div'
    """ The HTML-element that wraps the task in :attr:`html`. """
    html_class = 'task'
    """ Class(es) to include in :attr:`html`. """
    html_include_priority_class = True
    """ If ``True``, include a class like ``priority-a`` in :attr:`html` for tasks with a priority. """
    html_property_class_mapping = {
        'is_completed': 'completed',
        'is_on_threshold': 'threshold',
        'is_overdue': 'overdue'}
    """ If a key in this mapping returns ``True``, the value is added to the classes of :attr:`html`. """
    html_context_class_mapping = {}
    """ If a key in this mapping is in :attr:`contexts`, the the value is added to the classes of :attr:`html`. """
    html_project_class_mapping = {}
    """ If a key in this mapping is in :attr:`projects`, the the value is added to the classes of :attr:`html`. """

    def __init__(self, line):
        self.tokens = line.split(' ')
        """ The tokens of a task. """

        if self.tokens[0] == 'x':
            self.tokens[0] = TaskString('x')
            if TaskCompletedDate.parse_pattern.match(self.tokens[1]):
                self.tokens[1] = TaskCompletedDate(self.tokens[1], self)
            else:
                self.tokens.insert(1, None)
        else:
            self.tokens.insert(0, None)
            self.tokens.insert(1, None)

        if TaskPriority.parse_pattern.match(self.tokens[2]):
            self.tokens[2] = TaskPriority(self.tokens[2], self)
        else:
            self.tokens.insert(2, TaskPriority(0, self))

        if TaskCreatedDate.parse_pattern.match(self.tokens[3]):
            self.tokens[3] = TaskCreatedDate(self.tokens[3], self)
        else:
            self.tokens.insert(3, None)

        for i, token in enumerate(self.tokens[4:], start=4):
            self.tokens[i] = self.__parse_string_to_token(token)

        self._all_tasks.add(self)

    def __parse_string_to_token(self, string):
        for token_type in unambiguous_token_types:
            if token_type.parse_pattern.match(string):
                return token_type(string, self)
        else:
            return TaskString(string)

    def __iadd__(self, value):
        """ Add a token to a task.
            In case singleton-tokens such as priority are given, the token will be replaced.

        Examples:

        >>> task += TaskProject('project')
        >>> task += TaskCompletedDate('2014-08-05')
        >>> task += '(A)'
        >>> task += '+project'
        >>> task += 'two words'
        >>> task += ['@some', '@more', '@contexts']

        :param value: The token to add.
        :type value: a subclass of :class:`BaseToken` or :class:`str`
        """
        value = self.__handle_iterable_value_for_operator(value, self.__iadd__)
        if value is None:
            return self

        if not isinstance(value, tuple(token_types)):
            raise ValueError('{} is not supported by this operation.'.format(value.__class__.__name__))

        value.task = self
        if isinstance(value, BaseIndexedToken):
            if value.is_singleton:
                value.__class__.index._discard(self)
                if value.fixed_pos:
                    self.tokens[value.fixed_pos] = value
                else:
                    for i in range(1, len(self.tokens)):
                        if isinstance(self.tokens[i], type(value)):
                            self.tokens[i] = value
                            break
                    else:
                        self.tokens.append(value)
            else:
                self.tokens.append(value)
            value.__class__.index[value.value].add(self)
        else:
            self.tokens.append(value)

        return self

    def __isub__(self, value):
        """ Remove a token from a task.
            Singleton tokens can be removed by passing the class.

        Examples:

        >>> task -= TaskContext('context')
        >>> task -= TaskPriority
        >>> task -= '+project'
        >>> task -= 'two words'
        >>> task -= [TaskDueDate, '@urgent']

        :param value: The token to remove
        :type value: a subclass of :class:`BaseToken` or :class:`str`
        """
        value = self.__handle_iterable_value_for_operator(value, self.__isub__)
        if value is None:
            return self

        if not (isinstance(value, tuple(token_types)) or
                inspect.isclass(value) and issubclass(value, BaseToken) and value.is_singleton):
            raise ValueError('{} is not supported by this operation.'.format(value.__class__.__name__))

        value_class = value if inspect.isclass(value) else value.__class__

        if value.is_singleton:
            if value.fixed_pos:
                self.tokens[value.fixed_pos] = None
                value_class.index._discard(self)
            else:
                for i in self._unfixed_tokens_range:
                    if self.tokens[i].__class__ == value_class:
                        del self.tokens[i]
                        value_class.index._discard(self)
                        break
        else:
            for i in self._unfixed_tokens_range:
                if self.tokens[i].__class__ == value_class and self.tokens[i].value == value.value:
                    del self.tokens[i]
                    if isinstance(value, BaseIndexedToken):
                        value_class.index[value.value].discard(self)
                    break

        return self

    def __handle_iterable_value_for_operator(self, value, op):
        if isinstance(value, str):
            if ' ' in value:
                for word in value.split(' '):
                    op(word)
                return None
            else:
                return self.__parse_string_to_token(value)
        elif isinstance(value, Iterable):
            for item in value:
                op(item)
            return None
        else:
            return value

    def __contains__(self, item):
        """ Test if a token or a string is contained in the task.

        Example:

        >>> [ x for x in tasks if TaskPriority(1) in x ]
        """
        if item in self.tokens:
            return True
        if item in str(self):
            return True
        return False

    def __hash__(self):
        # necessary to add a task to a set, not actually a hash
        return id(self)

    def __eq__(self, other):
        return str(self) == str(other)

    def __lt__(self, other):
        if not self.is_completed and other.is_completed:
            return True
        elif self.is_completed and not other.is_completed:
            return False
        if self.priority > other.priority:
            return True
        if self.threshold_date is not None:
            if other.threshold_date is None:
                return False
            if self.threshold_date < other.threshold_date:
                return True
        if self.due_date is not None:
            if other.due_date is None:
                return True
            if self.due_date < other.due_date:
                return True
        if self.completion_date is not None:
            if other.completion_date is None:
                return True
            if self.completion_date > other.completion_date:
                return True
        if self.created_date is not None:
            if other.created_date is None:
                return True
            if self.created_date > other.created_date:
                return True
        if str(self) < str(other):
            return True
        return False

    def __gt__(self, other):
        return not self < other and not self == other

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return ' '.join(str(x) for x in self.tokens if x).strip()

    def __repr__(self):
        return "'{string}'".format(string=str(self))

    @property
    def _unfixed_tokens_range(self):
        return range(4, len(self.tokens))

    @classmethod
    def all_tasks(cls):
        """ Returns a :class:`TaskManager` with all tasks. """
        return TaskManager(cls._all_tasks)

    @classmethod
    def active_tasks(cls):
        """ Returns a :class:`TaskManager` with tasks that are not completed and not on threshold. """
        return cls.all_tasks() - cls.completed_tasks() - cls.future_tasks()

    @classmethod
    def completed_tasks(cls):
        """ Returns a :class:`TaskManager` with all completed tasks. """
        return cls.all_tasks().filter(is_completed=True)

    @classmethod
    def future_tasks(cls):
        """ Returns a :class:`TaskManager` with tasks whose threshold-date is in the future. """
        return cls.all_tasks().filter(threshold_date__gt=datetime.date.today())

    @classmethod
    def overdue_tasks(cls):
        """ Returns a :class:`TaskManager` with overdue tasks. """
        return cls.all_tasks().filter(due_date__lt=datetime.date.today())

    @property
    def contexts(self):
        """ The contexts of a task. """
        return sorted(x for x in TaskContext.index if self in TaskContext.index[x])

    @property
    def completion_date(self):
        """ The date when a task was marked as completed. """
        return self.tokens[1]

    @completion_date.setter
    def completion_date(self, value):
        self += TaskCompletedDate(value)

    @property
    def created_date(self):
        """ The date when a task was created. """
        return self.tokens[3]

    @created_date.setter
    def created_date(self, value):
        self += TaskCreatedDate(value)

    @property
    def due_date(self):
        """ The date when a task is due. """
        for token in self.tokens[4:]:
            if isinstance(token, TaskDueDate):
                return token
        return None

    @due_date.setter
    def due_date(self, value):
        self -= TaskDueDate()
        self += TaskDueDate(value)

    @property
    def html(self):
        """ HTML-representation of a task. """
        return '<{element}{classes}>{task}</{element}>'.format(
            element=self.html_element,
            classes=self.html_classes_string,
            task=' '.join(x.html for x in self.tokens if x)
        )

    @property
    def html_classes_string(self):
        result = []
        if self.html_class:
            result.append(self.html_class)
        if self.html_include_priority_class and self.priority:
            result.append('priority-' + self.priority.name.lower())
        for attribute, klass in self.html_property_class_mapping.items():
            if getattr(self, attribute):
                result.append(klass)
        for context, klass in self.html_context_class_mapping.items():
            if context in self.contexts:
                result.append(klass)
        for project, klass in self.html_project_class_mapping.items():
            if project in self.projects:
                result.append(klass)
        if result:
            return ' class="' + ' '.join(result) + '"'
        else:
            return ''

    @property
    def is_completed(self):
        """ Whether a task is marked as completed. """
        return self.tokens[0] == 'x'

    @is_completed.setter
    def is_completed(self, value):
        if bool(value):
            self.tokens[0] = 'x'
            self += TaskCompletedDate(datetime.date.today())
        else:
            self.tokens[0] = ' '
            self -= TaskCompletedDate()

    @property
    def is_on_threshold(self):
        return self.threshold_date and self.threshold_date > datetime.date.today()

    @property
    def is_overdue(self):
        return self.due_date and self.due_date < datetime.date.today()

    @property
    def priority(self):
        """ The task's priority. """
        return self.tokens[2]

    @priority.setter
    def priority(self, value):
        self += TaskPriority(value)

    @property
    def projects(self):
        """ The projects of a task. """
        return sorted(x for x in TaskProject.index if self in TaskProject.index[x])

    @property
    def threshold_date(self):
        """ The date until when a task is on threshold. """
        for token in self.tokens[4:]:
            if isinstance(token, TaskThresholdDate):
                return token
        return None

    @threshold_date.setter
    def threshold_date(self, value):
        self += TaskThresholdDate(value)

    @classmethod
    def set_weak_index(cls, setting):
        """ Sets whether to keep tasks in a weak-referenced container or not.

            It is assumed that the client code keeps the task it creates
            assigned as or in some variables. Thus the index of created is a
            :class:`weakref.WeakSet` by default.

            :param setting: Whether to use a ``Weakset`` or a :class:`set`
            :type setting: :class:`bool`
        """
        if setting and isinstance(cls._all_tasks, set):
            Task._all_tasks = WeakSet(Task._all_tasks)
        elif not setting and isinstance(cls._all_tasks, WeakSet):
            Task._all_tasks = set(Task._all_tasks)


token_types = set()
""" All token types. """
_fixed_positions = set()
fixed_token_types = []
""" All token types with a fixed position within a task's tokens sequence. """
unambiguous_token_types = set()
""" The token types that can clearly be identified by their string representation. """


class _RegisterClass(type):
    def __new__(cls, name, bases, attributes):
        if name.startswith('Base'):
            return super().__new__(cls, name, bases, attributes)

        for attribute, _type in (('fixed_pos', (int, None.__class__)),
                                 ('html_pattern', str),
                                 ('is_singleton', bool),
                                 ('str_pattern', str)):
            if attribute in attributes:
                assert isinstance(attributes[attribute], _type)

        global _fixed_positions
        if 'fixed_pos' in attributes:
            assert attributes['fixed_pos'] not in _fixed_positions

        if 'parse_pattern' in attributes:
            attributes['parse_pattern'] = re.compile(attributes['parse_pattern'])

        _type = attributes.get('type')
        if _type is not None:
            if not isinstance(_type, tuple):
                _type = (_type,)
            assert all(isinstance(x, type) for x in _type)

        return super().__new__(cls, name, bases, attributes)

    def __init__(cls, name, bases, attributes):
        super().__init__(name, bases, attributes)

        if name.startswith('Base'):
            return

        global _fixed_positions, fixed_token_types, token_types, unambiguous_token_types

        token_types.add(cls)

        for token_type in unambiguous_token_types:
            if cls.parse_pattern.pattern == token_type.parse_pattern.pattern:
                unambiguous_token_types.discard(token_type)
                break
        else:
            unambiguous_token_types.add(cls)

        if cls.fixed_pos is not None:
            _fixed_positions.add(cls.fixed_pos)
            fixed_token_types.append(cls)
            fixed_token_types.sort(key=lambda obj: obj.fixed_pos)


class _RegisterLeafClassesWithIndex(_RegisterClass):
    def __new__(cls, name, bases, atttributes):
        atttributes['index'] = TokenIndex()
        return super().__new__(cls, name, bases, atttributes)


class BaseToken(metaclass=_RegisterClass):
    """ Base class for any token.

        :param value: A representation of the token's value.
        :type value: as defined in the :attr:`type` attribute or :obj:`None`
        :param task: The referencing task.
        :type task: :class:`Task`
    """

    fixed_pos = None
    """ The fixed position of this token type in the :attr:`Task.tokens` or :obj:`None`. """
    html_pattern = None
    """ The pattern to format the HTML-representation of a token. """
    is_singleton = False
    """ Whether there can only be one such token in a task. """
    parse_pattern = None
    """ A regular expression that matches todo.txt's format for a token and returns the token's value
        from a regex group named ``value`` """
    str_pattern = None
    """ The pattern to format the string-representation of a token. """
    type = None
    """ The types that can be converted to the token's value representation. """
    value = None
    """ The token's internal value representation. """

    def __init__(self, value, task):
        if value is None:
            self.value = None
            self.task = None
        else:
            if not isinstance(value, (self.type, self.__class__)) and value is not None:
                raise ValueError('Expecting a {type} or {cls} instance.'.format(cls=self.__class__, type=self.type))
            self.value = self._duck(value)
            self.task = task

    @classmethod
    def _duck(cls, value):
        """ Cast the given input into the class' value type. """
        if cls.parse_pattern.match(value):
            return cls.parse_pattern.match(value).group('value')
        else:
            return value

    @classmethod
    def _other_value(cls, other):
        """ Get the value-property of other if it's the same class. """
        if isinstance(other, cls):
            return other.value
        return other

    def __eq__(self, other):
        return self.value == self._other_value(other)

    def __ge__(self, other):
        return self > other or self == other

    def __gt__(self, other):
        return self.value > self._other_value(other)

    def __le__(self, other):
        return not self > other or self == other

    def __lt__(self, other):
        return not self == other and not self > other

    def __ne__(self, other):
        return not self == other

    @property
    def html(self):
        """ The HTML-representation of the token. """
        return self.html_pattern.format(name=self.name)

    @property
    def name(self):
        """ The token's string representation without any type indicator. """
        return self.value

    def __str__(self):
        return self.str_pattern.format(name=self.name)


class TokenIndex(defaultdict):
    """ An index of task-tokens; tasks grouped by token value. """
    def __init__(self):
        super().__init__(WeakSet)

    def _discard(self, task):
        for indexed_tasks in self.values():
            indexed_tasks.discard(task)


class BaseIndexedToken(BaseToken, metaclass=_RegisterLeafClassesWithIndex):
    """ Base class for tokens that keep track of their associated tasks. """

    index = None
    """ The index of all known values and the tasks they are used in. """

    def __init__(self, value=None, task=None):
        super().__init__(value, task)
        if self.task:
            if self.is_singleton:
                self.index._discard(task)
            self.index[self.value].add(self.task)


class BaseDateToken(BaseIndexedToken):
    """ Base class for tokens that represent some date. """
    is_singleton = True
    parse_pattern = re.compile(r'^(?P<value>\d{4}-\d{2}-\d{2})$')
    type = (datetime.date, str)

    def __init__(self, value=None, task=None):
        if isinstance(value, BaseDateToken):
            value = value.value
        super().__init__(value, task)

    @classmethod
    def _duck(cls, value):
        if isinstance(value, str):
            if cls.parse_pattern.match(value):
                value = cls.parse_pattern.match(value).group('value')
            elif not BaseDateToken.parse_pattern.match(value):
                raise ValueError
            value = datetime.datetime.strptime(value, '%Y-%m-%d').date()
        return value

    @property
    def name(self):
        return '{:04d}-{:02d}-{:02d}'.format(self.value.year, self.value.month, self.value.day)


class TaskCompletedDate(BaseDateToken):
    """ A token that represents the date when a task was marked as completed. """
    fixed_pos = 1
    html_pattern = '<span class="completeddate">{name}</span>'
    str_pattern = '{name}'


class TaskContext(BaseIndexedToken):
    """ A token that represents one task's context. """
    html_pattern = '<span class="context">@{name}</span>'
    parse_pattern = r'^@(?P<value>\S+)$'
    str_pattern = '@{name}'
    type = str


class TaskCreatedDate(BaseDateToken):
    """ A token that represents the date when a task was created. """
    fixed_pos = 3
    html_pattern = '<span class="createddate">{name}</span>'
    str_pattern = '{name}'


class TaskDueDate(BaseDateToken):
    """ A token that represents a task's due date. """
    html_pattern = '<span class="duedate">due:{name}</span>'
    parse_pattern = r'^due:(?P<value>\d{4}-\d{2}-\d{2})$'
    str_pattern = 'due:{name}'


class TaskPriority(BaseIndexedToken):
    """ A token that represents a task's priority. """
    fixed_pos = 2
    html_pattern = '<span class="priority">{name}</span>'
    is_singleton = True
    parse_pattern = r'^\((?P<value>[A-Z])\)$'
    str_pattern = '({name})'
    type = (str, int)

    @classmethod
    def _duck(cls, value):
        if value is None:
            value = 0
        elif isinstance(value, TaskPriority):
            value = value.value
        elif isinstance(value, str):
            if cls.parse_pattern.match(value):
                value = cls.parse_pattern.match(value).group('value')
            if len(value.upper()) != 1:
                raise ValueError('String must be one character long. It may be surrounded by a pair of brackets.')
            else:
                value = ord(value.upper()) - 64
        if not 0 <= value <= 26:
            raise ValueError('Expecting an int [0-26] or string [A-Z ].')
        return value

    def __iadd__(self, other):
        if not self.value:
            result = 27 - other
        else:
            result = self.value - other
        result = 1 if result < 1 else result
        if self.task:
            self.task.priority = result
        return result

    def __isub__(self, other):
        if not self.value:
            result = 0 + other
        else:
            result = self.value + other
        result = 0 if result > 26 else result
        if self.task:
            self.task.priority = result
        return result

    def __gt__(self, other):
        other = self._other_value(other)
        if not self.value and not other:
            return False
        elif not self.value:
            return False
        elif not other:
            return True
        return self.value < other

    def __lt__(self, other):
        other = self._other_value(other)
        if other == 0:
            return False
        if self.value == 0:
            return True
        return self.value > other

    def __bool__(self):
        return bool(self.value)

    @property
    def html(self):
        if not self.value:
            return ''
        return self.html_pattern.format(name=self.name)

    @property
    def name(self):
        if not self.value:
            return ' '
        return chr(self.value + 64)

    def __str__(self):
        if not self.value:
            return ''
        return super().__str__()


class TaskProject(BaseIndexedToken):
    """ A token that represents one task's project. """
    html_pattern = '<span class="project">+{name}</span>'
    parse_pattern = r'^\+(?P<value>\S+)$'
    str_pattern = '+{name}'
    type = str


class TaskString(str):
    """ A plain sequence of characters. """
    is_singleton = False

    @property
    def html(self):
        return self

    @property
    def value(self):
        return self


token_types.add(TaskString)


class TaskThresholdDate(BaseDateToken):
    """ A token that represents a task's threshold date. """
    html_pattern = '<span class="thresholddate">t:{name}</span>'
    parse_pattern = r'^t:(?P<value>\d{4}-\d{2}-\d{2})$'
    str_pattern = 't:{name}'


class Url(BaseToken):
    """ A token that represents an URL. """
    html_pattern = '<a href="{name}">{name}</a>'
    parse_pattern = re.compile(
        r'^(?P<value>'  # noqa
            r'((https?|ftp)://'  # http(s)- or ftp-scheme
                r'(\S+(:\S+)?@)?'  # optional user:password@
                    r'(([A-Z0-9]([A-Z0-9-]{0,61}[A-Z0-9])\.?)+|'  # hostname ...
                    r'(\d{1,3}\.){3}\d{1,3}|'  # ...or ipv4
                    r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'  # ...or ipv6
                r'(:\d{1,5})?'  # optional port
                r'(/?|[/?]\S+)|'  # (no) trailing slash and anything in the path
            r'file:///.*)'  # ..or sleazy file-scheme
        r')$',  # the end
        re.IGNORECASE)
    str_pattern = '{name}'
    type = str
