import numpy as np

_fit_history = []


def xy_fit(x_data, y_data, model_function=None, p0=None, dp0=None,
           x_error=None, y_error=None, x_error_rel=None, y_error_rel=None,
           x_error_cor=None, y_error_cor=None, x_error_cor_rel=None, y_error_cor_rel=None,
           limits=None, constraints=None, report=True, profile=None):
    from kafe2.fit.xy.fit import XYFit

    if model_function is None:
        _fit = XYFit([x_data, y_data])
    else:
        _fit = XYFit([x_data, y_data], model_function)
    if p0 is not None:
        _fit.set_all_parameter_values(p0)
    if dp0 is not None:
        _fit.parameter_errors = dp0

    def _add_error_to_fit(axis, error, correlated=False, relative=False):
        if error is None:
            return
        error = np.asarray(error)
        _reference = "model" if axis == "y" and relative else "data"
        if correlated:
            if error.ndim == 0:
                error = np.reshape(error, (1,))
            for _err in error:
                _fit.add_error(axis, _err, correlation=1.0, reference=_reference)
        else:
            if error.ndim == 2:
                _fit.add_matrix_error(axis, error, "cov", relative=relative, reference=_reference)
            else:
                _fit.add_error(axis, error, relative=relative, reference=_reference)

    _add_error_to_fit("x", x_error)
    _add_error_to_fit("y", y_error)
    _add_error_to_fit("x", x_error_rel, relative=True)
    _add_error_to_fit("y", y_error_rel, relative=True)
    _add_error_to_fit("x", x_error_cor, correlated=True)
    _add_error_to_fit("y", y_error_cor, correlated=True)
    _add_error_to_fit("x", x_error_cor_rel, correlated=True, relative=True)
    _add_error_to_fit("y", y_error_cor_rel, correlated=True, relative=True)

    if limits is not None:
        if not isinstance(limits[0], (list, tuple)):
            limits = (limits,)
        for _limit in limits:
            _fit.limit_parameter(*_limit)
    if constraints is not None:
        if not isinstance(constraints[0], (list, tuple)):
            constraints = (constraints,)
        for _constraint in constraints:
            _fit.add_parameter_constraint(*_constraint)

    if profile is None:
        profile = x_error is not None or x_error_rel is not None or y_error_rel is not None

    _fit.do_fit(asymmetric_parameter_errors=profile)
    if report:
        _fit.report(asymmetric_parameter_errors=profile)
    _fit_history.append(dict(fit=_fit, profile=profile))


def plot(fits=-1, x_label=None, y_label=None, data_label=None, model_label=None,
         error_band_label=None, model_name=None, model_expression=None, legend=True, fit_info=True,
         error_band=True, profile=None, plot_profile=None, show=True):
    from kafe2 import Plot, ContoursProfiler
    if isinstance(fits, int):
        if fits >= 0:
            fit_profiles = [_fit_history[fits]["profile"]]
            fits = [_fit_history[fits]["fit"]]
        else:
            fits = _fit_history[fits:]
            fit_profiles = [_f["profile"] for _f in fits]
            fits = [_f["fit"] for _f in fits]
    if model_name is not None:
        fits[0].assign_model_function_latex_name(model_name)
    if model_expression is not None:
        fits[0].assign_model_function_latex_expression(model_expression)
    _plot = Plot(fits[0])
    if x_label is not None:
        _plot.x_label = x_label
    if y_label is not None:
        _plot.y_label = y_label
    if data_label is not None:
        _plot.customize("data", "label", [data_label])
    if model_label is not None:
        _plot.customize("model_line", "label", [model_label])
    if error_band_label is not None:
        _plot.customize("model_error_band", "label", [error_band_label])
    if not error_band:
        _plot.customize("model_error_band", "label", [None])
        _plot.customize("model_error_band", "hide", [True])

    if profile is None:
        profile = fit_profiles[0]
    _plot.plot(legend=legend, fit_info=fit_info, asymmetric_parameter_errors=profile)

    if plot_profile is None:
        plot_profile = fit_profiles[0]
    if plot_profile:
        _cpf = ContoursProfiler(fits[0])
        _cpf.plot_profiles_contours_matrix()
    if show:
        _plot.show()
