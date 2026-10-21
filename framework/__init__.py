"""Closed-loop Ti-alloy design framework, v2 (Stage-8 compatible).
sqs_mlip is imported lazily (pulls ASE/CHGNet) - import it explicitly when needed."""
from . import config as C
from . import composition, physics, strength, pareto