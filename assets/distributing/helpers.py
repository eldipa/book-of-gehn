
import threading
import queue

def sync_req_resp_loop(func, request_q, response_q):
    ''' Classic request-response synchronous loop. '''
    t = request_q.get()
    while t is not None:
        r = func(t)
        response_q.put(r)

    response_q.put(None)

class Channel:
    def __init__(self, q1, q2):
        self.q1 = q1
        self.q2 = q2

    def send(self, x, *args, **kargs):
        self.q1.put(x)

    def recv(self, *args, **kargs):
        return self.q2.get(*args, **kargs)

def socket_pair(*args, **kargs):
    q1 = queue.Queue(*args, **kargs)
    q2 = queue.Queue(*args, **kargs)

    ch1 = Channel(q1, q2)
    ch2 = Channel(q2, q1)

    return ch1, ch2

_threads = {}
def in_thread(th_model, args):
    ''' Return a decorator to wrap a function that will be
        executed under the thread model <th_model> (thread model).
        The thread model can be configured with <args>.
        '''
    def decorator(func):
        fname = func.__name__
        assert fname not in _threads

        eargs = (func,) + args
        _threads[fname] = threading.Thread(
                target=th_model,
                args=eargs,
                name=fname
                )
        _threads[fname].start()
        return _threads[fname]
    return decorator

def bg(func):
    ''' Decorate a function that will be executed in background.
        '''
    fname = func.__name__
    assert fname not in _threads

    _threads[fname] = threading.Thread(
            target=func,
            name=fname
            )
    _threads[fname].start()
    return _threads[fname]

def req_resp_worker(request_q, response_q):
    ''' Return a decorator to wrap a function under the
        'request and response loop' thread model.
        It will call the wrapped function for each request
        received returning each response.
        The model is synchronous: one request, one response and loop.
        '''
    return in_thread(
            sync_req_resp_loop,
            (request_q, response_q)
            )
