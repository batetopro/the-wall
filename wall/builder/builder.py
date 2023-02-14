import logging
import os
import threading


from wall import settings


LOGGER = logging.getLogger(__name__)


class History:
    """
    Represents the build history.
    """

    profiles = {}

    @staticmethod
    def build() -> None:
        """
        Build the history.
        :return: None
        """

        LOGGER.info("Building history ...")
        if settings.IS_MULTI_THREADED:
            builder = MultiThreadedHistoryBuilder()
            logging.info("Building the walls with MultiThreadedHistoryBuilder ...")
        else:
            builder = SimpleHistoryBuilder()
            logging.info("Building the walls with SimpleHistoryBuilder ...")
        data = builder.read_data()
        builder.build(data)

    @staticmethod
    def amount_per_profile_per_day(profile, day) -> int:
        """
        How much ice was added to a profile on a given day.

        :param profile: int
        :param day: int
        :return: int
        """

        if profile not in History.profiles:
            return 0
        if day not in History.profiles[profile]:
            return 0
        return History.profiles[profile][day] * settings.FOOT_VOLUME

    @staticmethod
    def price_per_profile_per_day(profile, day) -> int:
        """
        How much did the build of a profile costed on a given day.

        :param profile: int
        :param day: int
        :return: int
        """
        if profile not in History.profiles:
            return 0
        if day not in History.profiles[profile]:
            return 0
        return History.profiles[profile][day] * settings.FOOT_VOLUME * settings.VOLUME_PRICE

    @staticmethod
    def price_per_day(day) -> int:
        """
        How much the build of all profiles costed om a given day.
        :param day: int
        :return: int
        """

        total = 0
        for history in History.profiles.values():
            if day not in history:
                continue
            total += history[day]
        return total * settings.FOOT_VOLUME * settings.VOLUME_PRICE

    @staticmethod
    def overall() -> int:
        """
        How much cost the build of all profiles.
        :return: int
        """

        total = 0
        for history in History.profiles.values():
            for day, amount in history.items():
                total += amount
        return total * settings.FOOT_VOLUME * settings.VOLUME_PRICE


class HistoryBuilder:
    """
    Abstract builder of History.profiles
    """

    @classmethod
    def read_data(cls, path=None) -> dict:
        """
        Read the initial profiles from a file.

        :param path: str
        :return: dict
        """

        if path is None:
            path = settings.WALL_FILE

        LOGGER.info("Reading wall profiles from '{}' ...".format(path))
        if not os.path.exists(path):
            raise FileNotFoundError("Initial walls from '{}' can not be found.".format(path))

        data = {}
        counter = 1
        with open(path, "r") as fp:
            line = fp.readline().strip()
            while line:
                sections = line.split()
                data[counter] = [int(s) for s in sections]
                line = fp.readline().strip()
                counter += 1

        LOGGER.info("The are {} wall profiles.".format(counter - 1))

        return data

    def __init__(self):
        self._day = 1
        self._partitions = []

    @property
    def day(self) -> int:
        """
        Get the current day
        :return: int
        """
        return self._day

    def is_ready(self) -> bool:
        """
        Is the builder ready.
        :return: bool
        """
        raise NotImplementedError()


    def build_profile(self, profile, day) -> None:
        """
        Increase the History.profiles of a given profile and given day

        :param profile: int
        :param day: int
        :return: None
        """
        if profile not in History.profiles:
            History.profiles[profile] = {}
        if day not in History.profiles[profile]:
            History.profiles[profile][day] = 0
        History.profiles[profile][day] += 1

    def build(self, data) -> None:
        """
        Build History.profiles
        :param data: dict
        :return: None
        """
        raise NotImplementedError()

    def _make_partitions(self, data) -> None:
        """
        Prepare the partitions of the builder.
        :param data: dict
        :return: None
        """

        LOGGER.info("Preparing partitions ...")
        self._partitions = []
        for profile, sections in data.items():
            for idx, section in enumerate(sections):
                self._partitions.append({
                    "profile": profile,
                    "section": idx + 1,
                    "height": section,
                })
        LOGGER.info("Partitions ready.")


class SimpleHistoryBuilder(HistoryBuilder):
    """
    Builder of History.profiles, which builds all profiles at once oer day.
    """

    def __init__(self):
        super().__init__()
        self._amount_added = 0

    def is_ready(self) -> bool:
        """
        Get ready when there is no amount added.
        :return: bool
        """
        return self._amount_added == 0

    def build(self, data) -> None:
        """
        Build History.profiles
        :param data: dict
        :return: None
        """
        History.profiles = {}
        self._day = 1
        self._make_partitions(data)

        while True:
            self._amount_added = 0
            for partition in self._partitions:
                if partition["height"] >= settings.WALL_HEIGHT:
                    continue

                partition["height"] += 1
                self._amount_added += 1
                self.build_profile(partition["profile"], self.day)

            if self.is_ready():
                LOGGER.info("Ready. Wall was build in {} days.".format(self.day))
                break

            LOGGER.info("On day {} the wall workers extended {} sections.".format(self.day, self._amount_added))
            self._day += 1


class MultiThreadedHistoryBuilder(HistoryBuilder):
    """
    Builder of History.profiles, which uses workers to build profiles.
    """
    def _prepare_locks(self, data) -> None:
        """
        Prepare History.profiles locks.
        :param data: dict
        :return: None
        """
        self._profile_locks = {}
        for profile in data:
            self._profile_locks[profile] = threading.Lock()

    def __init__(self):
        super().__init__()
        self._profile_locks = {}
        self._schedule = {}
        self._barrier = None

    @property
    def profile_locks(self) -> dict:
        """
        Get the locks of builder.
        :return: dict
        """
        return self._profile_locks

    @property
    def schedule(self) -> dict:
        """
        Get the schedule - the partitions on which the workers are building
        :return: dict | None
        """
        return self._schedule

    @property
    def active_workers(self) -> int:
        """
        Get the count of active workers
        :return: int
        """
        result = 0
        for partition in self._schedule.values():
            if partition is not None:
                result += 1
        return result

    @property
    def barrier(self) -> threading.Barrier:
        """
        Get the barrier on which the workers are awaiting the day to end.
        :return: threading.Barrier
        """
        return self._barrier

    def is_ready(self) -> int:
        """
        Get ready when there are no active workers
        :return: int
        """
        return self.active_workers == 0

    def get_next_partition(self) -> dict:
        """
        Get the next partition to be added on worker's schedule.
        :return: dict | None
        """
        try:
            return self._partitions.pop(0)
        except IndexError:
            return None

    def build(self, data) -> None:
        """
        Build History.profiles
        :param data: dict
        :return: None
        """
        History.profiles = {}
        self._make_partitions(data)
        self._prepare_locks(data)
        self._day = 1
        self._schedule = {}

        for idx in range(1, settings.THREADS_NUMBER + 1):
            self.schedule[idx] = self.get_next_partition()
            if self.schedule[idx] is None:
                LOGGER.info("Build worker {} is ready.".format(idx))

        while not self.is_ready():
            for idx in range(1,  settings.THREADS_NUMBER + 1):
                if self.schedule[idx] and self.schedule[idx]["height"] >= settings.WALL_HEIGHT:
                    self.schedule[idx] = self.get_next_partition()
                    if self.schedule[idx] is None:
                        LOGGER.info("Build worker {} is ready.".format(idx))
                    else:
                        LOGGER.info("Build worker {} moves to profile {}, section {}.".format(
                            idx, self.schedule[idx]["profile"], self.schedule[idx]["section"]))

            self._barrier = threading.Barrier(self.active_workers + 1)
            for idx in range(1,  settings.THREADS_NUMBER + 1):
                if self.schedule[idx] is None:
                    continue

                w = BuilderThread(idx, self)
                w.start()

            self._barrier.wait()
            self._day += 1


class BuilderThread(threading.Thread):
    """
    Workers of MultiThreadedHistoryBuilder - build one profile section.
    """
    @property
    def idx(self) -> int:
        """
        Get the index of the worker.
        :return: int
        """
        return self._idx

    @property
    def builder(self) -> MultiThreadedHistoryBuilder:
        """
        Get the builder of the worker.
        :return: MultiThreadedHistoryBuilder
        """
        return self._builder

    def __init__(self, idx, builder):
        super().__init__()
        self._builder = builder
        self._idx = idx

    def run(self) -> None:
        """
        Run a worker for a given day, if the worker has partition assigned.
        :return: None
        """
        partition = self.builder.schedule[self.idx]
        partition["height"] += 1

        LOGGER.info("On day {} build worker {} extended section {} of profile {} to {} feet.".format(
            self.builder.day, self.idx, partition["section"], partition["profile"], partition["height"]
        ))

        with self.builder.profile_locks[partition["profile"]]:
            self.builder.build_profile(partition["profile"], self.builder.day)

        self.builder.barrier.wait()
