import mock
import pinject

from mock import MagicMock

from assistants.task_spawner.task_spawner_assistant import TaskSpawner


class MockTaskSpawnerHolder:
	task_spawner = None

	@pinject.copy_args_to_public_fields
	def __init__(self, task_spawner):
		pass


class MockTaskSpawner(pinject.BindingSpec):
	task_spawner = None

	def __init__(self, patched_task_spawner):
		self.patched_task_spawner = patched_task_spawner
		self.task_spawner = self.patched_task_spawner.start()

	@pinject.provides("task_spawner")
	def provide_task_spawner( self ):
		return self.task_spawner
