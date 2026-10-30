"""Tournament baseline: PCA on the 12 style metrics, then OLS of xG per 90 on the components."""
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from metrics import METRICS

N_COMPONENTS = 5  # first 5 components explain ~85% of the variance in the 12 metrics

# Name, and the metric whose loading must be positive so the name reads the right way round.
COMPONENTS = {
    "PC1": ("Control", "possession_share"),
    "PC2": ("Direct & wide", "crosses_per_entry"),
    "PC3": ("Pressing volume", "pressures_per_opp_possession"),
    "PC4": ("Pressing height", "pressure_height"),
    "PC5": ("Ball-carrying", "progressive_carries_p90"),
}
PCS = list(COMPONENTS)
NAMES = {pc: name for pc, (name, _) in COMPONENTS.items()}


@dataclass
class Baseline:
    scaler: StandardScaler
    pca: PCA
    ols: sm.regression.linear_model.RegressionResultsWrapper
    target: str

    @property
    def loadings(self):
        return pd.DataFrame(self.pca.components_.T, index=list(METRICS), columns=PCS)

    @property
    def explained(self):
        return pd.Series(self.pca.explained_variance_ratio_, index=PCS)

    @property
    def coefs(self):
        ci = self.ols.conf_int()
        return pd.DataFrame({"coef": self.ols.params, "lo": ci[0], "hi": ci[1], "p": self.ols.pvalues})

    def score(self, df):
        """Add component scores, predicted xG, residual and per-component contributions."""
        out = df.copy()
        s = self.pca.transform(self.scaler.transform(df[list(METRICS)]))
        out[PCS] = s
        b = self.ols.params
        for pc in PCS:
            out[f"contrib_{pc}"] = b[pc] * out[pc]
        out["predicted"] = b["const"] + out[[f"contrib_{pc}" for pc in PCS]].sum(axis=1)
        out["residual"] = out[self.target] - out["predicted"]
        return out


def fit(base, target="xg_p90"):
    scaler = StandardScaler().fit(base[list(METRICS)])
    pca = PCA(n_components=N_COMPONENTS).fit(scaler.transform(base[list(METRICS)]))
    # PCA signs are arbitrary: flip each component so its anchor metric loads positively.
    for i, (_, anchor) in enumerate(COMPONENTS.values()):
        if pca.components_[i, list(METRICS).index(anchor)] < 0:
            pca.components_[i] *= -1
    X = pd.DataFrame(pca.transform(scaler.transform(base[list(METRICS)])), columns=PCS, index=base.index)
    # Each match appears twice (once per team), so cluster the standard errors by match.
    ols = sm.OLS(base[target], sm.add_constant(X)).fit(
        cov_type="cluster", cov_kwds={"groups": base["match_id"].values}
    )
    return Baseline(scaler, pca, ols, target)
