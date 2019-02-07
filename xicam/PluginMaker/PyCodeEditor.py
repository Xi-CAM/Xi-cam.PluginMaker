import sys

from qtpy.QtCore import  *
from qtpy.QtWidgets import *

from pyqode.core.api import ColorScheme
from pyqode.python.backend import server
from pyqode.core import api
from pyqode.core import modes
from pyqode.core import panels
from pyqode.python import managers as pymanagers
from pyqode.python import modes as pymodes
from pyqode.python import panels as pypanels
from pyqode.python.backend.workers import defined_names
from pyqode.python.folding import PythonFoldDetector

from pyqode.python.backend import server
from pyqode.core import api, modes, panels
from pyqode.python import modes as pymodes, panels as pypanels, widgets
from pyqode.python.folding import PythonFoldDetector
from pyqode.python.backend.workers import defined_names
from pyqode.core.widgets import InteractiveConsole

from pyqode.core.widgets import InteractiveConsole


from pyqode.core.api.manager import Manager
from pyqode.python.backend.workers import JediCompletionProvider
from pyqode.core.backend.workers import DocumentWordsProvider

import time

from pyqode.core import backend
import logging

logging.getLogger("pyqode.core.backend.workers.DocumentWordsProvider").disabled = True
logging.getLogger("pyqode.core.backend.workers.JediCompletionProvider").disabled = True
logging.basicConfig(level="critical")


def import_class(klass):
    """
    Imports a class from a fully qualified name string.

    :param klass: class string, e.g.
        "pyqode.core.backend.workers.CodeCompletionWorker"
    :return: The corresponding class

    """
    path = klass.rfind(".")
    class_name = klass[path + 1: len(klass)]
    try:
        module = __import__(klass[0:path], globals(), locals(), [class_name])
        klass = getattr(module, class_name)
    except ImportError as e:
        raise ImportError('%s: %s' % (klass, str(e)))
    except AttributeError:
        raise ImportError(klass)
    else:
        return klass


class JediThread(QThread):

    work_done = Signal(object, object)
    finished = Signal()

    def __init__(self):
        super(JediThread, self).__init__()
        self.finish_worker = False
        self.work_list = []
        self.mutex = QMutex()
        self.jedi = JediCompletionProvider()
        self.docworker = DocumentWordsProvider()

        from pyqode.core import backend

        backend.CodeCompletionWorker.providers.append(self.jedi)
        backend.CodeCompletionWorker.providers.append(self.docworker)

    def finish_thread(self):
        self.mutex.lock()
        self.finish_worker = True
        self.mutex.unlock()

    def add_work(self, work, callback):
        self.mutex.lock()
        self.work_list.append([work, callback])
        self.mutex.unlock()

    def run(self):

        while True:
            work = None

            self.mutex.lock()
            if self.finish_worker :
                self.mutex.unlock()
                break

            if len(self.work_list) > 0:
                work = self.work_list.pop(0)
            self.mutex.unlock()

            if work is None:
                time.sleep(1)
            else:
                #print(work[0])
                result = self.handle(work[0])
                #print(result, work[1])
                self.work_done.emit(result, work[1])
        self.finished.emit()

    def handle(self, data):
        """
        Handles a work request.
        """
        import inspect
        try:
            assert data['worker']
            assert data['request_id']
            assert data['data'] is not None
            response = {'request_id': data['request_id'], 'results': []}
            try:
                worker = import_class(data['worker'])
            except ImportError:
                print("Failed...")
            else:
                if inspect.isclass(worker):
                    worker = worker()
                try:
                    ret_val = worker(data['data'])
                except Exception:
                    print("EXCEPTION")
                    ret_val = None

                if ret_val is None:
                    ret_val = []
                response = {'request_id': data['request_id'],
                            'results': ret_val}
                # print("RETURN", ret_val)
                return ret_val
        except:
            print("HERE")
        return None


class QtBackendManager(Manager):
    """
    The backend controller takes care of controlling the client-server
    architecture.

    It is responsible of starting the backend process and the client socket and
    exposes an API to easily control the backend:

        - start
        - stop
        - send_request

    """

    class QObj(QObject):

        stopThread = Signal()
        addWorker = Signal(object, object)

        def work_done(self, results, callback):
            # print(results, callback)

            if callback:
                callback(results)

        def __init__(self):
            super(QtBackendManager.QObj, self).__init__()
            self.jedi_thread = JediThread()

            self.stopThread.connect(self.jedi_thread.finish_thread)
            self.addWorker.connect(self.jedi_thread.add_work)

            self.jedi_thread.work_done.connect(self.work_done)

    def __init__(self, editor):
        super(QtBackendManager, self).__init__(editor)

        self.obj = QtBackendManager.QObj()
        self.obj.jedi_thread.start()

    @staticmethod
    def pick_free_port():
        """ Picks a free port """
        import socket
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.bind(('127.0.0.1', 0))
        free_port = int(test_socket.getsockname()[1])
        test_socket.close()
        return free_port

    def start(self, script, interpreter=sys.executable, args=None,
              error_callback=None, reuse=False):
        print("starting..")
        print("HERE!!")
        #self.obj.jedi_thread.start()

    def stop(self):
        self.obj.stopThread.emit()

    def send_request(self, worker_class_or_function, args, on_receive=None):
        import uuid

        _worker = worker_class_or_function
        _args = args

        # print(_worker, "CALLED")
        # print(_args, "CALLED")
        # print(on_receive, "CALLED")

        if isinstance(_worker, str):
            classname = _worker
        else:
            classname = '%s.%s' % (_worker.__module__,
                                   _worker.__name__)

        request_id = str(uuid.uuid4())

        # emit
        data = {'request_id': request_id, 'worker': classname,
                   'data': _args}

        #print(data)
        #response = self._handle(data)

        #if on_receive :
        #    on_receive(response)

        self.obj.addWorker.emit(data, on_receive)

    def _send_heartbeat(self):
        pass

    def _rm_socket(self, socket):
        pass

    @property
    def running(self):
        """
        Tells whether the backend process is running.

        :return: True if the process is running, otherwise False
        """
        return True

    @property
    def connected(self):
        """
        Checks if the client socket is connected to the backend.

        .. deprecated: Since v2.3, a socket is created per request. Checking
            for global connection status does not make any sense anymore. This
            property now returns ``running``. This will be removed in v2.5
        """
        return True

    @property
    def exit_code(self):
        """
        Returns the backend process exit status or None if the
        process is till running.

        """
        #if self.running:
        #    return None
        #else:
        #    return self._process.exitCode()
        return None


class MyPythonCodeEdit(widgets.PyCodeEditBase):
    def __init__(self):
        super(MyPythonCodeEdit, self).__init__()

        # starts the default pyqode.python server (which enable the jedi code
        # completion worker).
        self._backend = QtBackendManager(self)

        # some other modes/panels require the analyser mode, the best is to
        # install it first
        self.modes.append(modes.OutlineMode(defined_names))

        # --- core panels
        self.panels.append(panels.FoldingPanel())
        self.panels.append(panels.LineNumberPanel())
        self.panels.append(panels.CheckerPanel())
        self.panels.append(panels.SearchAndReplacePanel(),
                           panels.SearchAndReplacePanel.Position.BOTTOM)
        self.panels.append(panels.EncodingPanel(), api.Panel.Position.TOP)
        # add a context menu separator between editor's
        # builtin action and the python specific actions
        self.add_separator()

        # --- python specific panels
        self.panels.append(pypanels.QuickDocPanel(), api.Panel.Position.BOTTOM)

        # --- core modes
        self.modes.append(modes.CaretLineHighlighterMode())
        self.modes.append(modes.CodeCompletionMode())
        self.modes.append(modes.ExtendedSelectionMode())
        self.modes.append(modes.FileWatcherMode())
        self.modes.append(modes.OccurrencesHighlighterMode())
        self.modes.append(modes.RightMarginMode())
        self.modes.append(modes.SmartBackSpaceMode())
        self.modes.append(modes.SymbolMatcherMode())
        self.modes.append(modes.ZoomMode())

        # ---  python specific modes
        self.modes.append(pymodes.CommentsMode())
        self.modes.append(pymodes.CalltipsMode())
        self.modes.append(pymodes.PyFlakesChecker())
        self.modes.append(pymodes.PEP8CheckerMode())
        self.modes.append(pymodes.PyAutoCompleteMode())
        self.modes.append(pymodes.PyAutoIndentMode())
        self.modes.append(pymodes.PyIndenterMode())
        self.modes.append(pymodes.PythonSH(self.document()))
        self.syntax_highlighter.fold_detector = PythonFoldDetector()

