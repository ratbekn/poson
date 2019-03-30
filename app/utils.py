from abc import abstractmethod

from PyQt5.QtCore import QThread


class QThreadRunner(QThread):
    def __init__(self, *, target=None, args=()):
        super(QThreadRunner, self).__init__()

        self.task = target
        self.args = args

    def run(self):
        if self.task:
            self.task(*self.args)


class RunnableMixin:
    @abstractmethod
    def run(self):
        pass

    def __call__(self):
        self.run()
