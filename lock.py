import redis
import pickle
import os
from time import sleep, time
from random import random

r = redis.StrictRedis()

class Lock():
    """
    A way to prevent things from happening concurrently.
    Synchronization is bad! Use at your own risk.
    """

    def __init__(self, key, shared=False, expires=25, timeout=30, step=0.5):
        """
        Redis lock.
        key = name of the lock
        expires = lock expiration time in seconds. in case of failed jobs.
        timeout = max time to wait for a lock
        """

        self.exclusive_key = "bm-lock-x-{0}".format(key)
        self.shared_key = "bm-lock-s-{0}".format(key)
        self.shared = shared
        self.expires = expires
        self.timeout = timeout
        self.step = step
        self.pid = os.getpid()


    def __enter__(self):
        while self.timeout >= 0:
            self.expires = time() + self.expires + 1
            if self.shared == False:
                # We're getting an exclusive lock
                if r.setnx(self.exclusive_key, pickle.dumps((self.expires,self.pid))):
                    # Wait for all shared locks to clear, then proceed
                    self._wait_for_shared()
                    return
            else:
                # Make sure nobody has exclusive, but don't take it.
                if not r.get(self.exclusive_key):
                    # Nobody has exclusive. Get our shared lock
                    self._get_shared()
                    return
            # Lock not aquired! Check for stale exclusive lock
            oldlock = r.get(self.exclusive_key)
            (existing_expires, existing_pid) = pickle.loads(oldlock)
            if existing_expires and float(existing_expires) < time():
                # Stale Exc Lock found. Delete it.
                r.delete(self.exclusive_key)
            # Tick and repeat until timeout.
            if existing_expires:
                remaining = existing_expires - time()
            self.timeout -= self.step
            sleep(self.step)
        # Timed out
        raise(LockException("Could not acquire lock: {0}".format(self.exclusive_key)))

    def __exit__(self, typ, value, traceback):
        if self.shared:
            r.lrem(self.shared_key, 0, pickle.dumps((self.expires, self.pid)))
        else:
            r.delete(self.exclusive_key)

    def _get_shared(self):
        r.lpush(self.shared_key, pickle.dumps((self.expires, self.pid)))

    def _wait_for_shared(self):
        while r.llen(self.shared_key) > 0 and self.timeout >= 0:
            for sk in r.lrange(self.shared_key, 0, -1):
                (self.expires, self.pid) = pickle.loads(sk)
                if float(self.expires) < time():
                    r.lrem(self.shared_key, 0, pickle.dumps((self.expires, self.pid)))
                self.timeout -= self.step
                sleep(self.step)
        if r.llen(self.shared_key) == 0:
            return
        else:
            raise(LockException("Shared locks still present: {0}".format(self.shared_key)))

class LockException(Exception):
    pass
