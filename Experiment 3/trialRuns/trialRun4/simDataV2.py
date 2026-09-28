import pandas as pd
import numpy as np
import json, sys


def classify(row):
    if row["groundTruth"] == False and row["percCredibility"] == "p.False":
        return "hit"
    elif row["groundTruth"] == False and row["percCredibility"] != "p.False":
        return "miss"
    elif row["groundTruth"] == True and row["percCredibility"] == "p.True":
        return "hit"
    else:
        return "miss"


def createSimData(headlineData, NoParticipants):
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
            onlineResponses.append(np.random.binomial(1, conditionalProbs[i]))
        # get the confidence ratings from a normal distribution based on the mean and std of the distribution.
        condition_map = {
            (1, 1): {
                "mean": 74.80000,  # headline["mean|percTrue|onlineYes"],
                "std": 23.00435,  # headline["std|percTrue|onlineYes"],
            },
            (0, 0): {
                "mean": 64.55172,  # headline["mean|percFalse|onlineNo"],
                "std": 17.59380,  # headline["std|percFalse|onlineNo"],
            },
            (1, 0): {
                "mean": 52.40909,  # headline["mean|percTrue|onlineNo"],
                "std": 25.22784,  # headline["std|percTrue|onlineNo"],
            },
            (0, 1): {
                "mean": 85.25000,  # headline["mean|percFalse|onlineYes"],
                "std": 15.39210,  # headline["std|percFalse|onlineYes"],
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


with open("headlines.json", "r") as file:
    json_data = file.read()

# Parse the JSON data
headlineData = json.loads(json_data)

participantNo = int(sys.argv[1])
simData = createSimData(headlineData, participantNo)

simData.to_csv("simData.csv", index=False)
