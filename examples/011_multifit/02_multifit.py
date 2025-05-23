#!/usr/bin/env python
r"""
Fitting several related models in a multi-model fit
===================================================

The premise of this example is deceptively simple: a series
of voltages is applied to a resistor and the resulting current
is measured. The aim is to fit a model to the collected data
consisting of voltage-current pairs and determine the
resistance :math:`R`.

According to Ohm's Law, the relation between current and voltage
is linear, so a linear model can be fitted. However, Ohm's Law
only applies to an ideal resistor whose resistance does not
change, and the resistance of a real resistor tends to increase
as the resistor heats up. This means that, as the applied voltage
gets higher, the resistance changes, giving rise to
nonlinearities which are ignored by a linear model.

To get a hold on this nonlinear behavior, the model must take
the temperature of the resistor into account. Thus, the
temperature is also recorded for every data point.
The data thus consists of triples, instead of the usual "xy" pairs,
and the relationship between temperature and voltage must be
modeled in addition to the one between current and voltage.

Here, the dependence :math:`T(U)` is taken to be quadratic, with
some coefficients :math:`p_0`, :math:`p_1`, and :math:`p_2`:

.. math::

    T(U) = p_2 U^2 + p_1 U + p_0

This model is based purely on empirical observations. The :math:`I(U)`
dependence is more complicated, but takes the "running" of the
resistane with the temperature into account:

.. math::

    I(U) = \frac{U}{R_0 (1 + t \cdot \alpha_T)}

In the above, :math:`t` is the temperature in degrees Celsius,
:math:`\alpha_T` is an empirical "heat coefficient", and :math:`R_0`
is the resistance at 0 degrees Celsius, which we want to determine.

In essence, there are two models here which must be fitted to the
:math:`I(U)` and :math:`T(U)` data sets, and one model "incorporates"
the other in some way.


Approach 2: multi-model fit
---------------------------

There are several ways to achieve this with *kafe2*. The method chosen
here is to use the :py:object:`~kafe.fit.multi.Multifit` functionality
to fit both models simultaneously to the :math:`T(U)` and :math:`I(U)`
datasets.

In general, this approach yields different results than the one using
parameter constraints, which is demonstrated in the example called
``fit_with_parameter_constraints``.
"""


import numpy as np

from kafe2 import XYFit, MultiFit, Plot


# empirical model for T(U): a parabola
def empirical_T_U_model(U, p_2=1.0, p_1=1.0, p_0=1.0):
    # use quadratic model as empirical temperature dependence T(U)
    return p_2 * U**2 + p_1 * U + p_0

# model of current-voltage dependence I(U) for a heating resistor
def I_U_model(U, R_0=1., alpha=0.004, p_2=1.0, p_1=1.0, p_0=1.0):
    # use quadratic model as empirical temperature dependence T(U)
    _temperature = empirical_T_U_model(U, p_2, p_1, p_0)
    # plug the temperature into the model
    return U / (R_0 * (1.0 + _temperature * alpha))


# -- Next, read the data from an external file

# load all data into numpy arrays
U, I, T = np.loadtxt('OhmsLawExperiment.dat', unpack=True)  # data
sigU, sigI, sigT = 0.2, 0.1, 0.5  # uncertainties

T0 = 273.15  # 0 degrees C as absolute Temperature (in Kelvin)
T -= T0  # Measurements are in Kelvin, convert to °C

# -- Finally, go through the fitting procedure

# Step 1: construct the singular fit objects
fit_1 = XYFit(
    xy_data=[U, T],
    model_function="empirical_T_U_model: U p_2=1.0 p_1=1.0 p_0=1.0 -> p_2 * U^2 + p_1 * U + p_0"
)
fit_1.add_error(axis='y', err_val=sigT)  # declare errors on T
fit_1.data_container.axis_labels = ("Voltage (V)", "Temperature (°C)")
fit_1.data_container.label = "Temperature data"
fit_1.model_label = "Parametrization"

fit_2 = XYFit(
    xy_data=[U, I],
    model_function="I_U_model: U R_0 alpha=4e-3 p_2 p_1 p_0 -> U / (R_0 * (1 + alpha * (p_2 * U^2 + p_1 * U + p_0)))"
)
fit_2.add_error(axis='y', err_val=sigI)  # declare errors on I
fit_2.data_container.axis_labels = ("Voltage (V)", "Current (A)")
fit_2.data_container.label = "Current data"
fit_2.model_label = "Temperature-dependent conductance"

# Step 2: construct a MultiFit object
multi_fit = MultiFit(fit_list=[fit_1, fit_2], minimizer='iminuit')
#multi_fit.set_parameter_values(alpha=0.004)

# Step 3: Add a shared error error for the x axis.
multi_fit.add_error(axis='x', err_val=sigU, fits='all')

# (Optional): assign names for models and parameters
multi_fit.assign_parameter_latex_names(alpha=r'\alpha_\mathrm{T}')

# Step 4: do the fit
multi_fit.do_fit()

# (Optional): print the results
multi_fit.report(asymmetric_parameter_errors=True)

# (Optional): plot the results
plot = Plot(multi_fit, separate_figures=True)
plot.plot(asymmetric_parameter_errors=True)

plot.save()  # Automatically saves the plots to different files.

plot.show()
