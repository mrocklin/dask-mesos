
from collections import deque
import logging
import time
from threading import Thread
import uuid

from mesos.interface import Scheduler
from mesos.native import MesosSchedulerDriver
from mesos.interface import mesos_pb2

logger = logging.getLogger(__file__)
logging.basicConfig(format='%(levelname)s - %(message)s',
                    level=logging.DEBUG)


class DaskMesosDeployment(object):
    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.framework = mesos_pb2.FrameworkInfo()
        self.framework.user = ""
        self.framework.name = "dask-scheduler"
        self.driver = MesosSchedulerDriver(self.scheduler, self.framework,
                "zk://localhost:2181/mesos")  # assumes running on the master
        self._driver_thread = None

    def start(self):
        if self._driver_thread:
            return
        self._driver_thread = Thread(target=self.driver.run)
        self._driver_thread.daemon = True
        self._driver_thread.start()


class DaskMesosScheduler(Scheduler):
    def __init__(self, scheduler, target=0, cpus=1, mem=4096, disk=None,
                 executable='dask-worker'):
        self.target = target
        self.scheduler = scheduler
        self.cpus = cpus
        self.mem = mem
        self.disk = disk or mem * 10
        self.worker_executable = executable
        self.status_messages = deque(maxlen=10000)
        self.recent_offers = deque(maxlen=100)
        self.submitted = set()
        self.acknowledged = set()

    def registered(self, driver, framework_id, master_info):
        logger.info("Registered with framework id: {}".format(framework_id))
        logger.debug("Registered with frameowrk, %s, %s", framework_id,
                master_info)

    def reregistered(self, driver, master_info):
        logger.debug("Reregistered with frameowrk, %s", master_info)

    def disconnected(self, driver):
        logger.debug("Disconnected")

    def parse_offer(self, offer):
        r = {r.name: r.scalar.value for r in offer.resources}
        r['hostname'] = offer.hostname
        return r

    def active_workers(self):
        return len(self.scheduler.ncores) + len(self.submitted - self.acknowledged)

    def resourceOffers(self, driver, offers):
        self.recent_offers.extend(offers)
        logger.debug("Received offers: %s", offers)

        if self.active_workers() >= self.target:
            logger.debug("Saturated.  ncores: %d, submitted %d, ack: %d",
                    len(self.scheduler.ncores), len(self.submitted),
                    len(self.acknowledged))
            return


        for offer in offers:
            o = self.parse_offer(offer)
            cpus = o.get('cpus', 0)
            mem = o.get('mem', 0)
            disk = o.get('disk', 0)

            logger.info("Considering offer %s", o)

            tasks = []

            while (cpus >= self.cpus and
                   mem >= self.mem and
                   disk >= self.disk and
                   self.active_workers() < self.target):

                task = self.task_info(offer)

                cpus -= self.cpus
                mem -= self.mem
                disk -= self.disk

                options = {'--nthreads': self.cpus,
                           '--memory-limit': int(self.mem * 0.7)}
                command = '%s %s ' % (self.worker_executable, self.scheduler.address)
                command += ' '.join(' '.join(map(str, item)) for item in options.items())

                task.command.value = command
                self.submitted.add(task.task_id.value)
                tasks.append(task)

            driver.launchTasks(offer.id, tasks)
            logger.info("Launch tasks %s with offer %s",
                        [t.task_id.value for t in tasks], offer.id.value)
            logger.debug("Launching tasks %s", tasks)

    def task_info(self, offer):
        task = mesos_pb2.TaskInfo()
        id = str(uuid.uuid4())
        task.task_id.value = id
        task.slave_id.value = offer.slave_id.value
        task.name = "dask-worker-%s" % id

        cpus = task.resources.add()
        cpus.name = "cpus"
        cpus.type = mesos_pb2.Value.SCALAR
        cpus.scalar.value = self.cpus

        mem = task.resources.add()
        mem.name = "mem"
        mem.type = mesos_pb2.Value.SCALAR
        mem.scalar.value = self.mem

        mem = task.resources.add()
        mem.name = "disk"
        mem.type = mesos_pb2.Value.SCALAR
        mem.scalar.value = self.disk

        return task

    def offerRescinded(self, driver, offerId):
        logger.debug("Offer rescinded: %s", offerId)

    def frameworkMessage(self, driver, executorId, slaveId, message):
        logger.debug("Framework message.  executorId: %s, slaveId: %s, message: %s", executorId, slaveId, message)

    def slaveLost(self, driver, slaveId):
        logger.debug("Slave lost: %s", slaveId)

    def executorLost(self, driver, executorId, slaveId, status):
        logger.debug("Executor lost: executorId: %s, slaveId: %s, status: %s", executorId, slaveId, status)

    def error(self, driver, message):
        logger.info("error: %s", message)

    def statusUpdate(self, driver, status):
        logger.debug("Status update: %s", status)

        if status.state == 1:  # TASK_RUNNING
            self.acknowledged.add(status.task_id.value)

        self.status_messages.append(status)
