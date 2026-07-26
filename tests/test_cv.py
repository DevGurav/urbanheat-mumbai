"""The CV scorers must return the three metrics and respect the group holdout. Pure logic on a
tiny synthetic dataset — no project data needed."""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from data_pipeline.ml.cv import random_cv, spatial_cv


def _toy():
    rng = np.random.default_rng(0)
    n = 200
    x = pd.DataFrame({"a": rng.normal(size=n), "b": rng.normal(size=n)})
    y = x["a"] * 2.0 + rng.normal(scale=0.1, size=n)  # an easy linear signal
    groups = pd.Series(np.arange(n) % 5)  # exactly 5 balanced groups
    return x, y, groups


def test_spatial_cv_returns_the_three_metrics():
    x, y, groups = _toy()
    scores = spatial_cv(LinearRegression(), x, y, groups, n_splits=5)
    assert set(scores) == {"r2", "rmse", "mae"}
    assert scores["r2"] > 0.9  # a linear model recovers a linear signal
    assert scores["rmse"] >= 0


def test_random_cv_returns_the_three_metrics():
    x, y, _ = _toy()
    scores = random_cv(LinearRegression(), x, y, n_splits=5)
    assert set(scores) == {"r2", "rmse", "mae"}
    assert scores["rmse"] >= 0
