#!/usr/bin/env python3lkij
# -*- coding: utf-8 -*-

"""
Copyright 2019 Lukas Brunner, ETH Zurich

This file is part of ClimWIP.

ClimWIP is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

Authors
-------
- Lukas Brunner || lukas.brunner@env.ethz.ch

Abstract
--------
A collection of plot routines for quick checking of the output.
"""
import matplotlib as mpl
mpl.use('Agg')
import os
import logging
import numpy as np
import matplotlib.pyplot as plt
import cartopy
import cartopy.crs as ccrs
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter

# matplotlib bug; issue 1120
# https://github.com/SciTools/cartopy/issues/1120
from matplotlib.axes import Axes
from cartopy.mpl.geoaxes import GeoAxes
GeoAxes._pcolormesh_patched = Axes.pcolormesh

logger = logging.getLogger(__name__)


def plot_rmse(da, idx, cfg, what, min_=None, max_=None):
    """Matrix plot of RMSEs for a given diagnostic.

    Parameters
    ----------
    da : xarray.DataArray, shape (N, N)
        Has to contain the RMSE from each model to each model
    varn : string
        A string for naming the plot (normally the name of the diagnostic)
    cfg : object
        Config object
    """
    path = os.path.join(cfg.plot_path, cfg.config)
    os.makedirs(path, exist_ok=True)

    if what == 'performance':
        fig, ax = plt.subplots(figsize=(5, 20))
        ax.set_ylabel('Model')
        data = da.data.reshape(-1, 1)
        xx = ['Observations']
        yy = da['model_ensemble'].data

    elif what == 'independence':
        fig, ax = plt.subplots(figsize=(20, 20))
        fig.subplots_adjust(right=.97, bottom=.02, left=.15, top=.85)
        ax.set_xlabel('"Perfect" Model')
        ax.set_ylabel('Model')
        data = da.data
        # data = np.tril(da.data)
        # data[data == 0] = np.nan
        xx = da['model_ensemble'].data
        yy = xx

    p25, p75 = np.nanpercentile(data, (10, 90))

    if isinstance(idx, int):  # single diagnostics
        if what == 'performance':
            diagn = f'{cfg.performance_diagnostics[idx]}{cfg.performance_aggs[idx]}'
            period = f'{cfg.performance_startyears[idx]}-{cfg.performance_endyears[idx]}'
        elif what == 'independence':
            diagn = f'{cfg.independence_diagnostics[idx]}{cfg.independence_aggs[idx]}'
            period = f'{cfg.independence_startyears[idx]}-{cfg.independence_endyears[idx]}'
        title = 'Normalized {} RMSE {} {}; 50% range ({:.2f}-{:.2f})'.format(what, diagn, period, p25, p75)
        filename = 'rmse_{}_{}'.format(what, diagn)
    else:  # mean diagnostic
        title = 'Mean RMSE all diagnostics; 50% range ({:.2f}-{:.2f})'.format(p25, p75)
        filename = 'rmse_{}_mean'.format(what)

    if max_ is None:
        max_ = np.nanpercentile(data, 95)
    if min_ is None:
        min_ = np.nanpercentile(data, 5)

    im = ax.matshow(data, vmin=min_, vmax=max_)

    ax.set_xticks(np.arange(len(xx)))
    ax.set_yticks(np.arange(len(yy)))
    ax.set_xticklabels(xx)
    plt.xticks(rotation=90)
    ax.set_yticklabels(yy)
    ax.set_ylim(len(yy)-.5, -.5)
    ax.set_title(title, fontsize='xx-large', pad=150)

    fig.colorbar(im, ax=ax, fraction=.046, pad=.04)

    filename = os.path.join(path, filename)
    plt.savefig(filename, dpi=300)
    plt.clf()
    logger.debug('Saved plot: {}.png'.format(filename))


def plot_fraction_matrix(xx, yy, data, cfg, idx=None, title=''):
    """Matrix plot of the perfect model test result.

    Parameters
    ----------
    xx : array_like, shape (N,)
    yy : array_like, shape (M,)
    data : array_like, shape (M, N)
    cfg : object
    idx : tuple of two int
        idx gives the position of the selected sigma values as dot
    title : string, optional
    """
    boundaries = np.arange(.7, 1.01, .02)
    cmap = plt.cm.get_cmap('viridis', len(boundaries))
    colors = list(cmap(np.arange(len(boundaries))))
    cmap = mpl.colors.ListedColormap(colors, "")

    fig, ax = plt.subplots(figsize=(8, 8))

    im = ax.matshow(
        data+1.e-10,  # hack to include lower bounds
        cmap=cmap,
        norm=mpl.colors.BoundaryNorm(
            boundaries,
            ncolors=len(boundaries)-1,
            clip=False))

    ax.set_xticks(np.arange(len(xx)))
    ax.set_yticks(np.arange(len(yy)))
    ax.set_xticklabels(['{:.2f}'.format(x) for x in xx])
    plt.xticks(rotation=90)
    ax.set_yticklabels(['{:.2f}'.format(y) for y in yy])
    ax.set_xlabel('Independence parameter $\sigma_{i}$', fontsize='large')
    ax.set_ylabel('Performance parameter $\sigma_{q}$', fontsize='large')

    if idx is not None:
        ax.scatter(idx[0], idx[1], s=1, color='k')

    ax.set_title(title, fontsize='x-large', pad=20)

    fig.colorbar(im, ax=ax, fraction=.046, pad=.04)

    path = os.path.join(cfg.plot_path, cfg.config)
    os.makedirs(path, exist_ok=True)
    filename = os.path.join(path, 'inside_ratio.png')
    plt.savefig(filename, dpi=300)
    plt.clf()
    logger.debug('Saved plot: {}'.format(filename))
    return filename


def plot_maps(ds, idx, cfg):
    """Mapplot of a given diagnostic and each model.

    Parameters
    ----------
    ds : xarray.DataArray
        Has to contain the varn and the dimensions 'lat', 'lon', and
        'model_ensemble'
    idx : int
        Index of the predictor
    cfg : object
        Config object
    """
    agg = cfg.performance_aggs[idx]
    syear = cfg.performance_startyears[idx]
    eyear = cfg.performance_endyears[idx]

    path = os.path.join(cfg.plot_path, cfg.config, 'maps')
    os.makedirs(path, exist_ok=True)

    if 'month' in ds.dims:
        ds = ds.sum('month')

    for model_ensemble in ds['model_ensemble'].data:
        proj = ccrs.PlateCarree(central_longitude=0)
        fig, ax = plt.subplots(subplot_kw={'projection': proj})
        ds_sel = ds.sel(model_ensemble=model_ensemble).copy(deep=True)
        ds_sel.data[ds_sel.data == 0] = np.nan  # hack to set 0 distance to white
        cbar = ds_sel.plot.pcolormesh(
            ax=ax,
            transform=ccrs.PlateCarree(),
            center=0,
            levels=9,
            robust=True,
            # vmax=160,
            extend='both',
            cbar_kwargs={'orientation': 'horizontal',
                         'pad': .1})
        cbar.cmap.set_bad('white')  # set 0 distance to white
        ax.coastlines()
        ax.add_feature(cartopy.feature.BORDERS)
        xx, yy = np.meshgrid(ds['lon'].data[1:-1], ds['lat'].data[1:-1])
        if not (cfg.performance_regions[idx] == 'GLOBAL' or cfg.performance_masks[idx]):
            ax.scatter(xx, yy, s=1, color='k')

        # longitude_formatter = LongitudeFormatter()
        # latitude_formatter = LatitudeFormatter()
        # ax.set_xticks(np.arange(ds['lon'].min()-5, ds['lon'].max()+11, 10), crs=proj)
        # ax.set_yticks(np.arange(ds['lat'].min()-5, ds['lat'].max()+11, 10), crs=proj)
        # ax.xaxis.set_ticks_position('both')
        # ax.yaxis.set_ticks_position('both')
        # ax.xaxis.set_major_formatter(longitude_formatter)
        # ax.yaxis.set_major_formatter(latitude_formatter)
        ax.set_xlabel('')
        ax.set_ylabel('')

        ax.set_title('{}: {}{} {}-{}'.format(model_ensemble, ds.name, agg, syear, eyear))

        filename = os.path.join(path, 'map_{}-{}_{}'.format(ds.name, agg, model_ensemble))
        plt.savefig(filename + '.png', dpi=300)
        plt.close()
        logger.debug('Saved plot: {}.png'.format(filename))


def plot_weights(ds, cfg, sort_by='name'):
    """Lineplot of weights per model.

    Parameters
    ----------
    ds : xarray.Dataset
        Has to contain the 'weights' variable (shape (N,)) depending on the
        'model_ensemble' dimension.
    cfg : model_weighting.config object
    nn : array_like, shape (N,)
        Array of performance weights (numerator in weights equation)
    dd : array_like, shape (N,)
        Array of independence weights (denominator in weights equation)
    sort_by : string, optional
        name: plot models alphabetically and cluster ensemble members.
        weights: plot models by weight (highest first)
        performance: plot models by performance weight (highest first)
        independence: plot models by independence weight (highest first)
    """

    path = os.path.join(cfg.plot_path, cfg.config)
    os.makedirs(path, exist_ok=True)

    fig, ax = plt.subplots(figsize=(18, 12))
    fig.subplots_adjust(bottom=.2, top=.95)

    xx = np.arange(ds.dims['model_ensemble'])
    dd = 1/ds['weights_i'].data
    nn = ds['weights_q'].data
    ww = nn*dd
    if 'nr_variants' in ds:
        nr = ds['nr_variants'].data
    else:
        nr = None

    if sort_by == 'name':
        sorter = np.arange(len(xx))  # no additional sorting
        lw_w = 2
        lw_p = .5
        lw_i = .5
    elif sort_by == 'weight':
        sorter = np.argsort(ww)[::-1]
        lw_w = 2
        lw_p = .5
        lw_i = .5
    elif sort_by == 'performance':
        sorter = np.argsort(nn)[::-1]
        lw_w = .5
        lw_p = 2
        lw_i = .5
    elif sort_by == 'independence':
        sorter = np.argsort(dd)[::-1]
        lw_w = .5
        lw_p = .5
        lw_i = 2

    yy1 = (ww/ww.sum())[sorter]
    yy2 = (nn/nn.sum())[sorter]
    yy3 = (dd/dd.sum())[sorter]

    ax.plot(xx, yy1, lw=lw_w, color='k', label='Weights without number weight', marker='o')
    ax.plot(xx, yy2, lw=lw_p, color='blue', label='Performance weight', marker='^')
    ax.plot(xx, yy3, lw=lw_i, color='green', label='Independence weight', marker='v')
    ax.axhline(1/len(xx), color='k', ls='--', label='Equal weight')

    if nr is not None:
        yy4 = ((1/nr)/(1/nr).sum())[sorter]
        ax.plot(xx, yy4, lw=.5, color='orange', label='Number weight', marker='v')

    model_ensemble = ds['model_ensemble'].data
    if sort_by in ['weight', 'performance', 'independence']:
        ax.set_xticks(xx)
        ax.set_xticklabels(model_ensemble[sorter])
    else:  # plot xlabel only for first ensemble member
        models = [*map(lambda x: x.split('_')[0] + '_' + x.split('_')[2], model_ensemble)]
        _, idx = np.unique(models, return_index=True)  # index of unique models
        models = np.array(models)[idx]
        ax.set_xticks(idx)
        ax.set_xticks(xx, minor=True)
        ax.set_xticklabels(models)

    ax.set_xlim(0, xx.max())
    ax.set_ylim(0, None)
    plt.xticks(rotation=90)
    ax.set_xlabel('Model name', fontsize='large')
    ax.set_ylabel('Normalized weight', fontsize='large')

    ax.grid()
    title = 'Weights per model sorted by {} ($\sigma_q$={:.2f}, $\sigma_i$={:.2f})'.format(
        sort_by, ds['sigma_q'].data, ds['sigma_i'].data)
    ax.set_title(title, fontsize='x-large',)

    plt.legend(title=f'Normalized weights')
    plt.xticks(rotation=90)

    filename = os.path.join(path, f'weights_by_{sort_by}.png')
    plt.savefig(filename, dpi=300)
    plt.close()
    logger.debug('Saved plot: {}'.format(filename))
