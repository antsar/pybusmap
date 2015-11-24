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

    def __init__(cls, key, shared=False, expires=25, timeout=30, step=0.5):
        """
        A lock mechanism, using Redis as a backend.

        key = identifier for this lock
        expires = lock expiration time in seconds (when it is considered stale)
        timeout = max time to wait for a lock to become available

        Multiple shared locks can exist simultaneously.
        Only one non-shared (exclusive) lock can exist at a time.
        Shared locks wait for exclusive locks to release.
        If an exclusive lock is set, new shared lock attempts will wait (block).
        Similarly, exclusive locks will wait (block) until all shared locks to clear.
        """

        cls.exclusive_key = "bm-lock-x-{0}".format(key)
        cls.shared_key = "bm-lock-s-{0}".format(key)
        cls.shared = shared
        cls.expires = expires
        cls.timeout = timeout
        cls.step = step
        cls.pid = os.getpid()


    def __enter__(cls):
        """
        Attempt to acquire the lock.
        If the lock is unavailable, retry for `timeout` seconds.
        If a stale lock is found (older than `expires`), remove it.
        """
        while cls.timeout >= 0:
            cls.expires = time() + cls.expires + 1
            if cls.shared:
                # Make sure nobody has exclusive, but don't take it.
                if not r.get(cls.exclusive_key):
                    # Nobody has exclusive. Get our shared lock
                    cls._set_shared()
                    return
            else:
                # We're getting an exclusive lock. Set it.
                if cls._set_exclusive():
                    # Some shared locks may still exist. Wait for them to release.
                    cls._wait_for_shared()
                    return
            # Lock not aquired! Check for stale exclusive lock
            oldlock = r.get(cls.exclusive_key)
            (existing_expires, existing_pid) = pickle.loads(oldlock)
            if existing_expires and float(existing_expires) < time():
                # Stale Exc Lock found. Delete it.
                r.delete(cls.exclusive_key)
            # Tick and repeat until timeout.
            if existing_expires:
                remaining = existing_expires - time()
            cls.timeout -= cls.step
            sleep(cls.step)
        # Timed out
        raise(LockException("Could not acquire lock: {0}".format(cls.exclusive_key)))

    def __exit__(cls, typ, value, traceback):
        """
        Release the lock.
        """
        if cls.shared:
            r.lrem(cls.shared_key, 0, pickle.dumps((cls.expires, cls.pid)))
        else:
            r.delete(cls.exclusive_key)

    def _set_shared(cls):
        """
        Set a shared lock
        """
        return r.lpush(cls.shared_key, pickle.dumps((cls.expires, cls.pid)))

    def _set_exclusive(cls):
        """
        Set an exclusive lock
        """
        return r.setnx(cls.exclusive_key, pickle.dumps((cls.expires,cls.pid)))

    def _wait_for_shared(cls):
        while r.llen(cls.shared_key) > 0 and cls.timeout >= 0:
            for sk in r.lrange(cls.shared_key, 0, -1):
                (cls.expires, cls.pid) = pickle.loads(sk)
                if float(cls.expires) < time():
                    r.lrem(cls.shared_key, 0, pickle.dumps((cls.expires, cls.pid)))
                cls.timeout -= cls.step
                sleep(cls.step)
        if r.llen(cls.shared_key) == 0:
            return
        else:
            raise(LockException("Shared locks still present: {0}".format(cls.shared_key)))

class LockException(Exception):
    pass
