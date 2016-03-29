from datetime import date
import pytest
from todotxt import *  # noqa


def test_textonly():
    task = Task('do something')
    assert task == 'do something'
    assert not task.contexts
    assert not task.projects
    assert not task.is_completed
    assert not task.priority


def test_two_contexts():
    task = Task('do something @context1 @context2')
    assert task == 'do something @context1 @context2'
    assert task.contexts == ['context1', 'context2']
    assert not task.projects
    assert not task.is_completed
    assert not task.priority


def test_two_projects():
    task = Task('do something +project1 +project2')
    assert task == 'do something +project1 +project2'
    assert not task.contexts
    assert task.projects == ['project1', 'project2']
    assert not task.is_completed
    assert not task.priority


def test_project_with_dot_and_dash():
    task = Task('write docs for a +todo.txt-pylib')
    assert task.projects == ['todo.txt-pylib']


def test_single_plus():
    task = Task('this task has a + in the middle')
    assert task == 'this task has a + in the middle'
    assert not task.contexts
    assert not task.projects
    assert not task.is_completed
    assert not task.priority


def test_two_contexts_two_projects():
    task = Task('do something @context1 @context2 +project1 +project2')
    assert task == 'do something @context1 @context2 +project1 +project2'
    assert task.contexts == ['context1', 'context2']
    assert task.projects == ['project1', 'project2']
    assert not task.is_completed
    assert not task.priority


def test_completed_task():
    task = Task('x this task is complete')
    assert task == 'x this task is complete'
    assert not task.contexts
    assert not task.projects
    assert task.is_completed
    assert not task.priority
    task.is_completed = False
    assert task == 'this task is complete'
    task = Task('x 2000-01-01 finalize millenium')
    assert task.is_completed
    assert task.completion_date.value == datetime.date(2000, 1, 1)
    task.is_completed = False
    assert task == 'finalize millenium'


def test_dates():
    task = Task('overdue due:1999-12-31')
    assert task.due_date == datetime.date(1999, 12, 31)
    assert task.is_overdue
    assert task in Task.overdue_tasks()
    task = Task('Good news, everyone! t:2100-01-01')
    assert task.threshold_date == datetime.date(2100, 1, 1)
    assert task.is_on_threshold
    assert task in Task.future_tasks()
    assert task not in Task.active_tasks()
    today = datetime.date.today().strftime('%Y-%m-%d')
    task = Task('almost completed')
    task.is_completed = True
    assert task.is_completed
    assert task == 'x {} almost completed'.format(today)
    assert task in Task.completed_tasks()
    assert task not in Task.active_tasks()
    task = Task('a task')
    task.due_date = '2000-12-31'
    task.threshold_date = datetime.date(2000, 1, 1)
    assert task == 'a task due:2000-12-31 t:2000-01-01'


def test_task_creation_date():
    task = Task('2000-01-01 And now something completely different.')
    assert task.created_date.value == datetime.date(2000, 1, 1)


def test_date_tokens():
    date1 = TaskDueDate('0001-02-03')
    date2 = TaskCreatedDate(date1)
    assert date1.value == date2.value


def test_valid_priority():
    task = Task('(B) do something')
    assert task == '(B) do something'
    assert not task.contexts
    assert not task.projects
    assert not task.is_completed
    assert task.priority.value == 2
    assert str(task.priority) == '(B)'


def test_invalid_priority():
    task = Task('do something (A)')
    assert task == 'do something (A)'
    assert not task.contexts
    assert not task.projects
    assert not task.is_completed
    assert not task.priority


def test_set_priority():
    task1 = Task('(B) do something')
    task2 = Task('(F) do something else')
    assert task1 in TaskPriority.index[2]
    assert task2 in TaskPriority.index[6]
    task2.priority = 2
    assert str(task2) == '(B) do something else'
    assert task2 in TaskPriority.index[2]
    assert task2 not in TaskPriority.index[6]


def test_priority_comparison():
    assert Task('task1').priority == Task('task2').priority
    assert Task('(A) task1').priority == Task('(A) task2').priority
    assert Task('(A) task').priority != Task('task').priority
    assert Task('(A) task').priority > Task('(B) task').priority
    assert Task('(Z) task').priority > Task('task').priority
    assert Task('(B) task').priority < Task('(A) task').priority
    assert Task('task').priority < Task('(Z) task').priority
    assert not TaskPriority(0) < TaskPriority(0)
    assert Task('(A) task1').priority != Task('(AA) task2').priority


def test_increase_priority():
    task = Task('this task has no Priority')
    assert not task.priority
    assert task.priority.value == 0
    assert task.priority.task
    task.priority += 1
    assert task.priority == 26
    assert str(task.priority) == '(Z)'
    task.priority = TaskPriority(20)
    task.priority += 1
    assert task.priority == 19
    assert str(task.priority) == '(S)'
    task += TaskPriority('A')
    task.priority += 1
    assert task.priority == 1
    assert str(task.priority) == '(A)'
    assert task == '(A) this task has no Priority'


def test_decrease_priority():
    task = Task('this task has no Priority')
    assert not task.priority
    task.priority -= 1
    assert task.priority.value == 1
    assert str(task.priority) == '(A)'
    task.priority = TaskPriority(10)
    task.priority -= 1
    assert task.priority.value == 11
    assert str(task.priority) == '(K)'
    task += TaskPriority('Z')
    assert task == '(Z) this task has no Priority'
    task.priority -= 1
    assert not task.priority
    assert str(task.priority) == ''


def test_priority_token():
    priority = TaskPriority(None)
    assert str(priority) == ''
    with pytest.raises(ValueError):
        TaskPriority('abc')
    with pytest.raises(ValueError):
        TaskPriority('ß')
    with pytest.raises(ValueError):
        TaskPriority(29)


def test_token_in_task():
    task = Task('A task with @context')
    assert '@context' in task
    assert TaskContext('context') in task
    assert 'A task' in task


def test_operators():
    task = Task('Lorem ipsum')
    today = date.today()

    task.is_completed = True  # implicitly: task += TaskCompletedDate(today)
    assert task.tokens[1].value == today
    assert task in TaskCompletedDate.index[today]
    task -= TaskCompletedDate
    assert task == 'x Lorem ipsum'

    task += '@context'
    assert task == 'x Lorem ipsum @context'
    assert task in TaskContext.index['context']

    task += TaskCreatedDate('2112-12-21')
    assert task == 'x 2112-12-21 Lorem ipsum @context'
    assert task in TaskCreatedDate.index[date(2112, 12, 21)]

    task += TaskProject('project')
    assert task == 'x 2112-12-21 Lorem ipsum @context +project'
    assert task in TaskProject.index['project']

    task -= TaskContext('context')
    assert task == 'x 2112-12-21 Lorem ipsum +project'
    assert task not in TaskContext.index['context']

    task += 'due:2112-12-01'
    assert task == 'x 2112-12-21 Lorem ipsum +project due:2112-12-01'
    assert task in TaskDueDate.index[date(2112, 12, 1)]

    task += 'due:2112-12-24'
    assert task == 'x 2112-12-21 Lorem ipsum +project due:2112-12-24'
    assert task in TaskDueDate.index[date(2112, 12, 24)]

    task -= TaskCreatedDate
    assert task == 'x Lorem ipsum +project due:2112-12-24'
    assert task not in TaskCreatedDate.index[date(2112, 12, 21)]

    task += TaskPriority(1)
    assert task == 'x (A) Lorem ipsum +project due:2112-12-24'
    assert task in TaskPriority.index[1]

    task -= '+project'
    assert task == 'x (A) Lorem ipsum due:2112-12-24'
    assert task not in TaskProject.index['project']

    task += 'dolor sit'
    assert task == 'x (A) Lorem ipsum due:2112-12-24 dolor sit'

    task -= TaskDueDate
    assert task == 'x (A) Lorem ipsum dolor sit'
    assert task not in TaskDueDate.index[date(2112, 12, 24)]

    task += TaskThresholdDate('t:2113-01-01')
    assert task == 'x (A) Lorem ipsum dolor sit t:2113-01-01'
    assert task in TaskThresholdDate.index[date(2113, 1, 1)]

    task -= '(A)'
    assert task == 'x Lorem ipsum dolor sit t:2113-01-01'
    assert task.priority is None

    task -= 't:2113-01-01'
    assert task == 'x Lorem ipsum dolor sit'
    assert task not in TaskThresholdDate.index[date(2113, 1, 1)]

    task -= 'ipsum'
    assert task == 'x Lorem dolor sit'

    task += [TaskPriority(1), '@context', 'Hello world!']
    assert task == 'x (A) Lorem dolor sit @context Hello world!'

    task -= ['Lorem', 'dolor sit']
    assert task == 'x (A) @context Hello world!'

    with pytest.raises(ValueError):
        task.__iadd__(date(2000, 1, 1))

    with pytest.raises(ValueError):
        task.__isub__(['@context', date(2000, 1, 1)])


def test_invalid_value():
    with pytest.raises(ValueError):
        TaskContext(1.23)


def test_comparison():
    assert Task('task') == Task('task')
    assert Task('(A) task') == Task('(A) task')

    assert Task('one task') != Task('and another')

    assert Task('task1') < Task('task2')
    assert Task('task') < Task('x task')
    assert Task('(A) task') < Task('(B) task')
    assert Task('(A) task') < Task('task')
    assert Task('(A) task') < Task('x (A) task')

    assert Task('task2') > Task('task1')
    assert Task('x task') > Task('task')
    assert Task('(B) task') > Task('(A) task')
    assert Task('task') > Task('(A) task')
    assert Task('x (A) task') > Task('(A) task')

    assert Task('do something +project1 @context1') > Task('(A) do something else +project1 @context2')
    assert Task('something else +project1 @context2') > Task('(A) do something else +project1 @context2')


def test_indexes():
    task = Task('(A) something +todo @work due:2002-02-20')
    assert task in Task.all_tasks()
    assert task in Task.active_tasks()
    assert task not in Task.completed_tasks()
    assert task not in Task.future_tasks()
    assert task in Task.overdue_tasks()
    assert task in TaskPriority.index[1]
    assert task in TaskContext.index['work']
    assert task in TaskProject.index['todo']
    assert task in TaskDueDate.index[datetime.date(2002, 2, 20)]


def test_html():
    for string, html in (
        ('this is my task', '<div class="task">this is my task</div>'),
        ('this is my task @context', '<div class="task">this is my task <span class="context">@context</span></div>'),
        ('this is my task @context and some more words',
         '<div class="task">this is my task <span class="context">@context</span> and some more words</div>'),
        ('this is my task +project', '<div class="task">this is my task <span class="project">+project</span></div>'),
        ('this is my task +project and some more words',
         '<div class="task">this is my task <span class="project">+project</span> and some more words</div>'),
        ('this is my task @context and +project and some more words',
         '<div class="task">this is my task <span class="context">@context</span> and <span class="project">+project'
         '</span> and some more words</div>'),
        ('this is my task @context1 and @context2 and +project1 +project2 and +project3 some more words',
         '<div class="task">this is my task <span class="context">@context1</span> and <span class="context">@context2'
         '</span> and <span class="project">+project1</span> <span class="project">+project2</span> and '
         '<span class="project">+project3</span> some more words</div>'),
        ('(A) this is my task', '<div class="task priority-a"><span class="priority">A</span> this is my task</div>'),
        ('(B) this is my task', '<div class="task priority-b"><span class="priority">B</span> this is my task</div>'),
        ('(C) this is my task', '<div class="task priority-c"><span class="priority">C</span> this is my task</div>'),
        ('(D) this is my task', '<div class="task priority-d"><span class="priority">D</span> this is my task</div>'),
        ('Download https://github.com/mNantern/QTodoTxt/archive/master.zip and extract',
         '<div class="task">Download <a href="https://github.com/mNantern/QTodoTxt/archive/master.zip">'
         'https://github.com/mNantern/QTodoTxt/archive/master.zip</a> and extract</div>'),
        ('https://github.com/mNantern/QTodoTxt/archive/master.zip',
         '<div class="task"><a href="https://github.com/mNantern/QTodoTxt/archive/master.zip">'
         'https://github.com/mNantern/QTodoTxt/archive/master.zip</a></div>'),
        ('http://ginatrapani.org',
         '<div class="task"><a href="http://ginatrapani.org">http://ginatrapani.org</a></div>'),
        ('http://ginatrapani.org/', '<div class="task"><a href="http://ginatrapani.org/">http://ginatrapani.org/</a>'
                                    '</div>'),
        ('file:///home/user/todo.txt',
         '<div class="task"><a href="file:///home/user/todo.txt">file:///home/user/todo.txt'
         '</a></div>'),
        ('http://localhost/?query=tasks/', '<div class="task"><a href="http://localhost/?query=tasks/">'
                                           'http://localhost/?query=tasks/</a></div>'),
        ('+test Do dev+test', '<div class="task"><span class="project">+test</span> Do dev+test</div>')
    ):
        assert Task(string).html == html

        task = 'x Lorem @ipsum'
        Task.html_context_class_mapping = {'ipsum': 'foo'}
        assert Task(task).html == '<div class="task completed foo">x Lorem <span class="context">@ipsum</span></div>'
        Task.html_context_class_mapping = {}


def test_custom_token():
    class BoldToken(BaseToken):
        html_pattern = '<strong>{name}</strong>'
        parse_pattern = re.compile(r'^\*\*(?P<value>\w+)\*\*$')
        str_pattern = '**{name}**'
        type = str

    assert BoldToken in token_types
    assert BoldToken not in fixed_token_types
    assert BoldToken in unambiguous_token_types
    assert Task('add **Markdown** flavor').html == '<div class="task">add <strong>Markdown</strong> flavor</div>'


def test_manager():
    assert isinstance(Task.all_tasks(), TaskManager)

    Task._all_tasks.clear()
    task1 = Task('(A) Lorem ipsum @context1')
    task2 = Task('(B) foo bar +baz.peng-zap')
    all_tasks = Task.all_tasks()

    query = all_tasks.filter(context='context1')
    assert len(query) == 1
    assert task1 in query

    query_list = Task.all_tasks().filter(project='baz.peng-zap').list
    assert len(query_list) == 1
    assert task2 in query_list

    query = all_tasks.filter(priority=1)
    assert len(query) == 1
    assert task1 in query

    query = all_tasks.filter(priority__in=(1, 2))
    assert len(query) == 2
    assert task1 in query and task2 in query

    query = all_tasks.filter(priority=2, context=TaskContext('context1'))
    assert not query


def test_weak_index_setting():
    Task.set_weak_index(False)
    assert isinstance(Task._all_tasks, set)
    Task.set_weak_index(True)
    assert isinstance(Task._all_tasks, WeakSet)
