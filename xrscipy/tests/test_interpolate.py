from __future__ import absolute_import, division, print_function

import numpy as np
import scipy as sp
import pytest

import xarray as xr

from xrscipy import interpolate
from .testings import get_obj


@pytest.mark.parametrize('mode', [0, 1])
@pytest.mark.parametrize('func', ['interp1d', 'PchipInterpolator',
                                  'Akima1DInterpolator', 'CubicSpline'])
@pytest.mark.parametrize('coord', ['x', 'time'])
def test_interpolate1d(mode, func, coord):
    da = get_obj(mode)
    new_x = np.linspace(1, 8, 13) * 0.1

    axis = da.get_axis_num(da[coord].dims[0])
    actual = getattr(interpolate, func)(da, coord)(new_x)
    expected = getattr(sp.interpolate, func)(x=da[coord].values, y=da.values,
                                             axis=axis)(new_x)
    assert (actual.values == expected).all()

    # make sure the original data does not change
    da.values.ndim == get_obj(mode).ndim

    # make sure the coordinate is propagated
    for key, v in da.coords.items():
        assert key in actual.coords
        if 'x' not in v.dims:
            assert da[key].identical(actual[key])


@pytest.mark.parametrize('coord', ['x', 'time'])
def test_interpolate1d_dataset(coord):
    ds = get_obj(mode=3)
    new_x = np.linspace(1, 8, 13) * 0.1

    actual = interpolate.interp1d(ds, coord=coord)
    expected = interpolate.interp1d(ds['a'], coord=coord)
    assert (actual['a'](new_x).identical(expected(new_x)))
    assert (actual(new_x)['a'].identical(expected(new_x)))

    # make sure the coordinate is propagated
    for key, v in ds.coords.items():
        assert key in actual.coords
        if 'x' not in v.dims:
            assert ds[key].identical(actual(new_x)[key])

    # make sure the coordinate is propagated
    interped = actual(new_x)
    for key, v in ds.coords.items():
        assert key in interped.coords
        if 'x' not in v.dims:
            assert ds[key].identical(interped[key])


def get_obj_for_interp(mode):
    # These examples are taken from
    # https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.griddata.html  # noqa

    pi4 = 4 * np.pi

    def func1(x, y):
        return x * (1 - x)*np.cos(pi4 * x) * np.sin(pi4 * y**2)**2

    def func2(x, y):
        return x * (1 - x)*np.cos(pi4 * x**2) * np.sin(pi4 * y)**2

    x = np.random.rand(100)
    y = np.random.rand(100)

    if mode in [0, 1]:
        da = xr.DataArray(func1(x, y), dims=['a'],
                          coords={'x': ('a', x), 'y': ('a', y)})
        if mode == 0:
            grid_x, grid_y = np.mgrid[0:1:100j, 0:1:200j]
            grid_x_da = xr.DataArray(grid_x, dims=['b', 'c'], name='xx')
            grid_y_da = xr.DataArray(grid_y, dims=['b', 'c'])
        else:  # mode 1
            grid = np.linspace(0, 1, 200)
            grid_x_da = xr.DataArray(grid, dims=['b'], name='xx')
            grid_y_da = xr.DataArray(grid, dims=['c'])
        return da, (grid_x_da, grid_y_da)

    elif mode == 2:
        da = xr.DataArray(func1(x, 0.2), dims=['a'], coords={'x': ('a', x)})
        grid_x_da = xr.DataArray(np.linspace(0, 1, 200), dims=['b'], name='xx')
        return da, (grid_x_da, )

    elif mode == 3:
        values = np.stack([func1(x, y), func2(x, y)], axis=0)
        da = xr.DataArray(values, dims=['e', 'a'],
                          coords={'x': ('a', x), 'y': ('a', y)})
        grid = np.linspace(0, 1, 200)
        grid_x_da = xr.DataArray(grid, dims=['b'], name='xx')
        grid_y_da = xr.DataArray(grid, dims=['c'])
        return da, (grid_x_da, grid_y_da)


@pytest.mark.parametrize('mode', [0, 1, 2, 3])
def test_griddata(mode):
    obj, grid_das = get_obj_for_interp(mode)

    if len(grid_das) == 2:
        actual = interpolate.griddata(obj, ('x', 'y'), grid_das)
        points = np.stack([obj['x'], obj['y']], axis=-1)
    elif len(grid_das) == 1:
        actual = interpolate.griddata(obj, ('x', ), grid_das)
        points = np.stack([obj['x'], ], axis=-1)

    # points
    xi = np.stack(xr.broadcast(*grid_das), axis=-1)

    if mode == 3:
        expected = np.stack([sp.interpolate.griddata(points, v, xi)
                             for v in obj.values], axis=0)
    else:
        expected = sp.interpolate.griddata(points, obj.values, xi)

    if len(grid_das) == 1:
        expected = np.squeeze(expected, axis=-1)
    assert np.allclose(actual.values, expected, equal_nan=True)

    if mode == 1:
        assert actual['xx'].ndim == 1
        assert actual['y'].ndim == 1

    for d in ['_points', '_points2', 'a', 'b', 'c']:
        assert d not in list(actual.coords)
