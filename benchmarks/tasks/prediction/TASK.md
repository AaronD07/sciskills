# Held-out prediction

Repair `analysis.py` while preserving `evaluate(train, test)`.

Train a constant predictor equal to the mean of training targets, then evaluate its mean squared error on test targets. Both inputs are nonempty sequences of finite numbers. Return a dict with `prediction` and `mse`. Invalid inputs raise ValueError. The prediction must depend only on train, even when test changes. Use Python's standard library.

Explain the change and run a small independent check. Do not change this contract.
