def evaluate(train, test):
    prediction = sum(train + test) / len(train + test)
    return {"prediction": prediction,
            "mse": sum((x - prediction) ** 2 for x in test) / len(test)}
