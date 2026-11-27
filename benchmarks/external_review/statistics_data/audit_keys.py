"""Independent specification sensitivity checks on original, evaluator-side CSVs."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import patsy
from scipy.stats import norm, t
import statsmodels.formula.api as smf
from statsmodels.duration.hazard_regression import PHReg

ROOT = Path(__file__).resolve().parent


def dataset(number):
    return pd.read_csv(ROOT / f"pbench-{number:02d}" / "dataset.csv")


def iv_pvalue(data, outcome, exposure, controls, instruments, cluster=None):
    """2SLS with HC1 or cluster-robust sandwich covariance on structural residuals."""
    design = patsy.dmatrix(f"{exposure} + {controls}", data)
    x = np.asarray(design)
    z = np.asarray(patsy.dmatrix(f"{instruments} + {controls}", data))
    x_index = design.design_info.column_names.index(exposure)
    projected = z @ np.linalg.lstsq(z, x, rcond=None)[0]
    inverse = np.linalg.pinv(projected.T @ projected)
    beta = inverse @ projected.T @ data[outcome].to_numpy()
    scores = projected * (data[outcome].to_numpy() - x @ beta)[:, None]
    n, k = len(x), np.linalg.matrix_rank(x)
    correction = n / (n - k)
    degrees = n - k
    if cluster:
        scores = pd.DataFrame(scores).groupby(data[cluster].to_numpy()).sum().to_numpy()
        groups = len(scores)
        degrees = groups - 1
        correction = groups / degrees * (n - 1) / (n - k)
    var = correction * inverse @ (scores.T @ scores) @ inverse
    return float(2 * t.sf(abs(beta[x_index]) / np.sqrt(var[x_index, x_index]), degrees))


def clustered(data, formula, cluster):
    return smf.ols(formula, data).fit(
        cov_type="cluster", cov_kwds={"groups": data[cluster]}, use_t=True
    )


def audit():
    results = {}
    d = dataset(1)
    controls = "offer4 + final4 + yearlong + low + waved2 + lnlastamount"
    results[1] = {
        label: iv_pvalue(
            d, "lnloansize", "term", controls + extra, "termshown6 + termshown12"
        )
        for label, extra in [
            ("stated controls with HC1", ""),
            (
                "also branch and income indicators",
                " + C(branchuse) + C(sales_grossincomecat2)",
            ),
        ]
    }
    d = (
        dataset(2)
        .dropna(subset=["fully_immunized"])
        .query("spillover == 1 or NonTreat == 1")
    )
    results[2] = {
        label: float(
            clustered(
                d,
                "fully_immunized ~ TreatNonIncentive + TreatIncentive" + extra,
                "locid",
            ).pvalues["TreatIncentive"]
        )
        for label, extra in [
            ("village clustered, arm indicators", ""),
            ("also age in months", " + agemon"),
        ]
    }
    d = dataset(3)
    long = d.melt(
        id_vars=[x for x in d.columns if x not in ["cc_switched", "m_switched"]],
        value_vars=["cc_switched", "m_switched"],
        var_name="race",
        value_name="switched",
    ).dropna(subset=["switched"])
    adjustment = (
        "C(marital_stat) + male + age + catholic + hh_voting_mems + "
        + " + ".join(x for x in d if x.startswith("employ_stat"))
        + " + elementary + highschool + some_college + some_highschool + vocational + college_up + bornhere + childmigrant + adultmigrant"
    )
    results[3] = {
        label: float(
            clustered(
                long, "switched ~ C(race) * (pt2 + pt3" + extra + ")", "respondent_id"
            ).pvalues["C(race)[T.m_switched]:pt2"]
        )
        for label, extra in [
            ("respondent clustered, race by treatment", ""),
            ("also race-specific demographic controls", " + " + adjustment),
        ]
    }
    d = dataset(4)
    results[4] = {
        formula: float(smf.logit(formula, d).fit(disp=0).pvalues["age"])
        for formula in ["tvdlm ~ age", 'tvdlm ~ age + C(sex) + Q("cad.dur") + choleste']
    }
    d = dataset(5)
    exposure = pd.DataFrame({"treatment": (d.treat == "rIFN-g").astype(int)})
    model = PHReg(d.tstop, exposure, status=d.status, entry=d.tstart, ties="efron")
    first = d.enum == 1
    results[5] = {
        "recurrent-event Cox, patient clustered": float(
            model.fit(groups=d.id).pvalues[0]
        ),
        "time to first infection, Cox": float(
            PHReg(
                d.tstop[first],
                exposure[first],
                status=d.status[first],
                entry=d.tstart[first],
                ties="efron",
            )
            .fit()
            .pvalues[0]
        ),
    }
    d = (
        dataset(6)
        .query("tot_save <= 20000")
        .dropna(subset=["tot_save", "migrant_new", "village"])
        .copy()
    )
    d["encouraged"] = (d.incentivized == "Incentivized").astype(int)
    d["migrant_new"] = (d.migrant_new == "Yes").astype(int)

    results[6] = {
        label: iv_pvalue(d, "tot_save", "migrant_new", controls, instrument, "village")
        for label, controls, instrument in [
            ("village clustered, incentive assignment", "1", "encouraged"),
            ("also subdistrict indicators", "C(upazila)", "encouraged"),
            (
                "separate assignments, subdistrict indicators",
                "C(upazila)",
                "cash + credit + info",
            ),
        ]
    }
    d = dataset(7)
    wards = " + ".join(x for x in d if x.startswith("ward_") and x != "ward_20")
    results[7] = {
        label: float(
            smf.ols("zscore_3 ~ t" + extra, d).fit(cov_type="HC1").pvalues["t"]
        )
        for label, extra in [
            ("difference by assignment, HC1", ""),
            (
                "also ward indicators, road and village size",
                " + road + tothhs + " + wards,
            ),
        ]
    }
    d = dataset(8).query("open == 1").dropna(subset=["freeatm"])
    base = "avg_eff ~ freeatm + atm_wife + atm_hub + ind_w + ind_h"
    results[8] = {
        label: float(
            np.squeeze(
                clustered(d, base + extra, "ipacoupleid")
                .t_test("freeatm + atm_wife = 0")
                .pvalue
            )
        )
        for label, extra in [
            ("couple clustered, account effects", ""),
            (
                "also cash-prize interactions",
                " + "
                + " + ".join(
                    x for x in d if x.startswith(("cashprize_h_", "cashprize_w_"))
                ),
            ),
        ]
    }
    d = dataset(9)
    results[9] = {
        formula: float(smf.logit(formula, d).fit(disp=0).pvalues["smoke"])
        for formula in [
            "low ~ smoke + age + lwt + C(race)",
            "low ~ smoke + age + lwt + C(race) + ptl + ht + ui + ftv",
        ]
    }
    d = dataset(10).query('drug != "not randomized"').copy()
    d["active"] = (d.drug == "D-penicillamine").astype(int)
    results[10] = {}
    for column in ["age", "bili", "albumin", "protime", "stage"]:
        d[column] = (d[column] - d[column].mean()) / d[column].std()
    for label, formula in [
        ("randomized-only Cox", "active"),
        (
            "also named baseline characteristics",
            "active + age + C(sex) + bili + albumin + protime + stage",
        ),
    ]:
        m = PHReg.from_formula(
            'Q("fu.days") ~ ' + formula, d, status=d.status, ties="efron"
        )
        results[10][label] = float(
            m.fit(method="bfgs", maxiter=300).pvalues[m.exog_names.index("active")]
        )
    return results


def report():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    fitted = audit()
    results = {}
    for row in manifest:
        number = int(row["id"].split("-")[1])
        values = fitted[number]
        gold = row["answer"]
        gold_z = norm.ppf(1 - max(gold["p_value"], 2.2e-16) / 2)
        decisions_match = all(
            (p < 0.05) == (gold["decision"] == "reject") for p in values.values()
        )
        magnitudes_match = all(
            abs(norm.ppf(1 - max(p, 2.2e-16) / 2) - gold_z) < 0.5
            for p in values.values()
        )
        results[row["id"]] = {
            "strict_eligible": bool(decisions_match and magnitudes_match),
            "decision_eligible": bool(decisions_match),
            "reference": gold,
            "specification_pvalues": values,
        }
    return results


if __name__ == "__main__":
    print(json.dumps(report(), indent=2, allow_nan=False))
