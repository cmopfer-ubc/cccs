"""
Created: Camden Opfer, March 2026

A bunch of plotting functions for input and output files related to CESM
"""

import os
import warnings
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import cartopy.crs as ccrs
import cartopy.feature as cfeature

def globalMap(data, long, lat, savePath, title, units, cbarType='linear', cmap=None, vlims=None, contourIntervals=100, percentExcluded=0):
    """
    A very flexible function to plot colormaps over a global map with an outline of the continents.

    :param data: The data to plot on the grid.
    :type data: np.ndarray
    :param long: The array of longitude values to plot over. Must have the same shape as data.
    :type long: np.ndarray
    :param lat: The array of longitude values to plot over. Must have the same shape as data.
    :type lat: np.ndarray
    :param savePath: The file to which the resulting figure will be saved.
    :type savePath: str
    :param title: The title to display on the plot.
    :type title: str
    :param units: The units by which the colorbar will be labelled
    :type units: str
    :param cbarType: The choice of colorbar scaling. Must be 'linear', 'log', or 'diverging'.
    :type cbarType: str
    :param cmap: The colormap option to retrieve by plt.get_cmap(cmap). Therefore, must be available with the version of matplotlib being used. Default depends on cbarType.
    :type cmap: str or None, optional
    :param vlims: List containing the minimum and maximum values for the colorbar contours to reach. Default is to calculate this based on percentExcluded.
    :type vlims: list or None, optional
    :param contourIntervals: Number of increments at which to evaluate the colormap. A greater value leads to smoother, more pleasing visuals. Default is 100.
    :type contourIntervals: int, optional
    :param percentExcluded: The percentage of data to exclude from both the top and bottom of data's distribution when creating the colorbar. This avoids having a minimum (maximum )value of the colorbar far less (greater) than the majority of the data, washing out the visuals. Default is 0.
    :type percentExcluded: float or int

    :raises ValueError: Raised when cbarType is not a valid option ('linear', 'log', or 'diverging')
    """
    nonNanData = data[~np.isnan(data)]
    if np.all(nonNanData == nonNanData[0]):
        warnings.warn('Input data for globalMap contains one uniform value, so colorbar could not spread colormap across range. Will not create plot.', UserWarning)
        return # Return without plotting because continuing leads to a very cryptic error raised by ax.colorbar's call to pcolormesh

    # ccrsProj = ccrs.RotatedPole(140, 70) # Format is (lon, lat). Useful for regional plots, where the projection can be centred over the data. This value corresponds with Greenland as an example
    ccrsProj = ccrs.PlateCarree()
    fig, ax = plt.subplots(1, 1, subplot_kw={'projection':ccrsProj})

    if cbarType == 'linear':
        if cmap is None:
            if np.sum(data > 0) > 0.05 * data.size: # Vast majority of data is positive
                cmap = 'viridis'
            else:
                cmap = 'viridis_r'
        cmap = plt.get_cmap(cmap)

        if vlims is None:
            vlims = np.nanpercentile(data, [percentExcluded, 100-percentExcluded])

            # contourLevels = np.nanpercentile(data, np.linspace(percentExcluded, 100-percentExcluded, contourIntervals)) # This "cheats" by stretching/compressing the colorbar to match where there are more/less points
        contourLevels = np.linspace(vlims[0], vlims[1], contourIntervals)

        # Define distribution of colors in cmap across data range
        bottomExtend = contourLevels[0] * ((1-1e-5)) > np.nanmin(data) # True when data is smaller than vmin by more than 0.001%
        topExtend = contourLevels[-1] * (1+1e-5) < np.nanmax(data) # True when data is greater than vmax by more than 0.001%

        if bottomExtend and topExtend:
            norm = colors.BoundaryNorm(contourLevels, cmap.N, extend='both')
        elif bottomExtend:
            norm = colors.BoundaryNorm(contourLevels, cmap.N, extend='min')
        elif topExtend:
            norm = colors.BoundaryNorm(contourLevels, cmap.N, extend='max')
        else:
            norm = colors.BoundaryNorm(contourLevels, cmap.N, extend='neither')

        ticks = np.linspace(contourLevels[0], contourLevels[-1],8)

        # Make ticklabels coherent in choice of decimal or scientific notation if possible
        exponents = np.floor(np.log10(np.abs(ticks))).astype(int)
        if np.sum(np.logical_or(exponents < -1, exponents > 2)) < 2: # All (or all but one) best notated as floats
            tickLabels = [f'{tickLocation:#.3g}'.strip('.') for tickLocation in ticks]
        else:
            coefficients = ticks/(10.**exponents)
            tickLabels = []
            if np.sum(np.logical_and(exponents > -1, exponents < 2)) < 2: # All (or all but one) best notated as exponentials
                tickLabels = [rf'${coefficient:#.2f} \cdot 10^{{{exponent}}}$' for coefficient, exponent in zip(coefficients, exponents)]
            else: # Mixture of floats and exponentials needed
                for coefficient, exponent, tickLocation in zip(coefficients, exponents, ticks):
                    if exponent < -1 or exponent > 2:
                        tickLabels += [rf'${coefficient:#.2f} \cdot 10^{{{exponent}}}$']
                    else:
                        tickLabels += [f'{tickLocation:#.3g}'.strip('.')]

    elif cbarType == 'log':
        if cmap is None:
            cmap = 'inferno'

        if vlims is None:
            vlims = tuple(i for i in np.nanpercentile(data, [percentExcluded, 100-percentExcluded]))
        contourLevels = np.logspace(np.log10(vlims[0]), np.log10(vlims[1]), contourIntervals, base=10)

        norm = colors.LogNorm(vlims[0], vlims[1])

        # Define location of ticks for colorbar
        powers = list(range(math.ceil(np.log10(contourLevels[0])), math.ceil(np.log10(contourLevels[-1]))))
        if len(powers) >= 2:
            ticks = [10**power for power in powers]
            tickLabels = [f'$10^{{{power}}}$' for power in powers]
        else:
            ticks = np.logspace(np.log10(contourLevels[0]), np.log10(contourLevels[-1]), 8, base=10)
            exponents = np.floor(np.log10(np.abs(ticks))).astype(int)
            coefficients = ticks/(10.**exponents)
            tickLabels = [rf'${coefficient:#.2f} \cdot 10^{{{exponent}}}$' for exponent, coefficient in zip(exponents, coefficients)]

    elif cbarType == 'diverging':
        if vlims is not None:
            warnings.warn('globalMap will ignore user-specified value for vmin and/or vmax because cbarType is diverging.', UserWarning)

        if cmap is None:
            cmap = 'seismic'

        halfRange = np.nanmax(np.abs(np.nanpercentile(data, [percentExcluded, 100-percentExcluded])))
        norm = colors.CenteredNorm(halfrange=halfRange)

        ticks = np.linspace(-halfRange, halfRange,8)

        # Make ticklabels coherent in choice of decimal or scientific notation if possible
        exponents = np.floor(np.log10(np.abs(ticks))).astype(int)
        if np.sum(np.logical_or(exponents < -1, exponents > 2)) < 2: # All (or all but one) best notated as floats
            tickLabels = [f'{tickLocation:#.3g}'.strip('.') for tickLocation in ticks]
        else:
            coefficients = ticks/(10.**exponents)
            tickLabels = []
            if np.sum(np.logical_and(exponents > -1, exponents < 2)) < 2: # All (or all but one) best notated as exponentials
                tickLabels = [rf'${coefficient:#.2f} \cdot 10^{{{exponent}}}$' for coefficient, exponent in zip(coefficients, exponents)]
            else: # Mixture of floats and exponentials needed
                for coefficient, exponent, tickLocation in zip(coefficients, exponents, ticks):
                    if exponent < -1 or exponent > 2:
                        tickLabels += [rf'${coefficient:#.2f} \cdot 10^{{{exponent}}}$']
                    else:
                        tickLabels += [f'{tickLocation:#.3g}'.strip('.')]

    else:
        raise ValueError(f"Invalid cbarType option {cbarType} in greenlandPlotter. Must be one of 'linear', 'log', or 'diverging'")

    contour = ax.pcolormesh(long, lat, data, transform=ccrs.PlateCarree(), cmap=cmap, norm=norm)

    # Create and nice-ify colorbar
    colorbar = fig.colorbar(contour, ax=ax, norm=norm, spacing='proportional', pad=0.1)
    colorbar.set_ticks(ticks, labels=tickLabels)
    colorbar.minorticks_off()
    colorbar.set_label(units)

    ax.set_title(title)

    # # Center on region
    # bounds = [-63, -23, 59, 84] # Format is [lon_min, lon_max, lat_min, lat_max]. These correspond to Greenland, as an example
    # ax.set_extent(bounds, crs=ccrs.PlateCarree())
    # ax.set_aspect(1.8) # Useful to match the aspect of the bounds. Again, this corresponds to Greenland

    ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False)

    # Outline coasts, fill in continents
    ax.coastlines(resolution='110m') # Options are 110, 50, or 10m. For a global map, higher resolution is less useful
    ax.add_feature(cfeature.LAND, edgecolor='none', facecolor='dimgray')

    # Save and clear figure
    if os.path.splitext(savePath)[1] == '': # No file extension. May be tricked by a file name containing '.'
        savePath += '.png'
    os.makedirs(os.path.dirname(savePath), exist_ok=True)
    fig.savefig(savePath, bbox_inches='tight', dpi=200)
    plt.close(fig)

def threeVar(data1, data2, data3, long, lat, savePath, title, legend=True, dataLabels = None):
    """
    A function built to map three variables, each as their own colour, with overlapping regions showing a mixture of the relevant colours. As an example of when this could be useful: this was originally developed to plot how much the three grass PFTs were increased in a deforested fsurdat file.

    :param data1: The first set of data to plot. This will correspond with blue.
    :type data1: np.ndarray
    :param data2: The second set of data to plot. This will correspond with orange. Must be the same shape as data1.
    :type data2: np.ndarray
    :param data3: The third set of data to plot. This will correspond with purple. Must be the same shape as data1.
    :type data3: np.ndarray
    :param long: The longitude array corresponding to the three datasets. Must be the same shape as data1.
    :type long: np.ndarray
    :param lat: The latitude array corresponding to the three datasets. Must be the same shape as data1.
    :type lat: np.ndarray
    :param savePath: The file to which the resulting figure will be saved.
    :type savePath: str
    :param title: The title to display on the plot.
    :type title: str
    :param legend: Whether or not to create a triangular legend showing which colour corresponds to each dataset/label.
    :type legend: bool, optional
    :param dataLabels: The list of labels to use, with three elements corresponding to data1, data2, and data3 respectively. Default is ['C3 Arctic', 'C3', 'C4'], used when plotting the three grass PFTs of CESM. Has no effect when legend = False.
    :type dataLabels: list or None, optional
    """
    if dataLabels is None:
        dataLabels = ['C3 Arctic', 'C3', 'C4']

    # Check not all data is negative (negative colours are no colour in matplotlib-land)
    someNegative = False
    allNegative = True
    for data in [data1, data2, data3]:
        if np.all(data <= 0):
            someNegative = True
        else:
            allNegative = False
    
    if someNegative and not allNegative:
        raise ValueError('One or two datasets input to threeVar plotting function are negative. Unclear how to proceed and make logical/useful plot. Check if it makes sense to flip the signs of only some of your data, then do that before feeding it to the plotting function, if you wish to proceed.')
    if allNegative:
        data1, data2, data3 = -data1, -data2, -data3

    # Determine color weighting by point
    data1_frac = data1/np.nanmax(data1)
    data2_frac = data2/np.nanmax(data2)
    data3_frac = data3/np.nanmax(data3)

    blue = np.array([0,114,178])/255 # Need 0-1 range since data will be floats. 0-255 is only for ints
    orange = np.array([230,159,0])/255
    purple = np.array([204,121,167])/255

    color = data1_frac[...,None]*blue + data2_frac[...,None]*orange + data3_frac[...,None]*purple
    color = np.clip(color,0,1)

    # Plot
    ccrsProj = ccrs.PlateCarree()
    fig, ax = plt.subplots(1, 1, subplot_kw={'projection':ccrsProj}, dpi=200)
    ax.pcolormesh(long, lat, color, transform=ccrs.PlateCarree())

    ax.set_title(title)

    # Add lat/long grid, outline coasts, fill in continents
    ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False)
    ax.coastlines(resolution='110m', color='dimgray') # Options are 110, 50, or 10m. For a global map, the higher resolution is unneeded
    ax.add_feature(cfeature.LAND, edgecolor='none', facecolor='dimgray')

    ## Colorbar extraordinaire
    def makeLegend(dataLabels, res = 500):
        # Legend height
        h = np.sqrt(3)/2

        # Legend grid
        x = np.linspace(0, 1, res)
        y = np.linspace(0, h, res)
        X, Y = np.meshgrid(x, y)

        # Triangle vertices
        v1 = np.array([0.5, h])
        v2 = np.array([0.0, 0.0])
        v3 = np.array([1.0, 0.0])

        # Crazy math to find distances to each vertex. Why it works: someone on stack overflow sold his soul to the devil, and I trust them
        detT = (v2[1]-v3[1])*(v1[0]-v3[0]) + (v3[0]-v2[0])*(v1[1]-v3[1])

        A = ((v2[1]-v3[1])*(X-v3[0]) + (v3[0]-v2[0])*(Y-v3[1])) / detT
        B = ((v3[1]-v1[1])*(X-v3[0]) + (v1[0]-v3[0])*(Y-v3[1])) / detT
        C = 1 - A - B

        # Make image
        img = (A[...,None]*blue + B[...,None]*orange + C[...,None]*purple)
        mask = (A>=0) & (B>=0) & (C>=0)
        img[~mask] = 1

        # Plot
        ax2 = fig.add_axes([1.05, 0.4, 0.2, 0.2])
        ax2.axis('off')

        ax2.imshow(img, origin="lower", extent=[0,1,0,h])

        ax2.text(0.5, h+0.03, dataLabels[0], ha='center')
        ax2.text(-0.02, -0.03, dataLabels[1], ha='right')
        ax2.text(1.02, -0.03, dataLabels[2], ha='left')

    if legend:
        makeLegend(dataLabels)

    # Save and clear figure
    if os.path.splitext(savePath)[1] == '': # No file extension. May be tricked by a file name containing '.'
        savePath += '.png'
    os.makedirs(os.path.dirname(savePath), exist_ok=True)
    fig.savefig(savePath, bbox_inches='tight', dpi=200)
    plt.close(fig)

if __name__ == '__main__':
    import netCDF4 as nc

    fsurdatPath = '/home/cmopfer/projects/def-mlague/cmopfer/surfdata_0.9x1.25_hist_78pfts_CMIP6_simyr2000_c190214.nc'
    diffPath = '/home/cmopfer/projects/def-mlague/cmopfer/surfdata_woodedToGrass_diff0.nc'
    plotPath = '/home/cmopfer/projects/def-mlague/cmopfer/grassDiff_woodedToGrass'

    fsurdat = nc.Dataset(fsurdatPath)
    lat_fsurdat = fsurdat.variables['LATIXY'][:]
    lon_fsurdat = fsurdat.variables['LONGXY'][:]

    diff = nc.Dataset(diffPath)
    PCT_NAT_PFT_diff = diff.variables['PCT_NAT_PFT']
    c3Arctic_diff = -PCT_NAT_PFT_diff[12][:]
    c3_diff = -PCT_NAT_PFT_diff[13][:]
    c4_diff = -PCT_NAT_PFT_diff[14][:]

    threeVar(c3Arctic_diff, c3_diff, c4_diff, lon_fsurdat, lat_fsurdat, plotPath, 'Added Grass PFTs In Deforested Simulation')
