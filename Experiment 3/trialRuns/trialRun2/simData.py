# %%
import pandas as pd
import numpy as np
from scipy.stats import chi2_contingency
import sys

# from statsmodels.stats.multicomp import MultiComparison
import statsmodels.api as sm
from statsmodels.formula.api import ols


# %%
def create_crosstab(group):
    return pd.crosstab(group["percCredibility"], group["onlineResponse"])


def classify(row):
    if row["groundTruth"] == False and row["percCredibility"] == "p.False":
        return "hit"
    elif row["groundTruth"] == False and row["percCredibility"] != "p.False":
        return "miss"
    elif row["groundTruth"] == True and row["percCredibility"] == "p.True":
        return "hit"
    else:
        return "miss"


def read_csv(csv_file):
    df = pd.read_csv(csv_file)
    groupedData = df.groupby(["mainHeadline", "groundTruth"])
    crosstab_dict = groupedData.apply(create_crosstab)
    crosstab_dict_wide = crosstab_dict.reset_index().pivot_table(
        index=["mainHeadline", "groundTruth"],
        columns="percCredibility",
        values=["onlineNo", "onlineYes"],
        fill_value=0,
    )
    crosstab_dict_wide.columns = crosstab_dict_wide.columns.map("|".join).str.strip("|")
    crosstab_dict_wide["total"] = crosstab_dict_wide.sum(axis=1)
    crosstab_dict_wide["PT"] = (
        crosstab_dict_wide["onlineNo|percTrue"]
        + crosstab_dict_wide["onlineYes|percTrue"]
    ) / crosstab_dict_wide["total"]
    crosstab_dict_wide["PF"] = 1 - crosstab_dict_wide["PT"]
    crosstab_dict_wide["PCT"] = crosstab_dict_wide["onlineYes|percTrue"] / (
        crosstab_dict_wide["onlineYes|percTrue"]
        + crosstab_dict_wide["onlineNo|percTrue"]
    )
    crosstab_dict_wide["PCF"] = crosstab_dict_wide["onlineYes|percFalse"] / (
        crosstab_dict_wide["onlineYes|percFalse"]
        + crosstab_dict_wide["onlineNo|percFalse"]
    )
    crosstab_dict_wide.fillna(0, inplace=True)
    confData = df.groupby(["mainHeadline", "percCredibility", "onlineResponse"])[
        "confidence"
    ].agg(["mean", "std"])
    confData = confData.reset_index().pivot_table(
        index=["mainHeadline"],
        columns=["percCredibility", "onlineResponse"],
        values=["mean", "std"],
        fill_value=0,
    )
    confData.columns = confData.columns.map("|".join).str.strip("|")
    summary = confData.join(crosstab_dict_wide)
    summary.reset_index(inplace=True)
    headlineData = summary.to_dict(orient="records")
    return headlineData


# %%
def createSimData(fileName, NoParticipants):
    headlineData = read_csv(fileName)
    dataframes = []
    for headline in headlineData:
        # get the perceived credibility of the headline for each participant
        trueProb = headline["PT"]
        conditionalProbs = [headline["PCF"], headline["PCT"]]
        # get the perceptions
        perceptions = np.random.binomial(1, trueProb, NoParticipants)
        # get the online responses based on perceptions
        onlineResponses = []
        for i in perceptions:
            condProb = conditionalProbs[i]
            onlineResponses.append(np.random.binomial(1, condProb))
        # get the confidence ratings from a normal distribution based on the mean and std of the distribution.
        condition_map = {
            (1, 1): {
                "mean": headline["mean|percTrue|onlineYes"],
                "std": headline["std|percTrue|onlineYes"],
            },
            (0, 0): {
                "mean": headline["mean|percFalse|onlineNo"],
                "std": headline["std|percFalse|onlineNo"],
            },
            (1, 0): {
                "mean": headline["mean|percTrue|onlineNo"],
                "std": headline["std|percTrue|onlineNo"],
            },
            (0, 1): {
                "mean": headline["mean|percFalse|onlineYes"],
                "std": headline["std|percFalse|onlineYes"],
            },
        }
        confidence = []
        for a, b in zip(perceptions, onlineResponses):
            stats = condition_map.get((a, b), None)
            confidence.append(np.random.normal(stats["mean"], stats["std"]))
        headlineDf = pd.DataFrame(
            {
                "mainHeadline": headline["mainHeadline"],
                "groundTruth": headline["groundTruth"],
                "onlineResponse": onlineResponses,
                "percCredibility": perceptions,
                "confidence": confidence,
            }
        )
        dataframes.append(headlineDf)
    simData = pd.concat(dataframes, axis=0)
    simData["onlineResponse"] = simData["onlineResponse"].replace({1: "yes", 0: "no"})
    simData["percCredibility"] = simData["percCredibility"].replace(
        {1: "p.True", 0: "p.False"}
    )

    simData["classification"] = simData.apply(classify, axis=1)

    return simData


# %%
sampleFile = sys.argv[1]
participantNo = int(sys.argv[2])
simData = createSimData(sampleFile, participantNo)
simData.to_csv("simData.csv", index=False)
