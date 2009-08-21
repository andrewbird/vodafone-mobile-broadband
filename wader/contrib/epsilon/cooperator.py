
import time

from twisted.internet import reactor, defer

class _Timer:
    MAX_SLICE = 0.01
    def __init__(self):
        self.end = time.time() + self.MAX_SLICE

    def __call__(self):
        return time.time() >= self.end

_EPSILON = 0.00000001
def _defaultScheduler(x):
    return reactor.callLater(_EPSILON, x)

class Cooperator(object):
    """
    I am a task scheduler for cooperative tasks.
    """

    def __init__(self,
                 terminationPredicateFactory=_Timer,
                 scheduler=_defaultScheduler,
                 started=True):
        self.iterators = []
        self._metarator = iter(())
        self._terminationPredicateFactory = terminationPredicateFactory
        self._scheduler = scheduler
        self._delayedCall = None
        self._stopped = False
        self._started = started

    def coiterate(self, iterator, doneDeferred=None):
        """Add an iterator to the list of iterators I am currently running.

        @return: a Deferred that will fire when the iterator finishes.
        """
        if doneDeferred is None:
            doneDeferred = defer.Deferred()
        if self._stopped:
            doneDeferred.errback(SchedulerStopped())
            return doneDeferred
        self.iterators.append((iterator, doneDeferred))
        self._reschedule()
        return doneDeferred

    def _tasks(self):
        terminator = self._terminationPredicateFactory()
        while self.iterators:
            for i in self._metarator:
                yield i
                if terminator():
                    return
            self._metarator = iter(self.iterators)

    def _tick(self):
        """Run one scheduler tick.
        """
        self._delayedCall = None
        for taskObj in self._tasks():
            iterator, doneDeferred = taskObj
            try:
                result = iterator.next()
            except StopIteration:
                self.iterators.remove(taskObj)
                doneDeferred.callback(iterator)
            except:
                self.iterators.remove(taskObj)
                doneDeferred.errback()
            else:
                if isinstance(result, defer.Deferred):
                    self.iterators.remove(taskObj)
                    result.addCallbacks(
                        lambda whatever, pythonShouldHaveClosures=taskObj:
                        self.coiterate(*pythonShouldHaveClosures) and None,
                        lambda anError, noSeriouslyIMeanIt=doneDeferred.errback:
                        noSeriouslyIMeanIt(anError))
        self._reschedule()

    _mustScheduleOnStart = False
    def _reschedule(self):
        if not self._started:
            self._mustScheduleOnStart = True
            return
        if self._delayedCall is None and self.iterators:
            self._delayedCall = self._scheduler(self._tick)

    def start(self):
        self._stopped = False
        self._started = True
        if self._mustScheduleOnStart:
            del self._mustScheduleOnStart
            self._reschedule()

    def stop(self):
        self._stopped = True
        for iterator, doneDeferred in self.iterators:
            doneDeferred.errback(SchedulerStopped())
        self.iterators = []
        if self._delayedCall is not None:
            self._delayedCall.cancel()
            self._delayedCall = None

class SchedulerStopped(Exception):
    """The operation could not complete because the scheduler was stopped in
    progress or was already stopped.
    """

_theCooperator = Cooperator()

def iterateInReactor(i, delay=None):
    return _theCooperator.coiterate(i)

from twisted.application.service import Service

class SchedulingService(Service):
    """
    Simple L{IService} implementation.
    """
    def __init__(self):
        self.coop = Cooperator(started=False)

    def addIterator(self, iterator):
        return self.coop.coiterate(iterator)

    def startService(self):
        self.coop.start()

    def stopService(self):
        self.coop.stop()
