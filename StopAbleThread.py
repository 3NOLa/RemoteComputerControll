import threading

class StoppableThread(threading.Thread):
    def __init__(self, target, args=(), kwargs=None):
        super().__init__(daemon=True)
        self._stop_flag = True  # Use a boolean flag
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def run(self):
        if self._target:
            self._target(*self._args, **self._kwargs)

    def stop(self):
        self._stop_flag = False

    def should_stop(self):
        return self._stop_flag
