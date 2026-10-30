"""Stage 1: PCA on the 12 style metrics, then a regression of non-penalty xG per 90 on the components.

Penalties are not a style trait, so the model explains non-penalty xG. Penalties are added back
as their own block when we break a team's total xG down (see `breakdown`).
"""
from dataclasses import dataclass

import pandas as pd
import statsmodels.api as sm
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from metrics import METRICS

N_COMPONENTS = 5  # the first 5 components explain ~85% of the variance in the 12 metrics

# Name, plain-language summary, and the metric whose loading must be positive so the name reads right.
COMPONENTS = {
    "PC1": ("Control", "possession, field tilt, progressive passes, few long balls", "possession_share"),
    "PC2": ("Direct & wide", "crosses, vertical passing, regains in the opponent half", "crosses_per_entry"),
    "PC3": ("Pressing volume", "pressures per opponent possession", "pressures_per_opp_possession"),
    "PC4": ("Pressing height", "how far up the pitch the pressures happen", "pressure_height"),
    "PC5": ("Ball-carrying", "progressive carries", "progressive_carries_p90"),
}
PCS = list(COMPONENTS)
NAMES = {pc: c[0] for pc, c in COMPONENTS.items()}
SUMMARIES = {pc: c[1] for pc, c in COMPONENTS.items()}


@dataclass
class Baseline:
    scaler: StandardScaler
    pca: PCA
    ols: sm.regression.linear_model.RegressionResultsWrapper
    score_sd: pd.Series      # spread of each component across team-matches
    mean_pen_p90: float      # average penalty xG per 90 across team-matches

    @property
    def loadings(self):
        return pd.DataFrame(self.pca.components_.T, index=list(METRICS), columns=PCS)

    @property
    def explained(self):
        return pd.Series(self.pca.explained_variance_ratio_, index=PCS)

    @property
    def effects(self):
        """Change in non-penalty xG per 90 for +1 SD of each component, with 95% CI."""
        ci = self.ols.conf_int().loc[PCS]
        out = pd.DataFrame({"effect": self.ols.params[PCS], "lo": ci[0], "hi": ci[1]}).mul(self.score_sd, axis=0)
        return out.assign(p=self.ols.pvalues[PCS])

    @property
    def average_xg(self):
        return self.ols.params["const"] + self.mean_pen_p90

    def components(self, df):
        return pd.DataFrame(self.pca.transform(self.scaler.transform(df[list(METRICS)])), columns=PCS, index=df.index)

    def breakdown(self, df):
        """Split each row's xG/90 into: average team + style components + other + penalties = actual.

        `other` is non-penalty xG the style does not explain (individual quality, set pieces, noise).
        """
        s = self.components(df)
        out = pd.DataFrame(index=df.index)
        out["average_team"] = self.average_xg
        for pc in PCS:
            out[NAMES[pc]] = self.ols.params[pc] * s[pc]
        out["predicted_npxg"] = self.ols.params["const"] + out[[NAMES[p] for p in PCS]].sum(axis=1)
        out["other"] = df["npxg_p90"] - out["predicted_npxg"]
        out["penalties"] = (df["xg_p90"] - df["npxg_p90"]) - self.mean_pen_p90
        out["actual_xg"] = df["xg_p90"]
        return out


def fit(base):
    X = base[list(METRICS)]
    scaler = StandardScaler().fit(X)
    pca = PCA(n_components=N_COMPONENTS).fit(scaler.transform(X))
    # PCA signs are arbitrary: flip each component so its anchor metric loads positively.
    for i, (*_, anchor) in enumerate(COMPONENTS.values()):
        if pca.components_[i, list(METRICS).index(anchor)] < 0:
            pca.components_[i] *= -1
    S = pd.DataFrame(pca.transform(scaler.transform(X)), columns=PCS, index=base.index)
    # Each match appears twice (once per team), so standard errors are clustered by match.
    ols = sm.OLS(base["npxg_p90"], sm.add_constant(S)).fit(
        cov_type="cluster", cov_kwds={"groups": base["match_id"].values}
    )
    return Baseline(scaler, pca, ols, S.std(), (base.xg_p90 - base.npxg_p90).mean())
