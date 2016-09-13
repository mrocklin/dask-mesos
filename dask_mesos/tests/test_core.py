from dask_mesos import DaskMesosDeployment, DaskMesosScheduler

from time import time

from tornado import gen

from distributed.core import rpc
from distributed.utils_test import gen_cluster


@gen_cluster(client=True, ncores=[], timeout=None)
def test_simple(c, s):
    S = DaskMesosScheduler(scheduler=s, target=2, cpus=1, mem=256,
                           executable='/opt/anaconda/bin/dask-worker')
    DM = DaskMesosDeployment(S)
    DM.start()

    start = time()
    while len(s.ncores) < 2:
        yield gen.sleep(0.1)
        assert time() < start + 10

    assert S.acknowledged == S.submitted

    yield gen.sleep(0.2)
    assert len(s.ncores) == 2  # still 2 after some time

    # Test propagation of cpu/mem values
    assert all(v == 1 for v in s.ncores.values())

    def memory(dask_worker=None):
        return dask_worker.data.fast.n  # total number of available bytes

    results = yield c._run(memory)
    assert all(100 < v < 256 for v in results.values())
