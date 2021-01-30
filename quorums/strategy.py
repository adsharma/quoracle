from . import distribution
from . import geometry
from .distribution import Distribution
from .expr import Node
from .geometry import Point, Segment
from typing import Dict, Generic, List, Optional, Set, Tuple, TypeVar
import collections
import itertools
import numpy as np


T = TypeVar('T')


class Strategy(Generic[T]):
    def __init__(self,
                 nodes: Set[Node[T]],
                 reads: List[Set[T]],
                 read_weights: List[float],
                 writes: List[Set[T]],
                 write_weights: List[float]) -> None:
        self.nodes = nodes
        self.read_capacity = {node.x: node.read_capacity for node in nodes}
        self.write_capacity = {node.x: node.write_capacity for node in nodes}
        self.reads = reads
        self.read_weights = read_weights
        self.writes = writes
        self.write_weights = write_weights

        self.unweighted_read_load: Dict[T, float] = \
                collections.defaultdict(float)
        for (read_quorum, weight) in zip(self.reads, self.read_weights):
            for x in read_quorum:
                self.unweighted_read_load[x] += weight

        self.unweighted_write_load: Dict[T, float] = \
                collections.defaultdict(float)
        for (write_quorum, weight) in zip(self.writes, self.write_weights):
            for x in write_quorum:
                self.unweighted_write_load[x] += weight

    def __str__(self) -> str:
        non_zero_reads = {tuple(r): p
                          for (r, p) in zip(self.reads, self.read_weights)
                          if p > 0}
        non_zero_writes = {tuple(w): p
                           for (w, p) in zip(self.writes, self.write_weights)
                           if p > 0}
        return f'Strategy(reads={non_zero_reads}, writes={non_zero_writes})'

    def __repr__(self) -> str:
        return (f'Strategy(nodes={self.nodes}, '+
                         f'reads={self.reads}, ' +
                         f'read_weights={self.read_weights},' +
                         f'writes={self.writes}, ' +
                         f'write_weights={self.write_weights})')

    def get_read_quorum(self) -> Set[T]:
        return np.random.choice(self.reads, p=self.read_weights)

    def get_write_quorum(self) -> Set[T]:
        return np.random.choice(self.writes, p=self.write_weights)

    def load(self,
             read_fraction: Optional[Distribution] = None,
             write_fraction: Optional[Distribution] = None) \
             -> float:
        d = distribution.canonicalize_rw(read_fraction, write_fraction)
        return sum(weight * self._load(fr)
                   for (fr, weight) in d.items())

    # TODO(mwhittaker): Rename throughput.
    def capacity(self,
                 read_fraction: Optional[Distribution] = None,
                 write_fraction: Optional[Distribution] = None) \
                 -> float:
        return 1 / self.load(read_fraction, write_fraction)

    def network_load(self,
                     read_fraction: Optional[Distribution] = None,
                     write_fraction: Optional[Distribution] = None) -> float:
        d = distribution.canonicalize_rw(read_fraction, write_fraction)
        fr = sum(weight * f for (f, weight) in d.items())
        read_network_load = fr * sum(
            len(rq) * p
            for (rq, p) in zip(self.reads, self.read_weights)
        )
        write_network_load = (1 - fr) * sum(
            len(wq) * p
            for (wq, p) in zip(self.writes, self.write_weights)
        )
        return read_network_load + write_network_load

    def latency(self,
                read_fraction: Optional[Distribution] = None,
                write_fraction: Optional[Distribution] = None) -> float:
        # TODO(mwhittaker): Implement.
        return 0

    def node_load(self,
                  node: Node[T],
                  read_fraction: Optional[Distribution] = None,
                  write_fraction: Optional[Distribution] = None) \
                  -> float:
        d = distribution.canonicalize_rw(read_fraction, write_fraction)
        return sum(weight * self._node_load(node.x, fr)
                   for (fr, weight) in d.items())

    def node_utilization(self,
                         node: Node[T],
                         read_fraction: Optional[Distribution] = None,
                         write_fraction: Optional[Distribution] = None) \
                         -> float:
        # TODO(mwhittaker): Implement.
        return 0.0

    def node_throghput(self,
                       node: Node[T],
                       read_fraction: Optional[Distribution] = None,
                       write_fraction: Optional[Distribution] = None) \
                       -> float:
        # TODO(mwhittaker): Implement.
        return 0.0

    def _node_load(self, x: T, fr: float) -> float:
        """
        _node_load returns the load on x given a fixed read fraction fr.
        """
        fw = 1 - fr
        return (fr * self.unweighted_read_load[x] / self.read_capacity[x] +
                fw * self.unweighted_write_load[x] / self.write_capacity[x])

    def _load(self, fr: float) -> float:
        """
        _load returns the load given a fixed read fraction fr.
        """
        return max(self._node_load(node.x, fr) for node in self.nodes)
