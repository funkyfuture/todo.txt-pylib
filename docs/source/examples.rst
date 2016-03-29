Examples
========

.. doctest::

    >>> task = Task('2016-03-20 write docs for a +todo.txt-pylib')
    >>> task += '@foss'
    >>> task
    '2016-03-20 write docs for a +todo.txt-pylib @foss'
    >>> task += TaskDueDate(datetime.date(year=2016, month=3, day=25))
    >>> task
    '2016-03-20 write docs for a +todo.txt-pylib @foss due:2016-03-25'
    >>> task.is_overdue
    True
    >>> task -= TaskDueDate


Querying
--------

.. testcode::
    :hide:

    Task._all_tasks.clear()


.. doctest::

    >>> tasks = [Task('2016-03-20 write docs for a +todo.txt-pylib due:2016-03-25')]
    >>> Task.overdue_tasks().list
    ['2016-03-20 write docs for a +todo.txt-pylib due:2016-03-25']
    >>> Task.all_tasks().filter(project='todo.txt-pylib').list
    ['2016-03-20 write docs for a +todo.txt-pylib due:2016-03-25']
    >>> tasks.append(Task('(A) feed the cat'))
    >>> tasks.append(Task('(B) prepare a meal'))
    >>> tasks.append(Task('(Z) go to work'))
    >>> Task.all_tasks().filter(priority__in=(1, 2, 3)).list
    ['(A) feed the cat', '(B) prepare a meal']


Rendering HTML
--------------

.. doctest::

    >>> tasks[0].html
    '<div class="task overdue"><span class="createddate">2016-03-20</span> write docs for a <span class="project">+todo.txt-pylib</span> <span class="duedate">due:2016-03-25</span></div>'
    >>> Task.html_element = 'li'
    >>> del Task.html_property_class_mapping['is_overdue']
    >>> Task.html_project_class_mapping['todo.txt-pylib'] = 'highlight'
    >>> tasks[0].html
    '<li class="task highlight"><span class="createddate">2016-03-20</span> write docs for a <span class="project">+todo.txt-pylib</span> <span class="duedate">due:2016-03-25</span></li>'
    >>> tasks[1].html
    '<li class="task priority-a"><span class="priority">A</span> feed the cat</li>'
    >>> Task.html_include_priority_class = False
    >>> tasks[1].html
    '<li class="task"><span class="priority">A</span> feed the cat</li>'


Extending
---------

.. testcode::
    :hide:

    Task.html_element = 'div'
    Task.html_include_priority_class = True

.. doctest::

    >>> class GithubIssueToken(BaseToken):
    ...     html_pattern = '<a href="https://github.com/{gh_project}/issues/{gh_issue}">{name}</a>'
    ...     parse_pattern = r'(?P<value>\S+/\S+#\d+)'
    ...     type = str
    ...
    ...     @property
    ...     def html(self):
    ...         gh_project, gh_issue = tuple(self.value.split('#'))
    ...         return self.html_pattern.format(gh_project=gh_project, gh_issue=gh_issue, name=self.name)
    >>> task = Task('solve funkyfuture/todo.txt-pylib#1')
    >>> task.html
    '<div class="task">solve <a href="https://github.com/funkyfuture/todo.txt-pylib/issues/1">funkyfuture/todo.txt-pylib#1</a></div>'
