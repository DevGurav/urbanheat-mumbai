"""Ward-grouped spatial cross-validation, and its naive random-split contrast (ADR-0006/0008).

The **spatial** score is the honest one: `GroupKFold` on `ward_code` holds out whole wards, so
no test cell has a neighbour in training. The **random** score is reported only for the gap —
how much apparent accuracy is really spatial autocorrelation. Reporting the random number as if
it were the model's skill is the mistake this module exists to prevent.
"""

from __future__ import annotations

from sklearn.base import clone
from sklearn.model_selection import GroupKFold, KFold, cross_validate

N_SPLITS = 5
SCORING = {
    "r2": "r2",
    "rmse": "neg_root_mean_squared_error",
    "mae": "neg_mean_absolute_error",
}


def _summarise(cv_results: dict) -> dict[str, float]:
    # RMSE/MAE come back negated (sklearn maximises), so flip their sign.
    return {
        "r2": float(cv_results["test_r2"].mean()),
        "rmse": float(-cv_results["test_rmse"].mean()),
        "mae": float(-cv_results["test_mae"].mean()),
    }


def spatial_cv(model, X, y, groups, *, n_splits: int = N_SPLITS) -> dict[str, float]:
    """Mean R²/RMSE/MAE over ward-grouped folds — the honest, reported metric."""
    splitter = GroupKFold(n_splits=n_splits)
    results = cross_validate(clone(model), X, y, groups=groups, cv=splitter, scoring=SCORING)
    return _summarise(results)


def random_cv(model, X, y, *, n_splits: int = N_SPLITS, seed: int = 42) -> dict[str, float]:
    """Mean R²/RMSE/MAE over a shuffled random split — reported only for the gap."""
    splitter = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    results = cross_validate(clone(model), X, y, cv=splitter, scoring=SCORING)
    return _summarise(results)
