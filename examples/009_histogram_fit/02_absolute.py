#!/usr/bin/env python

"""
kafe2 example: Histogram Fit (Absolute)
=======================================

This example is equivalent to the other histogram example in this folder except for the fact that
the model function is not a density but has an amplitude as one of its parameters. Long-term this
will be replaced by a better example.
"""

import numpy as np
import kafe2


def normal_distribution(x, A=100, mu=0.01, sigma=1.0):
    return A * np.exp(-0.5 * ((x - mu) / sigma) ** 2) / np.sqrt(2.0 * np.pi * sigma ** 2)


# random dataset of 100 random values, following a normal distribution with mu=0 and sigma=1
data = np.random.normal(loc=0, scale=1, size=100)

# Finally, do the fit and plot it:
kafe2.hist_fit(model_function=normal_distribution, data=data, n_bins=10, bin_range=(-5, 5), density=False)
kafe2.plot()
