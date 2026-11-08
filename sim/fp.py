"""Re-export arithmetic classes from the two frozen network implementations."""

from _verified.independent_constant_norm import Fixed as UnitFixed
from _verified.independent_variance import Fixed as VarianceFixed

__all__ = ["UnitFixed", "VarianceFixed"]
