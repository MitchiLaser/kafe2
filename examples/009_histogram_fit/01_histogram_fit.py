#!/usr/bin/env python

"""
kafe2 example: Histogram Fit
============================

kafe2 is not only capable of performing XY-Fits.
One way to handle one-dimensional data with kafe2 is by fitting a histogram.
The distribution of a random stochastic variable follows a probability density function.
The fit will determine the parameters of that density function, which the dataset is most likely
to follow.
To get to the height of a bin, please multiply the results of the fitted function with the amount
of entries N of the histogram.
"""

import numpy as np
import kafe2


def normal_distribution(x, mu=0.01, sigma=1.0):
    return np.exp(-0.5 * ((x - mu) / sigma) ** 2) / np.sqrt(2.0 * np.pi * sigma ** 2)


# random dataset of 100 random values, following a normal distribution with mu=0 and sigma=1
data = np.random.normal(loc=0, scale=1, size=100)

# Finally, do the fit and plot it:
kafe2.hist_fit(model_function=normal_distribution, data=data, n_bins=10, bin_range=(-5, 5))
kafe2.plot()
