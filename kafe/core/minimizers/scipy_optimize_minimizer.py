from kafe.core.contour import ContourFactory
try:
    import scipy.optimize as opt
except ImportError:
    # TODO: handle importing nonexistent minimizer
    raise

import numpy as np
import numdifftools as nd

class MinimizerScipyOptimizeException(Exception):
    pass

class MinimizerScipyOptimize(object):
    def __init__(self,
                 parameter_names, parameter_values, parameter_errors,
                 function_to_minimize, method="slsqp"):
        self._par_names = parameter_names
        self._par_val = parameter_values
        self._par_err = parameter_errors
        self._method = method
        self._par_bounds = None
        #self._par_bounds = [(None, None) for _pn in self._par_names]
        self._par_fixed = [False] * len(parameter_names)
        self._par_constraints = []
        """
        # for fixing:
        dict(type='eq', fun=lambda: _const, jac=lambda: 0.)
        """

        self._func_handle = function_to_minimize
        self._err_def = 1.0
        self._tol = 1e-6

        # cache for calculations
        self._hessian = None
        self._hessian_inv = None
        self._fval = None
        self._par_cov_mat = None
        self._par_cor_mat = None
        self._par_asymm_err_dn = None
        self._par_asymm_err_up = None
        self._pars_contour = None

        self._opt_result = None

    # -- private methods

    def _get_opt_result(self):
        if self._opt_result is None:
            raise MinimizerScipyOptimizeException("Cannot get requested information: No fitters performed!")
        return self._opt_result

    # -- public properties

    @property
    def errordef(self):
        return self._err_def

    @errordef.setter
    def errordef(self, err_def):
        assert err_def > 0
        self._err_def = err_def


    @property
    def tolerance(self):
        return self._tol

    @tolerance.setter
    def tolerance(self, tolerance):
        assert tolerance > 0
        self._tol = tolerance




    @property
    def hessian(self):
        # TODO: cache this
        return self._hessian_inv.I

    @property
    def cov_mat(self):
        return self._par_cov_mat

    @property
    def cor_mat(self):
        raise NotImplementedError
        return self._par_cor_mat

    @property
    def hessian_inv(self):
        return self._hessian_inv

    @property
    def function_value(self):
        if self._fval is None:
            self._fval = self._func_handle(*self.parameter_values)
        return self._fval

    @property
    def parameter_values(self):
        return self._par_val

    @property
    def parameter_errors(self):
        return self._par_err

    @property
    def parameter_names(self):
        return self._par_names

    # -- private "properties"


    # -- public methods

    def fix(self, parameter_name):
        raise NotImplementedError
        _par_id = self._par_names.index(parameter_name)
        _pv = self._par_val[_par_id]
        self._par_fixed[_par_id] = True


    def fix_several(self, parameter_names):
        for _pn in parameter_names:
            self.fix(_pn)

    def release(self, parameter_name):
        raise NotImplementedError
        _par_id = self._par_names.index(parameter_name)
        self._par_fixed[_par_id] = False

    def release_several(self, parameter_names):
        for _pn in parameter_names:
            self.release(_pn)

    def limit(self, parameter_name, parameter_bounds):
        assert len(parameter_bounds) == 2
        _par_id = self._par_names.index(parameter_name)
        if self._par_bounds is None:
            self._par_bounds = [(None, None) for _pn in self._par_names]
        self._par_bounds[_par_id] = parameter_bounds

    def unlimit(self, parameter_name):
        _par_id = self._par_names.index(parameter_name)
        self._par_bounds[_par_id] = (None, None)

    def _func_wrapper_unpack_args(self, args):
        return self._func_handle(*args)

    def minimize(self, max_calls=6000):
        self._par_constraints = []
        for _par_id, (_pf, _pv) in enumerate(zip(self._par_fixed, self._par_val)):
            if _pf:
                self._par_constraints.append(
                    dict(type='eq', fun=lambda x: x[_par_id] - _pv, jac=lambda x: 0.)
                )
                
                
        self._opt_result = opt.minimize(self._func_wrapper_unpack_args,
                                        self._par_val,
                                        args=(),
                                        method=self._method,
                                        jac=None,
                                        hess=None, hessp=None,
                                        bounds=self._par_bounds,
                                        constraints=self._par_constraints,
                                        tol=self.tolerance,
                                        callback=None,
                                        options=dict(maxiter=max_calls, disp=False))

        self._par_val = self._opt_result.x

        self._hessian_inv = np.asmatrix(nd.Hessian(self._func_wrapper_unpack_args)(self._par_val)).I

        if self._hessian_inv is not None:
            self._par_cov_mat = self._hessian_inv * 2.0 * self._err_def
            self._par_err = np.sqrt(np.diag(self._par_cov_mat))

        self._fval = self._opt_result.fun


    def contour(self, parameter_name_1, parameter_name_2, sigma=1.0, **minimizer_contour_kwargs):
        _algorithm = minimizer_contour_kwargs.pop("algorithm", "heuristic_grid")

        if _algorithm == "beacon":
            pass
        elif _algorithm == "heuristic_grid":
            _initial_points = minimizer_contour_kwargs.pop("initial_points", 1)
            _iterations = minimizer_contour_kwargs.pop("iterations", 5)
            _area_scale_factor = minimizer_contour_kwargs.pop("area_scale_factor", 1.5)
        else:
            raise MinimizerScipyOptimizeException("Unknown algorithm: {}".format(_algorithm))
        
        if minimizer_contour_kwargs:
            raise MinimizerScipyOptimizeException("Unknown parameters for {}: {}".format(_algorithm, minimizer_contour_kwargs.keys()))
        
        if _algorithm == "beacon":
            return self._contour_beacon(parameter_name_1, parameter_name_2, sigma=sigma)
        elif _algorithm == "heuristic_grid":
            return self._contour_heuristic_grid(parameter_name_1, parameter_name_2, sigma=sigma, 
                                                initial_points=_initial_points, iterations=_iterations,
                                                area_scale_factor=_area_scale_factor)

    def _contour_old(self, parameter_name_1, parameter_name_2, sigma=1.0, numpoints = 20, strategy=1):
        if strategy == 0:
            _fraction = 0.08
            _bias = 0.1
        elif strategy == 1:
            _fraction = 0.04
            _bias = 1
        elif strategy == 2:
            _fraction = 0.01
            _bias = 1
            
        _contour_fun = self.function_value + sigma ** 2
        _ids = (self._par_names.index(parameter_name_1), self._par_names.index(parameter_name_2))
        _minimum = np.asarray([self._par_val[_ids[0]], self._par_val[_ids[1]]])
        _coords = (0, 0)
        _x_err, _y_err = self._par_err[_ids[0]], self._par_err[_ids[1]]
        step_1, step_2 = _x_err * _fraction, _y_err * _fraction
        _x_vector = np.asarray([step_1, 0])
        _y_vector = np.asarray([0, step_2])
        _steps = np.asarray([[0, step_2], [step_1, 0], [0, -step_2], [-step_1, 0]])
        _fun_distance = sigma ** 2
        _adjacent_funs = np.zeros(4)
        _last_direction = -1
        
        _contour_coords = []
        _explored_coords = set()
        _explored_coords.add((0,0))
        _log_points = False
        _termination_coords = None
        _first_lap = True

        _loops = 0
        
        while True:
            if _coords == _termination_coords:
                if not _first_lap:
                    break
                else:
                    _first_lap = False
            _adjacent_coords = self._get_adjacent_coords(_coords)
            for i in range(4):
                if _adjacent_coords[i] in _explored_coords or i == _last_direction:
                    _adjacent_funs[i] = 0
                elif _adjacent_coords[i] == _termination_coords:
                    _adjacent_funs[i] = _contour_fun
                else:
                    _point = _minimum + _adjacent_coords[i][0] * _x_vector + _adjacent_coords[i][1] * _y_vector
                    _local_constraints = [{'type' : 'eq', 'fun' : lambda x: x[_ids[0]] - _point[0]},
                                          {'type' : 'eq', 'fun' : lambda x: x[_ids[1]] - _point[1]}]
                    _adjacent_funs[i] = self._calc_fun_with_constraints(_local_constraints)
            _distances = _contour_fun - _adjacent_funs
            for i in range(4):
                if _distances[i] < 0:
                    _distances[i] *= -_bias
            _adjacent_funs_best_distance = np.min(_distances)
            _min_index = np.argmin(_distances)
            _new_coords = _adjacent_coords[_min_index]
            
            for i in range(4):
                if i != _last_direction:
                    _explored_coords.add(_adjacent_coords[i])
            if _fun_distance < _adjacent_funs_best_distance and not _log_points:
                _log_points = True
                _termination_coords = _new_coords
                _explored_coords.clear()
            _coords = _new_coords
            _fun_distance = _adjacent_funs_best_distance
            _last_direction = (np.argmin(_distances) + 2) % 4
            if _log_points:
                _contour_coords.append(_coords)
            if _loops < 10000:
                _loops += 1
            else:
                break 
        _contour_array = np.asarray(_contour_coords, dtype=float).T
        _contour_array[0] = _contour_array[0] * step_1 + _minimum[0]
        _contour_array[1] = _contour_array[1] * step_2 + _minimum[1]
        #function call needed to reset the nexus cache to minimal values
        self._func_wrapper_unpack_args(self._par_val)
        return _contour_array
    
    def _contour_heuristic_grid(self, parameter_name_1, parameter_name_2, sigma=1.0, initial_points=1,
                                iterations=5, area_scale_factor=1.5):
        initial_points = int(initial_points)
        iterations = int(iterations)

        if initial_points < 1:
            raise MinimizerScipyOptimize("initial_points must be a >= 1")
        if iterations < 0:
            raise MinimizerScipyOptimize("iterations must be a >= 0")
        
        _initial_points_per_axis = 1 + initial_points * 2
        _target_points_per_axis = 1 + initial_points * 2 ** (iterations + 1)
        _ids = (self._par_names.index(parameter_name_1), self._par_names.index(parameter_name_2))
        _minimum = np.asarray([self._par_val[_ids[0]], self._par_val[_ids[1]]])
        _err = np.asarray([self._par_err[_ids[0]], self._par_err[_ids[1]]])

        _x_values = np.linspace(start=-area_scale_factor * sigma * _err[0], stop=area_scale_factor * sigma * _err[0], num=_target_points_per_axis, endpoint = True)
        _x_values += _minimum[0]
        _y_values = np.linspace(start=-area_scale_factor * sigma * _err[1], stop=area_scale_factor * sigma * _err[1], num=_target_points_per_axis, endpoint = True)
        _y_values += _minimum[1]

        _grid = np.zeros((_target_points_per_axis, _target_points_per_axis)) - 1
        _x_step = (_target_points_per_axis - 1) / (_initial_points_per_axis - 1)
        _y_step = (_target_points_per_axis - 1) / (_initial_points_per_axis - 1)

        _min_coords = (_target_points_per_axis - 1) / 2
        _confirmed_coords = set()
        _unsure_coords = set()

        for _x in range(0, _target_points_per_axis, _x_step):
            for _y in range(0, _target_points_per_axis, _y_step):
                    _local_constraints = [{'type' : 'eq', 'fun' : lambda x: x[_ids[0]] - _x_values[_x]},
                                          {'type' : 'eq', 'fun' : lambda x: x[_ids[1]] - _y_values[_y]}]
                    _grid[_x,_y] = self._calc_fun_with_constraints(_local_constraints)

        
        _min_fun = min(self.function_value, _grid[_min_coords,_min_coords])
        _contour_fun = _min_fun + sigma ** 2

        _iterations = 0
        while _x_step > 0 and _y_step > 1:
            if _iterations % 2 == 0:
                _x_0 = _x_step / 2
                _y_0 = _y_step / 2
                _vector_1 = (_x_step / 2, _y_step / 2)
                _vector_2 = (_x_step / 2, -_y_step / 2)
            else:
                _x_0 = 0
                _y_0 = 0
                _vector_1 = (_x_step, 0)
                _vector_2 = (0, _y_step / 2)
                
            for _x in range(_x_0, _target_points_per_axis, _x_step):
                if _iterations % 2 == 1 and _x % (2 * _x_step) == 0:
                    _current_y_0 = _y_0 + _y_step / 2
                else:
                    _current_y_0 = _y_0
                for _y in range(_current_y_0, _target_points_per_axis, _y_step):
                    _point_value = self._heuristic_point_evaluation(_contour_fun, _grid, _x, _y, _vector_1, _vector_2)
                    if _point_value == -1:
                        _local_constraints = [{'type' : 'eq', 'fun' : lambda x: x[_ids[0]] - _x_values[_x]},
                                              {'type' : 'eq', 'fun' : lambda x: x[_ids[1]] - _y_values[_y]}]
                        _grid[_x, _y] = self._calc_fun_with_constraints(_local_constraints)
                        _confirmed_coords.add((_x,_y))
                        if _iterations % 2 == 0:
                            _unsure_coords.add((_x - _x_step,   _y))
                            _unsure_coords.add((_x,             _y - _y_step))
                            _unsure_coords.add((_x + _x_step,   _y))
                            _unsure_coords.add((_x,             _y + _y_step))
                        else:
                            _unsure_coords.add((_x - _x_step, _y - _y_step / 2))
                            _unsure_coords.add((_x - _x_step, _y + _y_step / 2))
                            _unsure_coords.add((_x + _x_step, _y - _y_step / 2))
                            _unsure_coords.add((_x + _x_step, _y + _y_step / 2))
                    else:
                        _grid[_x, _y] = _point_value
            
            while _unsure_coords:
                _current_coords = _unsure_coords.pop()
                if (_current_coords[0] < 0 or _current_coords[0] >= _target_points_per_axis or 
                    _current_coords[1] < 0 or _current_coords[1] >= _target_points_per_axis):
                    continue
                if _current_coords in _confirmed_coords:
                    continue
                _x = _current_coords[0]
                _y = _current_coords[1]
                _local_constraints = [{'type' : 'eq', 'fun' : lambda x: x[_ids[0]] - _x_values[_x]},
                                      {'type' : 'eq', 'fun' : lambda x: x[_ids[1]] - _y_values[_y]}]
                _current_fun = self._calc_fun_with_constraints(_local_constraints)
                _grid_fun = _grid[_current_coords[0], _current_coords[1]]
                if ((_current_fun > _contour_fun and _grid_fun < _contour_fun) or
                    (_current_fun < _contour_fun and _grid_fun > _contour_fun)):
                        if _iterations % 2 == 0:
                            _unsure_coords.add((_x - _x_step,   _y))
                            _unsure_coords.add((_x,             _y - _y_step))
                            _unsure_coords.add((_x + _x_step,   _y))
                            _unsure_coords.add((_x,             _y + _y_step))
                        else:
                            _unsure_coords.add((_x - _x_step, _y - _y_step / 2))
                            _unsure_coords.add((_x - _x_step, _y + _y_step / 2))
                            _unsure_coords.add((_x + _x_step, _y - _y_step / 2))
                            _unsure_coords.add((_x + _x_step, _y + _y_step / 2))
                _grid[_current_coords[0], _current_coords[1]] = _current_fun
                _confirmed_coords.add(_current_coords)
                
            if _iterations % 2 == 0:
                _x_step /= 2
            else:
                _y_step /= 2
            _iterations += 1
            
        _left_cutoff = 0
        _right_cutoff = _target_points_per_axis - 1
        _bottom_cutoff = 0
        _top_cutoff = _target_points_per_axis - 1
        _padding = int(3 / area_scale_factor * max(1, 2 ** (iterations - 4)))

        while _right_cutoff > 0 and np.min(_grid[_right_cutoff]) > _contour_fun:
            _right_cutoff -= 1
        _right_cutoff += _padding
        _right_cutoff = min(_right_cutoff, _target_points_per_axis - 1)
        
        while _left_cutoff < _right_cutoff and np.min(_grid[_left_cutoff]) > _contour_fun:
            _left_cutoff += 1
        _left_cutoff -= _padding
        _left_cutoff = max(_left_cutoff, 0)
        
        _grid = _grid[_left_cutoff:_right_cutoff]
        _grid = _grid.T
        
        while _top_cutoff > 0 and np.min(_grid[_top_cutoff]) > _contour_fun:
            _top_cutoff -= 1
        _top_cutoff += _padding
        _top_cutoff = min(_top_cutoff, _target_points_per_axis - 1)
        
        while _bottom_cutoff < _top_cutoff and np.min(_grid[_bottom_cutoff]) > _contour_fun:
            _bottom_cutoff += 1
        _bottom_cutoff -= _padding
        _bottom_cutoff = max(_bottom_cutoff, 0)
        
        _grid=_grid[_bottom_cutoff:_top_cutoff]
        _grid = _grid.T
            
        _x_values = _x_values[_left_cutoff:_right_cutoff]
        _y_values = _y_values[_bottom_cutoff:_top_cutoff]
        
        _grid = np.sqrt(_grid - _min_fun)
        self._func_wrapper_unpack_args(self._par_val)
        return ContourFactory.create_grid_contour(_x_values, _y_values, _grid, sigma)
    
    @staticmethod
    def _heuristic_point_evaluation(contour_fun, grid, x, y, vector_1, vector_2):
        _adjacent_points = MinimizerScipyOptimize._get_adjacent_grid_points(grid, x, y, vector_1, vector_2)
        if np.max(_adjacent_points) < contour_fun:
            return np.mean(_adjacent_points)
        if np.min(_adjacent_points) > contour_fun:
            return np.mean(_adjacent_points)
        return -1
    
    
    @staticmethod
    def _get_adjacent_grid_points(grid, x_0, y_0, vector_1, vector_2):
        _x_size = np.ma.size(grid, 0)
        _y_size = np.ma.size(grid, 1)
        _grid_points = []
        for i in range(4):
            _x = x_0
            _y = y_0
            if i == 0:
                _x -= vector_1[0]
                _y -= vector_1[1]
            elif i == 1:
                _x -= vector_2[0]
                _y -= vector_2[1]
            elif i == 2:
                _x += vector_1[0]
                _y += vector_1[1]
            elif i == 3:
                _x += vector_2[0]
                _y += vector_2[1]
            if _x >= 0 and _x < _x_size and _y >= 0 and _y < _y_size:
                _grid_points.append(grid[_x][_y])
        return np.asarray(_grid_points)
    
    def _get_adjacent_coords(self, central_coords):
        return [(central_coords[0], central_coords[1] + 1),
                (central_coords[0] + 1, central_coords[1]),
                (central_coords[0], central_coords[1] - 1),
                (central_coords[0] - 1, central_coords[1])]

    def _contour_beacon(self, parameter_name_1, parameter_name_2, sigma=1.0, beacon_size=0.02):
            
        _contour_fun = self.function_value + sigma ** 2
        _contour_fun_upper_tolerance = self.function_value + (1.2 * sigma) ** 2
        _contour_fun_lower_tolerance = self.function_value + (0.8 * sigma) ** 2
        _ids = (self._par_names.index(parameter_name_1), self._par_names.index(parameter_name_2))
        _minimum = np.asarray([self._par_val[_ids[0]], self._par_val[_ids[1]]])
        _err = np.asarray([self._par_err[_ids[0]], self._par_err[_ids[1]]])
        
        _angles = []

        CONTOUR_ELLIPSE_POINTS = 21
        CONTOUR_STRETCHING = 4.0
        _unstretched_angles = np.linspace(-np.pi/2, np.pi/2, CONTOUR_ELLIPSE_POINTS, endpoint=True)
        _contour_search_ellipse = np.empty((2, CONTOUR_ELLIPSE_POINTS))
        _contour_search_ellipse[0] = sigma * beacon_size * np.sin(_unstretched_angles)
        _contour_search_ellipse[1] = sigma * CONTOUR_STRETCHING * beacon_size * np.cos(_unstretched_angles)
        _stretched_absolute_angles = np.abs(np.arctan(np.tan(_unstretched_angles) / CONTOUR_STRETCHING))
        _curvature_adjustion_factors = 1 + 0.025 * (10 - _stretched_absolute_angles * 180 / np.pi)
        _curvature_adjustion_factors = np.where(_curvature_adjustion_factors >= 0.25, _curvature_adjustion_factors, 0.25)
        
        _termination_distance = (sigma * CONTOUR_STRETCHING * beacon_size) ** 2
        
        _meta_cost_function = lambda z: (_contour_fun - self._calc_fun_with_constraints([{'type' : 'eq', 'fun' : lambda x: x[_ids[0]] - (_minimum[0] + _err[0] * z)},
                                                                                         {'type' : 'eq', 'fun' : lambda x: x[_ids[1]] - _minimum[1]}]))


        
        _start_x = opt.brentq(_meta_cost_function, 0, 2 * sigma, maxiter=1000)
        _start_point = np.asarray([_start_x, 0.0])
        
        _phi = self._calculate_tangential_angle(_start_point, _ids)
        _coords = _start_point
        _curvature_adjustion = 1.0
        _last_backtrack = 0

        _loops = 0
        
        _contour_coords = [_start_point]
        
        while(True):
            _transformed_search_ellipse = self._rotate_clockwise(_contour_search_ellipse * _curvature_adjustion, _phi)
            _transformed_search_ellipse[0] += _coords[0]
            _transformed_search_ellipse[1] += _coords[1]
            _transformed_search_ellipse = _transformed_search_ellipse.T
            _ellipse_fun_values = np.empty(CONTOUR_ELLIPSE_POINTS)
            for i in range(CONTOUR_ELLIPSE_POINTS):
                _ellipse_coords = _transformed_search_ellipse[i]
                _transformed_coords = self._transform_coordinates(_minimum, _ellipse_coords, _err)
                _point_constraints = [{"type" : "eq", "fun" : lambda x: x[_ids[0]] - _transformed_coords[0]},
                                      {"type" : "eq", "fun" : lambda x: x[_ids[1]] - _transformed_coords[1]}]
                _ellipse_fun_values[i] = self._calc_fun_with_constraints(_point_constraints)
            _min_index = np.argmin(np.abs(_ellipse_fun_values - _contour_fun))
            _new_coords = _transformed_search_ellipse[_min_index]

            _curvature_adjustion *= _curvature_adjustion_factors[_min_index]
            if _curvature_adjustion > 1.0:
                _curvature_adjustion = 1.0

            
            if _stretched_absolute_angles[_min_index] > 0.349111:
                print "BACKTRACK"
                _contour_coords = _contour_coords[0:-1]
            else:
                _contour_coords.append(_new_coords)
            
#             _delta = _contour_coords[-1] - _contour_coords[-2]
#             _phi = np.arctan2(_delta[0], _delta[1])
            _coords = _contour_coords[-1]
            _phi = self._calculate_tangential_angle(_coords, _ids)
            
            if np.sum((_coords - _start_point) ** 2) < _termination_distance and _loops > 10:
                break
            
            if _loops < 200:
                _loops += 1
            else:
                break
        self._func_wrapper_unpack_args(self._par_val)
        return ContourFactory.create_xy_contour(self._transform_contour(_minimum, _contour_coords, _err), sigma)
    
    @staticmethod
    def _transform_coordinates(minimum, sigma_coordinates, errors):
        return minimum + sigma_coordinates * errors
    
    @staticmethod
    def _transform_contour(minimum, sigma_contour, errors):
        _transformed_contour = []
        for _coords in sigma_contour:
            _transformed_contour.append(MinimizerScipyOptimize._transform_coordinates(minimum, _coords, errors))
        return _transformed_contour
        
    @staticmethod
    def _rotate_clockwise(xy_values, phi):
        _rotated_xy_values = np.empty(shape=xy_values.shape)
        _rotated_xy_values[0] =  np.cos(phi) * xy_values[0] + np.sin(phi) * xy_values[1]
        _rotated_xy_values[1] = -np.sin(phi) * xy_values[0] + np.cos(phi) * xy_values[1]
        return _rotated_xy_values
    
    def _calculate_tangential_angle(self, coords, ids):
        _meta_cost_function_gradient = lambda pars: self._calc_fun_with_constraints([{'type' : 'eq', 'fun' : lambda x: x[ids[0]] - (self._par_val[ids[0]] + self._par_err[ids[0]] * pars[0])},
                                                                                     {'type' : 'eq', 'fun' : lambda x: x[ids[1]] - (self._par_val[ids[1]] + self._par_err[ids[1]] * pars[1])}])
        _grad = nd.Gradient(_meta_cost_function_gradient)(coords)
        return np.arctan2(_grad[0], _grad[1]) + np.pi / 2

    def _calc_fun_with_constraints(self, additional_constraints):
        _local_constraints = self._par_constraints + additional_constraints
        _result = opt.minimize(self._func_wrapper_unpack_args,
                                        self._par_val,
                                        args=(),
                                        method="slsqp",
                                        jac=None,
                                        bounds=self._par_bounds,
                                        constraints=_local_constraints,
                                        tol=self.tolerance,
                                        callback=None,
                                        options=dict(maxiter=6000, disp=False))
        return _result.fun
        
    def profile(self, parameter_name, bins=21, bound=2, args=None, subtract_min=False):
        _par_id = self._par_names.index(parameter_name)
        _par_err = self._par_err[_par_id]
        _par_min = self._par_val[_par_id]
        _par = np.linspace(start=_par_min - bound * _par_err, stop=_par_min + bound * _par_err, num=bins, endpoint=True)
        _y_offset = self.function_value if subtract_min else 0
        
        _y = np.empty(bins)
        for i in range(bins):
            _y[i] = self._calc_fun_with_constraints([{"type" : "eq", "fun" : lambda x: x[_par_id] - _par[i]}])
        self._func_wrapper_unpack_args(self._par_val)
        return np.asarray([_par, _y])