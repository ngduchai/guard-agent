"""
comparator.py – Pluggable output comparison for the VeloC validation framework.

Built-in strategies
-------------------
  HashComparator             – SHA-256 byte-identical comparison
  SSIMComparator             – Structural Similarity Index on HDF5 datasets
  NumericToleranceComparator – element-wise comparison with atol/rtol
  TextDiffComparator         – line-by-line text diff

Extension point
---------------
  CustomPluginComparator     – loads a user-supplied Python file that exports
                               compare(baseline_path, resilient_path, **kwargs)

Factory
-------
  make_comparator(method, plugin_path, **kwargs) -> BaseComparator

Plugin contract
---------------
The plugin file must export a top-level function::

    def compare(baseline_path: str, resilient_path: str, **kwargs) -> dict:
        '''
        Returns a dict with keys:
          passed  : bool
          score   : float | None
          message : str
          details : dict
        '''
"""

from __future__ import annotations

import difflib
import hashlib
import importlib.util
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class CompareResult:
    """Result of a single output comparison."""
    passed: bool
    method: str
    score: float | None = None      # SSIM value, max-abs-diff, etc. (None for hash)
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        score_str = f", score={self.score:.6g}" if self.score is not None else ""
        return f"[{status}] {self.method}{score_str}: {self.message}"


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseComparator(ABC):
    """Abstract base class for all output comparators."""

    @abstractmethod
    def compare(self, baseline_path: Path, resilient_path: Path) -> CompareResult:
        """Compare *baseline_path* against *resilient_path* and return a result."""
        ...

    def _check_files_exist(
        self, baseline_path: Path, resilient_path: Path
    ) -> CompareResult | None:
        """Return a failing CompareResult if either file is missing, else None."""
        missing = []
        if not baseline_path.exists():
            missing.append(str(baseline_path))
        if not resilient_path.exists():
            missing.append(str(resilient_path))
        if missing:
            return CompareResult(
                passed=False,
                method=self.__class__.__name__,
                message=f"File(s) not found: {', '.join(missing)}",
            )
        return None


# ---------------------------------------------------------------------------
# Hash comparator
# ---------------------------------------------------------------------------

class HashComparator(BaseComparator):
    """SHA-256 byte-identical comparison."""

    def compare(self, baseline_path: Path, resilient_path: Path) -> CompareResult:
        err = self._check_files_exist(baseline_path, resilient_path)
        if err:
            return err

        h_base = self._sha256(baseline_path)
        h_res = self._sha256(resilient_path)
        passed = h_base == h_res
        return CompareResult(
            passed=passed,
            method="hash",
            message=(
                "outputs are byte-identical"
                if passed
                else f"SHA-256 mismatch: baseline={h_base[:16]}… resilient={h_res[:16]}…"
            ),
            details={"baseline_sha256": h_base, "resilient_sha256": h_res},
        )

    @staticmethod
    def _sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()


# ---------------------------------------------------------------------------
# SSIM comparator
# ---------------------------------------------------------------------------

class SSIMComparator(BaseComparator):
    """Structural Similarity Index on an HDF5 dataset.

    Requires ``h5py`` and ``scikit-image``.
    """

    def __init__(self, dataset: str = "data", threshold: float = 0.9999) -> None:
        self.dataset = dataset
        self.threshold = threshold

    def compare(self, baseline_path: Path, resilient_path: Path) -> CompareResult:
        err = self._check_files_exist(baseline_path, resilient_path)
        if err:
            return err

        try:
            import h5py  # noqa: F401
        except ImportError:
            return CompareResult(
                passed=False,
                method="ssim",
                message="h5py is required for SSIM comparison. Install with: pip install h5py",
            )
        try:
            from skimage.metrics import structural_similarity  # noqa: F401
        except ImportError:
            return CompareResult(
                passed=False,
                method="ssim",
                message=(
                    "scikit-image is required for SSIM comparison. "
                    "Install with: pip install scikit-image"
                ),
            )

        try:
            arr1 = self._load_hdf5(baseline_path, self.dataset)
            arr2 = self._load_hdf5(resilient_path, self.dataset)
        except (KeyError, OSError) as exc:
            return CompareResult(
                passed=False, method="ssim", message=f"HDF5 load error: {exc}"
            )

        if arr1.shape != arr2.shape:
            return CompareResult(
                passed=False,
                method="ssim",
                message=f"Shape mismatch: baseline={arr1.shape}, resilient={arr2.shape}",
            )

        ssim_value = self._compute_ssim(arr1, arr2)
        passed = ssim_value >= self.threshold
        return CompareResult(
            passed=passed,
            method="ssim",
            score=ssim_value,
            message=(
                f"SSIM={ssim_value:.6f} >= threshold={self.threshold}"
                if passed
                else f"SSIM={ssim_value:.6f} < threshold={self.threshold}"
            ),
            details={
                "ssim": ssim_value,
                "threshold": self.threshold,
                "dataset": self.dataset,
            },
        )

    @staticmethod
    def _load_hdf5(path: Path, dataset: str):
        import h5py
        with h5py.File(path, "r") as f:
            if dataset not in f:
                available = list(f.keys())
                raise KeyError(
                    f"Dataset {dataset!r} not found in {path}. Available: {available}"
                )
            return f[dataset][...]

    @staticmethod
    def _compute_ssim(arr1, arr2) -> float:
        from skimage.metrics import structural_similarity
        data_range = max(
            float(arr1.max() - arr1.min()),
            float(arr2.max() - arr2.min()),
            1.0,
        )
        min_extent = min(arr1.shape)
        win_size = min(7, min_extent)
        if win_size % 2 == 0:
            win_size = max(1, win_size - 1)
        result = structural_similarity(
            arr1, arr2, data_range=data_range, channel_axis=None, win_size=win_size
        )
        value = result[0] if isinstance(result, tuple) else result
        return float(value)


# ---------------------------------------------------------------------------
# Numeric tolerance comparator
# ---------------------------------------------------------------------------

class NumericToleranceComparator(BaseComparator):
    """Element-wise comparison with absolute and relative tolerance.

    Supports HDF5 files (requires ``h5py`` and ``numpy``) and NumPy ``.npy``
    files.  The *dataset* parameter selects the HDF5 dataset name; it is
    ignored for ``.npy`` files.
    """

    def __init__(
        self,
        dataset: str = "data",
        atol: float = 1e-6,
        rtol: float = 1e-6,
    ) -> None:
        self.dataset = dataset
        self.atol = atol
        self.rtol = rtol

    def compare(self, baseline_path: Path, resilient_path: Path) -> CompareResult:
        err = self._check_files_exist(baseline_path, resilient_path)
        if err:
            return err

        try:
            import numpy as np
        except ImportError:
            return CompareResult(
                passed=False,
                method="numeric-tolerance",
                message="numpy is required. Install with: pip install numpy",
            )

        try:
            arr1 = self._load(baseline_path, np)
            arr2 = self._load(resilient_path, np)
        except Exception as exc:
            return CompareResult(
                passed=False, method="numeric-tolerance", message=f"Load error: {exc}"
            )

        if arr1.shape != arr2.shape:
            return CompareResult(
                passed=False,
                method="numeric-tolerance",
                message=f"Shape mismatch: baseline={arr1.shape}, resilient={arr2.shape}",
            )

        abs_diff = np.abs(arr1.astype(float) - arr2.astype(float))
        max_abs_diff = float(abs_diff.max())
        max_rel_diff = float(
            (abs_diff / (np.abs(arr1.astype(float)) + 1e-300)).max()
        )
        passed = bool(np.allclose(arr1, arr2, atol=self.atol, rtol=self.rtol))

        return CompareResult(
            passed=passed,
            method="numeric-tolerance",
            score=max_abs_diff,
            message=(
                f"max_abs_diff={max_abs_diff:.3e}, max_rel_diff={max_rel_diff:.3e} "
                f"(atol={self.atol:.3e}, rtol={self.rtol:.3e})"
            ),
            details={
                "max_abs_diff": max_abs_diff,
                "max_rel_diff": max_rel_diff,
                "atol": self.atol,
                "rtol": self.rtol,
                "dataset": self.dataset,
            },
        )

    def _load(self, path: Path, np):
        if path.suffix in {".npy", ".npz"}:
            return np.load(path)
        # Assume HDF5
        try:
            import h5py
        except ImportError:
            raise RuntimeError(
                "h5py is required for HDF5 numeric comparison. "
                "Install with: pip install h5py"
            )
        with h5py.File(path, "r") as f:
            if self.dataset not in f:
                available = list(f.keys())
                raise KeyError(
                    f"Dataset {self.dataset!r} not found in {path}. "
                    f"Available: {available}"
                )
            return f[self.dataset][...]


# ---------------------------------------------------------------------------
# Text diff comparator
# ---------------------------------------------------------------------------

class TextDiffComparator(BaseComparator):
    """Line-by-line text diff.

    Suitable for comparing stdout/log files.  Lines matching any pattern in
    *ignore_patterns* (substring match) are excluded before comparison.
    """

    def __init__(self, ignore_patterns: list[str] | None = None) -> None:
        self.ignore_patterns = ignore_patterns or []

    def compare(self, baseline_path: Path, resilient_path: Path) -> CompareResult:
        err = self._check_files_exist(baseline_path, resilient_path)
        if err:
            return err

        lines1 = self._filtered_lines(baseline_path)
        lines2 = self._filtered_lines(resilient_path)

        diff = list(
            difflib.unified_diff(
                lines1, lines2,
                fromfile=str(baseline_path),
                tofile=str(resilient_path),
                lineterm="",
            )
        )
        passed = len(diff) == 0
        return CompareResult(
            passed=passed,
            method="text-diff",
            message="outputs are identical" if passed else f"{len(diff)} diff lines",
            details={"diff_lines": diff[:200]},  # cap at 200 lines in details
        )

    def _filtered_lines(self, path: Path) -> list[str]:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if not self.ignore_patterns:
            return lines
        return [
            ln for ln in lines
            if not any(pat in ln for pat in self.ignore_patterns)
        ]


# ---------------------------------------------------------------------------
# Custom plugin comparator
# ---------------------------------------------------------------------------

class CustomPluginComparator(BaseComparator):
    """Load a user-supplied Python file and call its ``compare()`` function.

    The plugin must export::

        def compare(baseline_path: str, resilient_path: str, **kwargs) -> dict:
            ...

    The returned dict must contain at least ``passed`` (bool) and ``message``
    (str).  Optional keys: ``score`` (float | None), ``details`` (dict).
    """

    def __init__(self, plugin_path: Path, **kwargs: Any) -> None:
        self.plugin_path = plugin_path
        self.kwargs = kwargs
        self._fn = self._load_plugin(plugin_path)

    @staticmethod
    def _load_plugin(plugin_path: Path):
        spec = importlib.util.spec_from_file_location("_veloc_custom_comparator", plugin_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load plugin from {plugin_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules["_veloc_custom_comparator"] = module
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        if not hasattr(module, "compare"):
            raise AttributeError(
                f"Plugin {plugin_path} must export a top-level 'compare' function"
            )
        return module.compare

    def compare(self, baseline_path: Path, resilient_path: Path) -> CompareResult:
        err = self._check_files_exist(baseline_path, resilient_path)
        if err:
            return err

        try:
            result = self._fn(str(baseline_path), str(resilient_path), **self.kwargs)
        except Exception as exc:
            return CompareResult(
                passed=False,
                method="custom-plugin",
                message=f"Plugin raised an exception: {exc}",
            )

        return CompareResult(
            passed=bool(result.get("passed", False)),
            method="custom-plugin",
            score=result.get("score"),
            message=result.get("message", ""),
            details=result.get("details", {}),
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

BUILTIN_METHODS = ("hash", "ssim", "numeric-tolerance", "text-diff")


def make_comparator(
    method: str,
    plugin_path: Path | None = None,
    *,
    dataset: str = "data",
    ssim_threshold: float = 0.9999,
    atol: float = 1e-6,
    rtol: float = 1e-6,
    ignore_patterns: list[str] | None = None,
    **plugin_kwargs: Any,
) -> BaseComparator:
    """Factory: create the appropriate comparator from CLI arguments.

    Parameters
    ----------
    method:
        One of ``"hash"``, ``"ssim"``, ``"numeric-tolerance"``,
        ``"text-diff"``, or ``"custom"``.
    plugin_path:
        Required when *method* is ``"custom"``.
    dataset:
        HDF5 dataset name (used by SSIM and numeric-tolerance comparators).
    ssim_threshold:
        Minimum SSIM value for a pass (SSIM comparator only).
    atol / rtol:
        Absolute / relative tolerance (numeric-tolerance comparator only).
    ignore_patterns:
        Substrings to ignore when comparing text files (text-diff only).
    **plugin_kwargs:
        Extra keyword arguments forwarded to the custom plugin's ``compare()``.
    """
    if method == "hash":
        return HashComparator()
    if method == "ssim":
        return SSIMComparator(dataset=dataset, threshold=ssim_threshold)
    if method == "numeric-tolerance":
        return NumericToleranceComparator(dataset=dataset, atol=atol, rtol=rtol)
    if method == "text-diff":
        return TextDiffComparator(ignore_patterns=ignore_patterns)
    if method == "custom":
        if plugin_path is None:
            raise ValueError(
                "--custom-comparator path is required when --comparison-method=custom"
            )
        return CustomPluginComparator(plugin_path=plugin_path, **plugin_kwargs)
    raise ValueError(
        f"Unknown comparison method {method!r}. "
        f"Choose from: {', '.join(BUILTIN_METHODS)}, custom"
    )
