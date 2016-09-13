from dask_mesos import FixedScheduler

import sys
from time import time

from tornado import gen

from distributed.core import rpc
from distributed.utils_test import gen_cluster


@gen_cluster(client=True, ncores=[], timeout=None)
def test_simple(c, s):
    S = FixedScheduler(s, target=2, cpus=1, mem=256,
                       executable='/opt/anaconda/bin/dask-worker')
    S.start()

    start = time()
    while len(s.ncores) < 2:
        yield gen.sleep(0.1)
        assert time() < start + 10

    assert not S.submitted
    assert len(S.running) == len(s.ncores)

    yield gen.sleep(0.2)
    assert len(s.ncores) == 2  # still 2 after some time

    # Test propagation of cpu/mem values
    assert all(v == 1 for v in s.ncores.values())

    def memory(dask_worker=None):
        return dask_worker.data.fast.n  # total number of available bytes

    results = yield c._run(memory)
    assert all(100 < v < 256 for v in results.values())


@gen_cluster(client=True, ncores=[], timeout=None)
def test_redeploy(c, s):
    S = FixedScheduler(s, target=2, cpus=1, mem=256,
                       executable='/opt/anaconda/bin/dask-worker')
    S.start()

    start = time()
    while len(s.ncores) < 2:
        yield gen.sleep(0.1)
        assert time() < start + 5

    yield c._run(sys.exit, nanny=True)

    start = time()
    while not len(S.finished) == 2:
        yield gen.sleep(0.1)
        assert time() < start + 5

    start = time()
    while len(s.ncores) < 2:
        yield gen.sleep(0.1)
        assert time() < start + 5
