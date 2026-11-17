"""Módulo "tarefas": lista de afazeres guardada no SQLite (equivale a TasksModule do C++)."""

from datetime import date

from jarvis.core.command import Response
from jarvis.core.database import Database
from jarvis.core.errors import JarvisError
from jarvis.core.module import Context, Module, action
from jarvis.modules.tasks import migrations
from jarvis.modules.tasks.models import (
    AddTaskArgs,
    EditTaskArgs,
    ListTasksArgs,
    Priority,
    Task,
    TaskFilter,
    TaskIdArgs,
)
from jarvis.modules.tasks.repository import TaskRepository

_WEEKDAYS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
_PRIORITY_LABEL = {Priority.low: "baixa", Priority.medium: "média", Priority.high: "alta"}


def _due_label(due: date, today: date) -> str:
    """Prazo em português: "hoje", "amanhã", "sex 20/11", "atrasada (15/11)"."""
    days = (due - today).days
    if days < 0:
        return f"atrasada ({due:%d/%m})"
    if days == 0:
        return "hoje"
    if days == 1:
        return "amanhã"
    label = f"{_WEEKDAYS[due.weekday()]} {due:%d/%m}"
    return label if days < 7 else f"{due:%d/%m}" if due.year == today.year else f"{due:%d/%m/%Y}"


def _line(task: Task, today: date) -> str:
    parts = [f"#{task.id} {'[x]' if task.done else '[ ]'} {task.title}"]
    if task.due_date and not task.done:
        parts.append(_due_label(task.due_date, today))
    if task.priority is not Priority.medium:
        parts.append(_PRIORITY_LABEL[task.priority])
    return " · ".join(parts)


def _summary(task: Task, verb: str) -> str:
    return f"Tarefa #{task.id} {verb}: {task.title}"


class TasksModule(Module):
    name = "tarefas"

    def init(self, db: Database) -> None:
        for version, sql in enumerate(migrations.ALL, start=1):
            db.migrate(self.name, version, sql)  # não faz nada se já estiver aplicada

    @staticmethod
    def _get(ctx: Context, task_id: int) -> Task:
        task = TaskRepository(ctx.db).find(task_id)
        if task is None:
            raise JarvisError(f"Tarefa #{task_id} não encontrada.")
        return task

    @action("add", "Adiciona uma tarefa", args=AddTaskArgs, result=Task, text_arg="title")
    def add(self, ctx: Context, args: AddTaskArgs) -> Response[Task]:
        task = TaskRepository(ctx.db).add(args.title, args.due_date, args.priority, ctx.now)
        return Response.success(_summary(task, "adicionada"), task)

    @action(
        "listar",
        "Lista as tarefas: pendentes (padrão), todas, ou hoje (atrasadas e de hoje)",
        args=ListTasksArgs,
        result=list[Task],
        text_arg="filter",
    )
    def listar(self, ctx: Context, args: ListTasksArgs) -> Response[list[Task]]:
        tasks = TaskRepository(ctx.db).list(args.filter, ctx.today)
        if not tasks:
            empty = {
                TaskFilter.pending: "Nenhuma tarefa pendente.",
                TaskFilter.all: "Nenhuma tarefa.",
                TaskFilter.today: "Nada atrasado nem para hoje.",
            }[args.filter]
            return Response.success(empty, [])
        return Response.success("\n".join(_line(t, ctx.today) for t in tasks), tasks)

    @action("feito", "Marca uma tarefa como concluída", args=TaskIdArgs, result=Task, text_arg="id")
    def feito(self, ctx: Context, args: TaskIdArgs) -> Response[Task]:
        task = self._get(ctx, args.id)
        if task.done:
            raise JarvisError(f"Tarefa #{task.id} já estava concluída.")
        TaskRepository(ctx.db).set_done(task.id, ctx.now)
        return Response.success(_summary(task, "concluída"), self._get(ctx, task.id))

    @action("reabrir", "Reabre uma tarefa concluída", args=TaskIdArgs, result=Task, text_arg="id")
    def reabrir(self, ctx: Context, args: TaskIdArgs) -> Response[Task]:
        task = self._get(ctx, args.id)
        if not task.done:
            raise JarvisError(f"Tarefa #{task.id} já está pendente.")
        TaskRepository(ctx.db).set_done(task.id, None)
        return Response.success(_summary(task, "reaberta"), self._get(ctx, task.id))

    @action(
        "editar",
        "Muda título, prazo ou prioridade de uma tarefa",
        args=EditTaskArgs,
        result=Task,
        text_arg="id",
    )
    def editar(self, ctx: Context, args: EditTaskArgs) -> Response[Task]:
        task = self._get(ctx, args.id)
        changed = args.model_fields_set - {"id"}
        if not changed:
            raise JarvisError("Nada para editar. Mande título, prazo ou prioridade.")
        if "title" in changed and args.title is None:
            raise JarvisError("Título não pode ficar vazio.")
        if "priority" in changed and args.priority is None:
            raise JarvisError("Prioridade não pode ficar vazia. Use low, medium ou high.")
        TaskRepository(ctx.db).update(
            task.id,
            title=args.title,
            priority=args.priority,
            due_date=args.due_date,
            set_due_date="due_date" in changed,
        )
        updated = self._get(ctx, task.id)
        return Response.success(_summary(updated, "editada"), updated)

    @action("remover", "Apaga uma tarefa", args=TaskIdArgs, result=Task, text_arg="id")
    def remover(self, ctx: Context, args: TaskIdArgs) -> Response[Task]:
        task = self._get(ctx, args.id)
        TaskRepository(ctx.db).remove(task.id)
        return Response.success(_summary(task, "removida"), task)
