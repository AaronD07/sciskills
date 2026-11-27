"""Independent oracle checks using NumPy, pandas and SciPy. Study sessions use the standard library only."""

from io import StringIO
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy import integrate, stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from science import cases  # noqa: E402


def check(actual, expected):
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys(), (actual, expected)
        for key in expected:
            check(actual[key], expected[key])
    elif isinstance(expected, (int, float)):
        np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-7)
    else:
        assert actual == expected, (actual, expected)


def frame(case, name="observations.csv"):
    return pd.read_csv(StringIO(case["files"][name]), dtype=str, keep_default_na=False)


def numeric(case):
    x = frame(case)
    source = case["source"]
    if source == "ChickWeight":
        x = x[x.Diet == "1"].astype(float).sort_values("Time")
        g = x.groupby("Chick")
        delta = g.last() - g.first()
        pool = delta.weight.sum() / delta.Time.sum()
        jack = (delta.weight.sum() - delta.weight) / (delta.Time.sum() - delta.Time)
        return dict(
            birds=len(delta),
            pooled=pool,
            equally_weighted=(delta.weight / delta.Time).mean(),
            jackknife_se=jack.std(ddof=0) * np.sqrt(len(jack) - 1),
        )
    if source == "airquality":
        x = x.replace("", np.nan).dropna(subset=["Ozone", "Solar.R"]).astype(float)
        fit = stats.linregress(x["Solar.R"], x.Ozone)
        return dict(pairs=len(x), slope=fit.slope, intercept=fit.intercept)
    if source == "CO2":
        # These observations are the uninterrupted January 1959–December 1997 series.
        change = x.value.astype(float).diff(12).dropna()
        return dict(
            pairs=len(change), mean_gain=change.mean(), median_gain=change.median()
        )
    if source == "PlantGrowth":
        a = x.loc[x.group == "trt2", "weight"].astype(float)
        b = x.loc[x.group == "trt1", "weight"].astype(float)
        fit = stats.ttest_ind(a, b, equal_var=False)
        gap = a.mean() - b.mean()
        return dict(difference=gap, se=gap / fit.statistic, df=fit.df)
    if source == "Theoph":
        vals = {}
        for key, group in x.groupby("Subject"):
            g = group.astype(float).sort_values("Time")
            boundary = g.loc[g.Time.between(0, 8), "Time"].tolist()
            vals[key] = (
                integrate.quad(
                    lambda t: max(0, np.interp(t, g.Time, g.conc) - g.conc.iloc[0]),
                    0,
                    8,
                    points=boundary,
                )[0]
                / g.Dose.iloc[0]
            )
        mid = np.median(list(vals.values()))
        return dict(
            subjects=len(vals),
            peak_subject=max(vals, key=vals.get),
            median_exposure=mid,
            decision="advance" if mid >= 10 else "defer",
        )
    if source == "Loblolly":
        p = x.astype(float).pivot(index="Seed", columns="age", values="height")
        a, b = (p[15] - p[5]) / 10, (p[25] - p[15]) / 10
        return dict(
            median_individual_pct=np.median(100 * (1 - b / a)),
            aggregate_pct=100 * (1 - b.mean() / a.mean()),
            covariance=np.cov(a, b)[0, 1],
        )
    if source == "ToothGrowth":
        w = frame(case, "target.csv").set_index("dose").relative_frequency.astype(float)
        w /= sum(w)
        t = x.assign(v=x.len.astype(float)).groupby(["dose", "supp"]).v
        mu = t.mean().unstack()
        ee = t.sem().pow(2).unstack()
        gap = w.dot(mu.OJ - mu.VC)
        se = np.sqrt(w.pow(2).dot(ee.OJ + ee.VC))
        return dict(target_difference=gap, se=se, upper95=gap + 1.96 * se)
    if source == "warpbreaks":

        def outcome(g):
            a = g.loc[g.wool == "A", "breaks"].astype(float)
            b = g.loc[g.wool == "B", "breaks"].astype(float)
            return stats.mannwhitneyu(a, b).statistic / (len(a) * len(b))

        low = x[x.tension == "L"]
        ties = len(low[low.wool == "A"].merge(low[low.wool == "B"], on="breaks"))
        targets = (
            frame(case, "allocation.csv")
            .set_index("tension")
            .target_units.astype(float)
        )
        within = sum(outcome(g) * targets[t] for t, g in x.groupby("tension")) / sum(
            targets
        )
        return dict(stratified=within, unstratified=outcome(x), ties_l=ties)
    if source == "esoph":
        x = x[x.alcgp != "40-79"].copy()
        x["high"] = x.alcgp != "0-39g/day"
        t = (
            x.astype({"ncases": int, "ncontrols": int})
            .groupby(["agegp", "tobgp", "high"])[["ncases", "ncontrols"]]
            .sum()
            .unstack(fill_value=0)
        )
        numerator = t["ncases", True] * t["ncontrols", False]
        denominator = t["ncontrols", True] * t["ncases", False]
        mass = t.sum(axis=1)
        return dict(
            adjusted_or=(numerator / mass).sum() / (denominator / mass).sum(),
            crude_or=t["ncases", True].sum()
            * t["ncontrols", False].sum()
            / (t["ncontrols", True].sum() * t["ncases", False].sum()),
            informative_strata=(numerator + denominator).gt(0).sum(),
        )
    if source == "OrchardSprays":
        y = x.decrease.astype(float)

        def residual(cols):
            design = pd.get_dummies(x[cols], drop_first=True, dtype=float)
            design.insert(0, "intercept", 1.0)
            beta, _, rank, _ = np.linalg.lstsq(design, y, rcond=None)
            return ((y - design @ beta) ** 2).sum(), len(y) - rank

        reduced, dr = residual(["rowpos", "colpos"])
        full, df = residual(["rowpos", "colpos", "treatment"])
        return dict(
            residual_df=df,
            treatment_f=((reduced - full) / (dr - df)) / (full / df),
            partial_eta2=1 - full / reduced,
        )
    if source == "morley":
        x = x.astype(float).sort_values(["Expt", "Run"])
        x["r"] = x.Speed - x.groupby("Expt").Speed.transform("mean")
        pairs = x.assign(prior=x.groupby("Expt").r.shift()).dropna()
        return dict(
            absolute_speed=x.groupby("Expt").Speed.mean().mean() + 299000,
            series_se=stats.sem(x.groupby("Expt").Speed.mean()),
            lag_slope=np.linalg.lstsq(
                pairs.prior.to_numpy()[:, None], pairs.r, rcond=None
            )[0][0],
        )
    x = x[x.station != ""].astype({"dist": float, "accel": float})
    x = (
        x[(x.dist > 0) & (x.accel > 0)]
        .groupby("event")
        .filter(lambda g: g.dist.nunique() > 1)
    )
    dummies = pd.get_dummies(x.event, dtype=float).to_numpy()
    y = np.log(x.accel)
    design = np.column_stack([dummies, np.log(x.dist)])
    fit = np.linalg.lstsq(design, y, rcond=None)[0]
    base = np.linalg.lstsq(dummies, y, rcond=None)[0]
    return dict(
        event_ids=sorted(x.event.unique(), key=int),
        records=len(x),
        log_slope=fit[-1],
        within_r2=1
        - np.linalg.norm(y - design @ fit) ** 2
        / np.linalg.norm(y - dummies @ base) ** 2,
        interpretation="decreasing"
        if fit[-1] < 0
        else "increasing"
        if fit[-1] > 0
        else "flat",
    )


def independent_program(source, rows):
    if not rows:
        return 0 if source == "airquality" else {}
    x = pd.DataFrame(rows)
    if source == "ChickWeight":
        p = x.assign(w=x.weight.astype(float)).pivot(
            index=["Diet", "Chick"], columns="Time", values="w"
        )
        return (
            (p.get("20") - p.get("0")).dropna().groupby(level="Diet").median().to_dict()
        )
    if source == "airquality":
        dates = pd.to_datetime(
            dict(year=[1973] * len(x), month=x.Month.astype(int), day=x.Day.astype(int))
        )
        valid = dates[pd.to_numeric(x.Ozone, errors="coerce") > 60].sort_values()
        return (
            int(valid.groupby(valid.diff().dt.days.ne(1).cumsum()).size().max())
            if len(valid)
            else 0
        )
    if source == "CO2":
        x["year"] = (x.time.astype(float) * 12).round().astype(int) // 12
        g = x.assign(v=x.value.astype(float)).groupby("year").v
        return {str(k): v for k, v in (g.max() - g.min())[g.count() == 12].items()}
    if source == "PlantGrowth":
        return (
            x.assign(v=pd.to_numeric(x.weight, errors="coerce"))
            .dropna()
            .groupby("group")
            .v.apply(stats.median_abs_deviation)
            .to_dict()
        )
    if source == "Theoph":
        out = {}
        for s, g in x.groupby("Subject"):
            g = g.astype(float).sort_values("Time").reset_index(drop=True)
            hi = g.conc.max() / 2
            after = g.loc[g.conc.idxmax() :]
            matches = after[(after.conc <= hi) & (after.conc.shift() > hi)]
            if len(matches):
                j = matches.index[0]
                out[s] = np.interp(
                    hi, g.loc[[j, j - 1], "conc"], g.loc[[j, j - 1], "Time"]
                )
        return out
    if source == "Loblolly":
        out = {}
        for s, g in x.groupby("Seed"):
            g = g.astype(float).sort_values("age")
            h, t = g.height.to_numpy(), g.age.to_numpy()
            if len(h) > 2:
                out[s] = max(
                    abs(h[i] - np.interp(t[i], np.delete(t, i), np.delete(h, i)))
                    for i in range(1, len(h) - 1)
                )
        return out
    if source == "ToothGrowth":
        pairs = x[x.supp == "OJ"].merge(x[x.supp == "VC"], on="dose")
        return (
            (pairs.len_x.astype(float) - pairs.len_y.astype(float))
            .groupby(pairs.dose)
            .median()
            .to_dict()
        )
    if source == "warpbreaks":
        out = {}
        for (w, t), g in x.groupby(["wool", "tension"]):
            high = np.sort(g.breaks.astype(float))[::-1]
            mass = len(high) / 4
            out[w + "/" + t] = (
                np.dot(high, np.clip(mass - np.arange(len(high)), 0, 1)) / mass
            )
        return out
    if source == "esoph":
        ordering = {"0-9g/day": 0, "10-19": 1, "20-29": 2, "30+": 3}
        out = {}
        for age, g in x.groupby("agegp"):
            codes = g.tobgp.map(ordering)
            patients = np.repeat(codes.to_numpy(), g.ncases.astype(int))
            controls = np.repeat(codes.to_numpy(), g.ncontrols.astype(int))
            if len(patients) and len(controls):
                out[age] = stats.mannwhitneyu(patients, controls).statistic / (
                    len(patients) * len(controls)
                )
        return out
    if source == "OrchardSprays":
        xy = x.astype({"rowpos": int, "colpos": int, "decrease": float})
        near = xy.merge(xy, how="cross")
        same = (near.rowpos_x - near.rowpos_y).abs() + (
            near.colpos_x - near.colpos_y
        ).abs()
        residual = (
            near[same == 1]
            .groupby(["treatment_x", "rownames_x"])
            .apply(
                lambda g: g.decrease_x.iloc[0] - g.decrease_y.mean(),
                include_groups=False,
            )
        )
        return residual.groupby(level=0).median().to_dict()
    if source == "morley":
        out = {}
        for exp, g in x.groupby("Expt"):
            obs = g.astype(float).set_index("Run").Speed.sort_index()
            if not {1, 2, 3}.issubset(obs.index):
                continue
            increments = (obs - obs.loc[[1, 2, 3]].median() - 10).loc[
                lambda z: z.index > 3
            ]
            for _, sequence in increments.groupby(
                increments.index.to_series().diff().ne(1).cumsum()
            ):
                total = sequence.cumsum()
                scores = total - total.cummin().clip(upper=0)
                hits = scores[scores >= 75]
                if len(hits):
                    out[exp] = int(hits.index[0])
                    break
        return out
    y = x[x.station != ""].astype({"dist": float, "accel": float})
    y = y[(y.dist > 0) & (y.accel > 0)]
    out = {}
    for ev, g in y.groupby("event"):
        if g.station.nunique() < 2:
            continue
        obs = np.log(g.accel.to_numpy())
        dist = np.log(g.dist.to_numpy())
        diff = np.abs(dist[:, None] - dist[None, :])
        stations = g.station.to_numpy()
        diff[stations[:, None] == stations[None, :]] = np.inf
        nearest = diff <= diff.min(axis=1)[:, None] + 1e-12
        pred = nearest @ obs / nearest.sum(axis=1)
        out[ev] = np.mean(abs(obs - pred))
    return out


def policy(case):
    x = frame(case)
    source = case["source"]
    if source == "ChickWeight":
        final = (
            x[x.Diet == "1"].assign(age=x.Time.astype(int)).groupby("Chick").age.max()
        )
        return dict(ids=sorted(final[final < 21].index, key=int), reviewed=len(final))
    if source == "airquality":
        p = (
            x.assign(complete=(x.Ozone != "") & (x["Solar.R"] != ""))
            .groupby("Month")
            .complete
        )
        good = p.mean().loc[lambda z: z >= 0.7].index.tolist()
        return dict(
            months=sorted(good, key=int), retained_days=p.sum().reindex(good).sum()
        )
    if source == "CO2":
        months = pd.period_range("1959-01", periods=len(x), freq="M")
        annual = x.value.astype(float).groupby(months.year).min()
        years = list(map(str, annual[annual > 350].index))
        return dict(years=years, first_year=years[0])
    if source == "PlantGrowth":
        val = x.weight.astype(float)
        maximum = val[x.group == "ctrl"].max()
        return dict(
            control_max=maximum,
            ids=sorted(
                x.loc[(val > maximum) & (x.group != "ctrl"), "rownames"], key=int
            ),
        )
    if source == "Theoph":
        log = frame(case, "QC.csv").astype({"filed_day": int, "revision": int})
        held = (
            log[(log.filed_day <= 5) & (log.signed == "yes")]
            .sort_values("revision")
            .drop_duplicates("assay", keep="last")
        )
        clean = x[~x.rownames.isin(held.loc[held.state == "hold", "assay"])].astype(
            {"conc": float, "Time": float}
        )
        eligible = clean.loc[(clean.Time == 0) & (clean.conc <= 0.5), "Subject"]
        maxima = clean[clean.Subject.isin(eligible)].groupby("Subject").conc.max()
        return dict(
            eligible_subjects=len(eligible),
            high_ids=sorted(maxima[maxima >= 9].index, key=int),
            max_retained_concentration=maxima.max(),
        )
    if source == "Loblolly":
        lots = frame(case, "lots.csv")
        release = (
            frame(case, "ledger.csv")
            .astype({"revision": int, "available_day": int})
            .query("available_day<=15")
            .sort_values("revision")
            .drop_duplicates("lot", keep="last")
        )
        lots = lots[~lots.lot.isin(release.loc[release.status == "review", "lot"])]
        grid = x.assign(y=x.height.astype(float)).pivot(
            index="Seed", columns="age", values="y"
        )
        growth = grid["25"] - grid["10"]
        gap = lots.lead_seed.map(growth) - lots.reference_seed.map(growth)
        return dict(
            lot_ids=sorted(lots.lot), mean_gap=gap.mean(), positive_lots=(gap > 0).sum()
        )
    if source == "ToothGrowth":
        reg = frame(case, "registry.csv").astype(
            {"target_weight": float, "threshold": float}
        )
        rev = (
            frame(case, "revisions.csv")
            .astype({"published_day": int, "revision": int, "threshold": float})
            .query("published_day<=5")
            .sort_values("revision")
            .drop_duplicates("bin", keep="last")
        )
        reg["limit"] = reg.bin.map(rev.set_index("bin").threshold).fillna(reg.threshold)
        q = x.merge(reg, on="dose")
        p = (q.len.astype(float) >= q.limit).groupby([q.bin, q.supp]).mean().unstack()
        w = reg.set_index("bin").target_weight
        return dict(
            lower_oj_bins=sorted(p.index[p.OJ < p.VC]),
            target_oj=w.dot(p.OJ),
            target_vc=w.dot(p.VC),
        )
    if source == "warpbreaks":
        reg = (
            frame(case, "fleet.csv")
            .astype({"looms_A": int, "looms_B": int})
            .set_index(["site", "tension"])
        )
        moves = (
            frame(case, "transfers.csv")
            .query("approved=='1'")
            .astype({"transfer": int})
            .set_index(["site", "tension"])
            .transfer
        )
        means = (
            x.assign(n=x.breaks.astype(float))
            .groupby(["tension", "wool"])
            .n.mean()
            .unstack()
        )
        base = reg.mul(0)
        base["looms_A"] = reg.looms_A * reg.index.get_level_values("tension").map(
            means.A
        )
        base["looms_B"] = reg.looms_B * reg.index.get_level_values("tension").map(
            means.B
        )
        diff = moves * moves.index.get_level_values("tension").map(means.B - means.A)
        sites = diff.groupby(level="site").sum()
        return dict(
            expected_before=base.sum().sum(),
            expected_after=base.sum().sum() + diff.sum(),
            sites_with_reduction=sorted(sites[sites < 0].index),
        )
    if source == "esoph":
        m = x.merge(frame(case, "age-map.csv"), on="agegp").astype(
            {"ncases": int, "ncontrols": int}
        )
        cells = m.groupby(["reporting_label", "alcgp"])[["ncases", "ncontrols"]].sum()
        hidden = cells.min(axis=1) < 12
        count = hidden.sum()
        for label in m.reporting_label.unique():
            h = hidden.loc[label]
            if h.sum() == 1:
                totals = cells.loc[label].sum(axis=1)
                hidden[label, totals[~h].idxmin()] = True
        return dict(
            primary_cells=count,
            final_hidden=["/".join(k) for k in sorted(hidden[hidden].index)],
            published_people=cells[~hidden].sum().sum(),
        )
    if source == "OrchardSprays":
        reg = (
            frame(case, "incidents.csv")
            .astype({"available_day": int, "revision": int})
            .query("available_day<=5")
            .sort_values("revision")
            .drop_duplicates("incident", keep="last")
            .query("status=='open'")
        )
        spots = (
            reg.merge(frame(case, "layout.csv"), on=["bank", "lane"])[
                ["rowpos", "column"]
            ]
            .astype(int)
            .to_numpy()
        )
        cells = x[["rowpos", "colpos"]].astype(int).to_numpy()
        hidden = (np.abs(cells[:, None, :] - spots[None, :, :]).sum(axis=2) <= 1).any(
            axis=1
        )
        means = (
            x[~hidden]
            .assign(y=x.loc[~hidden, "decrease"].astype(float))
            .groupby("treatment")
            .y.mean()
        )
        return dict(
            excluded_count=hidden.sum(),
            excluded_cells=sorted(x.loc[hidden, "rownames"], key=int),
            h_minus_a=means.H - means.A,
        )
    if source == "morley":
        reg = (
            frame(case, "certificates.csv")
            .astype(
                {"start_run": int, "version": int, "released_day": int, "bias": float}
            )
            .query("released_day<=5")
        )
        pairs = x.merge(
            frame(case, "instruments.csv"), left_on="Expt", right_on="experiment"
        ).merge(reg, on="device")
        live = (
            pairs[pairs.start_run <= pairs.Run.astype(int)]
            .sort_values(["start_run", "version"])
            .drop_duplicates("rownames", keep="last")
        )
        y = (live.Speed.astype(float) - live.bias).groupby(live.Expt).mean()
        return dict(
            series_ids=sorted(y.index, key=int),
            retained_runs=len(live),
            calibrated_speed=y.mean() + 299000,
        )
    reg = (
        frame(case, "calibration.csv")
        .astype({"released_day": int, "version": int})
        .query("released_day<=5")
        .sort_values("version")
        .drop_duplicates("station", keep="last")
    )
    p = (
        frame(case, "commission.csv")
        .merge(reg, on="station", how="left")
        .merge(x, on=["event", "station"], how="left")
    )
    p["value"] = pd.to_numeric(p.factor, errors="coerce") * pd.to_numeric(
        p.accel, errors="coerce"
    )
    good = p.groupby("event").value.count() == p.groupby("event").size()
    maxima = p.groupby("event").value.max()
    return dict(
        complete_events=sorted(good[good].index, key=int),
        unresolved_events=sorted(good[~good].index, key=int),
        mean_event_max=maxima[good].mean(),
    )


def main():
    tasks = cases("dev") + cases("science")
    programs = 0
    for case in tasks:
        try:
            if case["route"] == "program":
                for test in case["tests"]:
                    check(
                        independent_program(case["source"], test["rows"]),
                        test["expected"],
                    )
                    programs += 1
                expected = [test["expected"] for test in case["tests"]]
                check(expected[0], expected[3])
                assert expected[0] != expected[1] or expected[0] != expected[2]
            else:
                check(
                    (numeric if case["route"] == "numbers" else policy)(case),
                    case["gold"],
                )
        except Exception:
            print("Failed independent validation:", case["id"], file=sys.stderr)
            raise
    print(
        f"Validated {len(tasks)} science case references, including {programs} program input/output pairs."
    )


if __name__ == "__main__":
    if not __debug__:
        raise SystemExit("Run the reference verifier with Python assertions enabled.")
    main()
