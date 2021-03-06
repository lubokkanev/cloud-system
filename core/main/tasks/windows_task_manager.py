from core.main.constants import Constants
from core.main.tasks import task
from core.main.persistence.persistence_execution_error import \
    PersistenceExecutionError
from core.main.tasks import task_execution_error, task_validation_error
from core.main.persistence.persistence_validation_error import \
    PersistenceValidationError
from core.main.binaries.binary_validation_error import BinaryValidationError
from core.main.runtimes.runtime_validation_error import RuntimeValidationError
from core.main.binaries.binary_execution_error import BinaryExecutionError
from core.main.runtimes.runtime_execution_error import RuntimeExecutionError
from core.main.processes.process_execution_error import ProcessExecutionError
import os


class WindowsTaskManager:

    _READING_FAIL_MESSAGE = 'Task could not be read: '
    _DELETION_FAIL_MESSAGE = 'Task deletion failed: '
    _CREATION_FAIL_MESSAGE = 'Task creation failed: '
    _UPDATE_FAIL_MESSAGE = 'Task update failed: '
    _WINWDOWS_SCRIPT_EXTENSION = '.bat'

    def __init__(self, data_persistence_manager, runtime_manager,
                 binary_manager, process_manager, scripts_location,
                 tasks_loctaion, temp_files_location, nginx_location):
        self.__data_persistence_manager = data_persistence_manager
        self.__binary_manager = binary_manager
        self.__runtime_manager = runtime_manager
        self.__process_manager = process_manager

        self.__tasks_location = tasks_loctaion
        self.__scripts_location = scripts_location
        self.__temp_files_location = temp_files_location
        self.__nginx_location = nginx_location

        self.__task_id_counter = 0
        self._set_proper_id_counter(
            self.__data_persistence_manager.get_all_elements())

    def _set_proper_id_counter(self, tasks):
        self.__task_id_counter = 0

        for task in tasks:
            self.__task_id_counter = max(self.__task_id_counter, task.get_id())

    def _generate_task_id(self):
        return ++self.__task_id_counter

    def _generate_script(self, task):
        pass

    def create_task(self, runtime_id, binary_id, owner):
        try:
            binary = self.__binary_manager.read_binary(binary_id)
            runtime = self.__runtime_manager.read_runtime(runtime_id)

            task_id = self._generate_task_id()
            new_task = task(task_id, runtime, binary,
                            Constants.TASK_DESCRIPTION_FORMAT.format(
                                binary.get_description(),
                                runtime.get_description()))
            script_file = self._generate_script()

            try:
                self.__data_persistence_manager.cleate_element(task_id,
                                                               new_task)
            except PersistenceExecutionError as e:
                os.remove(script_file)
                raise task_execution_error(
                    self._CREATION_FAIL_MESSAGE + str(e))
            except PersistenceValidationError as e:
                os.remove(script_file)
                raise task_validation_error(
                    self._CREATION_FAIL_MESSAGE + str(e))

            return task_id
        except (BinaryValidationError, RuntimeValidationError) as e:
            raise task_validation_error(self._CREATION_FAIL_MESSAGE + str(e))
        except (BinaryExecutionError, RuntimeExecutionError) as e:
            raise task_execution_error(self._CREATION_FAIL_MESSAGE + str(e))

    def _has_running_instances(self, task):
        try:
            for process in self.__process_manager.get_active_processes():
                if process.get_task_id() == task:
                    return True
        except ProcessExecutionError as e:
            raise task_execution_error(str(e))

        return False

    def read_task(self, task_id):
        try:
            return self.__data_persistence_manager.read_element(task_id)
        except PersistenceExecutionError as e:
            raise task_execution_error(self._READING_FAIL_MESSAGE + str(e))
        except PersistenceValidationError as e:
            raise task_validation_error(self._READING_FAIL_MESSAGE + str(e))

    def delete_task(self, task_id, user):
        try:
            if self.read_task(task_id).get_owner is not user:
                raise task_validation_error('Tasks can only be deleted by their \
                owner.')

            if self._has_running_instances(self.read_task(task_id)):
                raise task_validation_error('Can\'t delete a task that has \
                running instances.')

            deleted_task = self.__data_persistence_manager
            script_file_path = self.__scripts_location +\
                deleted_task.get_execution_filename() +\
                self._WINWDOWS_SCRIPT_EXTENSION
            os.remove(script_file_path)
        except PersistenceValidationError as e:
            raise task_validation_error(self._DELETION_FAIL_MESSAGE + str(e))
        except PersistenceExecutionError as e:
            raise task_execution_error(self._DELETION_FAIL_MESSAGE + str(e))

    def get_all_tasks(self):
        try:
            return self.__data_persistence_manager.get_all_elements()
        except PersistenceExecutionError as e:
            raise task_execution_error('Could not get tasks: ' + str(e))

    def run_task(self, task_id, args, user):
        task = self.read_task(task_id)

        if task.get_owner() is not user:
            raise task_validation_error('Tasks can only be started by their \
            owner.')

    def update_task(self, task_id, runtime_id, binary_id, user):
        try:
            runtime = self.__runtime_manager.read_runtime(runtime_id)
            binary = self.__binary_manager.read_binary(binary_id)
            old_task = self.read_task(task_id)

            if old_task.get_owner is not user:
                raise task_validation_error('Tasks can only be updated by their \
                owner.')

            new_task = task(task_id, runtime, binary,
                            Constants.TASK_DESCRIPTION_FORMAT.format(
                                binary.get_description(),
                                runtime.get_description()), user)

            script_path = self.__scripts_location +\
                old_task.get_execution_filename() +\
                self._WINDOWS_SCRIPT_EXTENSION
            backup_script_path = script_path + '_old'
            os.rename(script_path, backup_script_path)

            new_file = self._generate_script(new_task)

            try:
                self.__data_persistence_manager.update_element(task_id,
                                                               new_task)
                os.remove(backup_script_path)
            except PersistenceExecutionError as e:
                os.remove(new_file)
                os.rename(backup_script_path, script_path)
                raise task_execution_error(self._UPDATE_FAIL_MESSAGE + str(e))
            except PersistenceValidationError as e:
                os.remove(new_file)
                os.rename(backup_script_path, script_path)
                raise task_validation_error(self._UPDATE_FAIL_MESSAGE + str(e))
        except (RuntimeValidationError, BinaryValidationError) as e:
            raise task_validation_error(self._UPDATE_FAIL_MESSAGE + str(e))
        except (RuntimeExecutionError, BinaryExecutionError) as e:
            raise task_execution_error(self._UPDATE_FAIL_MESSAGE +
                                       'Data could not be read.')
