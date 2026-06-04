"""
Created: Camden Opfer, March 2026
Modified: Camden Opfer, May 2026

A bunch of plotting functions mostly relevant to input and output files related to CESM
"""
# Imports for typing
from typing import Any
from numpy import ndarray as _ndarray
from matplotlib.axis import Axis as _Axis
from cartopy.mpl.geoaxes import GeoAxes as _GeoAxes
from matplotlib.figure import Figure as _Figure

## Plotting Utitlities ##

def saveFig(fig:_Figure, savePath:str, saveDpi:int|float|None = 200):
    """
    Ensures the relevant directories exist, that the save path ends in a file extension, and then saves the figure out.

    :param fig: The figure object to save out as an image
    :type fig: matplotlib.figure.Figure
    :param savePath: The path, including filename, to which the image will be saved
    :type savePath: str
    :param saveDpi: The dpi to use when rendering and saving the image. If None, uses the figure's specified DPI. Default is 200
    :type saveDpi: int or float or None, optional
    """
    import os
    import warnings

    if saveDpi is None:
        saveDpi = 'figure'

    if os.path.splitext(savePath)[1] == '': # No file extension. May be tricked by a file name containing '.'
        savePath += '.png'
    saveDir = os.path.dirname(savePath)
    if saveDir:
        os.makedirs(saveDir, exist_ok=True)
    try:
        fig.savefig(savePath, bbox_inches='tight', dpi=saveDpi)
    except Exception as e:
        import datetime
        timestamp = datetime.datetime.now().timestamp()
        fallbackPath = f'BACKUP-DOWNLOAD-{timestamp}.png'

        warnings.warn(f'fig.savefig() failed with error {e}. To avoid lost work, will attempt to save figure to fallback path: {fallbackPath}')
        fig.savefig('', bbox_inches='tight', dpi=200)

def ensureAxis(ax:_Axis|_GeoAxes|None = None, wantGeoAxes:bool = False, projection:Any = None) -> tuple[_Figure, _Axis|_GeoAxes]:
    """
    Checks if ax is an Axis object (or GeoAxes object if specified), and returns it if satisfied. If not, either replaces the ax object with the correct type (switching Axis to GeoAxes or GeoAxes to Axis) or creates a new figure and axis.

    :param ax: The axis object to check. Default is None, in which case a new figure and axis is created.
    :type ax: Axis or GeoAxes or None, optional
    :param wantGeoAxes: Specifies whether the desired return of the function should contain a GeoAxes (True) or Axis (False) object. Default is False, which will lead to a regular Axis object.
    :type wantGeoAxes: bool, optional
    :param projection: The projection to be used by the GeoAxes object, if applicable. Something like cartopy.crs.PlateCarre(). Default is None, which leaves the projection unspecified. Must be provided if wantGeoAxes is True.
    :type projection: Any, optional

    :return: The figure and axis objects associated with the (potentially new) axis
    :rtype: tuple[Figure, Axis or GeoAxes]
    """
    import matplotlib.pyplot as plt
    from matplotlib.layout_engine import ConstrainedLayoutEngine, TightLayoutEngine

    if wantGeoAxes and projection is None:
        raise ValueError('When wantGeoAxis is True, projection must be provided to ensureAxis(), but got projection=None.')

    if ax is None:
        if wantGeoAxes:
            fig, outAx = plt.subplots(1, 1, subplot_kw={'projection':projection})
        else:
            fig, outAx = plt.subplots(1, 1)
        return fig, outAx

    fig = ax.figure

    if (isinstance(ax, _Axis) and not wantGeoAxes) or (isinstance(ax, _GeoAxes) and wantGeoAxes):
        return fig, ax

    # NOTE The following block may not be necessary? The layoutengine is preserved since it's a figure property?
    # Take note of what layout to use when adding the GeoAxes.
    layoutEngine = fig.get_layout_engine()
    constrained = isinstance(layoutEngine, ConstrainedLayoutEngine)
    tight = isinstance(layoutEngine, TightLayoutEngine)

    pos = ax.get_position() # Position the old axis had, so that the new one will replace it
    fig.delaxes(ax)

    if wantGeoAxes:
        outAx = fig.add_axes(pos, projection=projection)
    else:
        outAx = fig.add_axes(pos)

    # NOTE Again, from above, it seems that layout engine is preserved?
    # Re-apply layout stored earlier
    if constrained:
        fig.set_constrained_layout(True)
    elif tight:
        fig.tight_layout()
    return fig, outAx

def yAxisPressure(ax:_Axis|_GeoAxes, ydata:_ndarray, pMin:int|float = 300) -> _Axis|_GeoAxes:
    """
    Sets up the y axis of a plot to represent pressure by having it go from large to small values, using a log scale, and having useful tick values.

    :param ax: The axis to setup the y axis of
    :type ax: Axis or GeoAxes
    :param ydata: The pressure data to be plotted, used to define the plot limits.
    :type ydata: ndarray
    :param pMin: The minimum pressure value (visually, the highest level) to plot on the graph. Default is 300, which is usually reasonable assuming units are hPa.
    :type pMin: int or float, optional

    :return: The edited axis object. The type will match the input ax object since it is the same object.
    :rtype: Axis or GeoAxes
    """
    import numpy as np
    from matplotlib.ticker import StrMethodFormatter, NullFormatter

    ax.yaxis.set_inverted(True)
    ax.set_yscale('log')

    pMax = np.nanmax(ydata)
    yTicks = np.logspace(np.log10(pMax-10), np.log10(pMin+10), 6)
    yTicks = np.round(yTicks / 10) * 10

    ax.set_ylim(bottom=pMax, top=pMin)

    ax.set_yticks(yTicks)
    ax.tick_params(axis='y', which='minor', left=False)
    ax.yaxis.set_major_formatter(StrMethodFormatter('{x:.0f}'))
    ax.yaxis.set_minor_formatter(NullFormatter())

    return ax

def cbarTicks(dataMin:float|int, dataMax:float|int, logAx:bool = False) -> tuple[list|_ndarray, list[str]]:
    """
    Creates lists of reasonable tick and tick label values to be fed to the cbarObject.set_ticks() method.
    
    Note that, for a diverging colorbar, dataMax and dataMin should be +/-halfRange respectively.

    :param dataMin: The value to be used for the minimum tick.
    :type dataMin: float or int
    :param dataMin: The value to be used for the maximum tick.
    :type dataMin: float or int
    :param logAx: Indicates whether the colorbar will have a log axis (True) or a linear one (False). Default is False, representing a linear dataset.
    :type logAx: bool, optional

    :return: A tuple with the ticks (list or array of numerical values representing expected tick locations) and their labels (a list of strings of the same length which nicely formats the values in a consistent way).
    :rtype: tuple[list or _ndarray, list[str]]
    """
    from math import ceil, log10
    import numpy as np

    def scientificNotation(floats:_ndarray) -> list[str]:
        exponents = np.astype(np.floor(np.log10(np.abs(floats))), int)
        coefficients = floats/(10.**exponents)
        sciNot = [rf'${coefficient:#.2f} \cdot 10^{{{exponent}}}$' for exponent, coefficient in zip(exponents, coefficients)]
        return sciNot

    if logAx:
        powers = list(range(ceil(log10(dataMin)), ceil(log10(dataMax))))
        if len(powers) >= 3:
            ticks = [10**power for power in powers]
            tickLabels = [f'$10^{{{power}}}$' for power in powers]
        else:
            ticks = np.logspace(log10(dataMin), log10(dataMax), 8, base=10)
            tickLabels = scientificNotation(ticks)

        return ticks, tickLabels

    # If linear ax (logAx didn't trigger the above return statement)...
    ticks = np.linspace(dataMin, dataMax,8)

    exponents = np.astype(np.floor(np.log10(np.abs(ticks))), int)
    bestAsFloat = np.sum(np.logical_or(exponents > -2, exponents < 3))
    if bestAsFloat >= 7: # All (or all but one) best notated as floats
        tickLabels = [f'{tick:#.3g}' for tick in ticks]
    elif bestAsFloat <= 1: # All (or all but one) best notated as exponentials
        tickLabels = scientificNotation(ticks)
    else: # Use a mixture of floats and exponentials
        tickLabels = []
        for exponent, tick in zip(exponents, ticks):
            if exponent < -1 or exponent > 2:
                tickLabels += scientificNotation(tick)
            else:
                tickLabels += [f'{tick:#.3g}']

    return ticks, tickLabels


## Functions That Make Full Plots ##

def atmCrossSection(data:_ndarray, xdim:_ndarray, ydim:_ndarray, title:str, dataLabel:str, xLabel:str = None, yLabel:str = None, globalMap:bool = True, yIsPressure:bool = False, cbarType:str = 'linear', cmap:str|None = None, vlims:list|None = None, pMin:int|float = 300, contourIntervals:int = 30, ax:_Axis|_GeoAxes|None = None, savePath:str|None = None) -> _Axis|_GeoAxes|None:
    """
    A very flexible function to plot colormaps over a global map with an outline of the continents.

    :param data: The data to plot on the grid.
    :type data: ndarray
    :param xdim: The array of x values the data should be plotted over. If globalMap is True, this should be longitude. Otherwise, it should likely be latitude or longitude.
    :type xdim: ndarray
    :param ydim: The array of y values the data should be plotted over. If globalMap is True, this should be latitude. Otherwise, it should likely be pressure.
    :type ydim: ndarray
    :param title: The title to display on the plot.
    :type title: str
    :param dataLabel: The units by which the colorbar will be labelled, corresponding to the units of data.
    :type dataLabel: str
    :param xLabel: The units by which the x axis will be labelled, corresponding to the units of xdim. Will be ignored if globalMap is True, since then it is evident that the x axis is longitude. Default is None, so there will be no label.
    :type xLabel: str, optional
    :param yLabel: The units by which the y axis will be labelled, corresponding to the units of ydim. Will be ignored if globalMap is True, since then it is evident that the y axis is latitude. Default is None, so there will be no label.
    :type yLabel: str, optional
    :param globalMap: Indicates whether this is a global map (True), in which case data will be plotted against a background showing the continental boundaries, with ticks and labels indicating latitude and longidute. Default is True
    :type globalMap: bool, optional
    :param yIsPressure: Indicates whether the y axis of the plot represents pressure (True) or not (False). If True, inverts the axis, makes it log scale, and makes more readable ticks.
    :type yIsPressure: bool, optional
    :param cbarType: The choice of colorbar scaling. Must be 'linear', 'log', or 'diverging'.
    :type cbarType: str, optional
    :param cmap: The colormap option to retrieve by plt.get_cmap(cmap). Therefore, must be available with the version of matplotlib being used. Default depends on cbarType.
    :type cmap: str or None, optional
    :param vlims: List containing the minimum and maximum values for the colorbar contours to reach. Default is to calculate this based on percentExcluded.
    :type vlims: list or None, optional
    :param pMin: When yIsPressure is True, this argument determines the minimum y value plotted. Default is 300, which is reasonable for plotting things in hPa in the troposphere.
    :type pMin: int or float, optional
    :param contourIntervals: Number of increments at which to evaluate the colormap. A greater value leads to smoother, more pleasing visuals. Default is 100.
    :type contourIntervals: int, optional
    :param ax: An axis or axis-like object to use as a reference for the plot. If the wrong type (e.g. an Axis object, but globalMap is True), will be replaced in place (within the figure) by a correct axis object. When this argument is not None, the final axis object will be returned rather than saving the figure and clearing it. Default is None, in which case a new figure and axis are created.
    :type ax: Axis or GeoAxes or None, optional
    :param savePath: The file to which the resulting figure will be saved. Default is the working directory. The figure is only saved out if ax is None, otherwise an axis object is, instead, returned.
    :type savePath: str or None, optional

    :return: Default is to return None. When returnAx is True, returns a GeoAxes object with the map drawn on it.
    :rtype: None or GeoAxes
    :raises ValueError: Raised when cbarType is not a valid option ('linear', 'log', or 'diverging')
    """
    import warnings
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.colors as colors
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    if globalMap and yIsPressure:
        raise ValueError('Invalid combination of arguments to atmCrossSection(). Only one of globalMap and yIsPressure can be True, but both provided values were True.')

    try:
        mask = np.logical_or(data.mask, np.isnan(data))
    except AttributeError: # data is not a masked array, and doesn't have a data.mask attribute
        mask = np.isnan(data)

    plotData = np.ma.MaskedArray(data, mask=mask)

    validData = plotData[~plotData.mask]
    if np.all(validData == validData[0]):
        warnings.warn('Input data for globalMap contains one uniform value, so colorbar could not spread colormap across range. Will not create plot.', UserWarning)
        return ax # Return without plotting because continuing leads to a very cryptic error raised by ax.colorbar's call to pcolormesh

    if globalMap:
        projection = ccrs.PlateCarree()
    else:
        projection = None
    fig, plotAx = ensureAxis(ax, globalMap, projection)

    if yIsPressure:
        plotAx = yAxisPressure(plotAx, ydim, pMin)

    if cbarType == 'linear':
        if cmap is None:
            if np.sum(plotData > 0) > 0.05 * plotData.size: # Vast majority of data is positive
                cmap = 'viridis'
            else:
                cmap = 'viridis_r'
        cmap = plt.get_cmap(cmap)

        if vlims is None:
            vlims = np.nanpercentile(plotData, [0, 100])

        contourLevels = np.linspace(vlims[0], vlims[1], contourIntervals)

        # Define distribution of colors in cmap across data range
        bottomExtend = contourLevels[0] * (1-1e-5) > np.nanmin(plotData) # True when data is smaller than vmin by more than 0.001%
        topExtend = contourLevels[-1] * (1+1e-5) < np.nanmax(plotData) # True when data is greater than vmax by more than 0.001%

        if bottomExtend and topExtend:
            norm = colors.BoundaryNorm(contourLevels, cmap.N, extend='both')
        elif bottomExtend:
            norm = colors.BoundaryNorm(contourLevels, cmap.N, extend='min')
        elif topExtend:
            norm = colors.BoundaryNorm(contourLevels, cmap.N, extend='max')
        else:
            norm = colors.BoundaryNorm(contourLevels, cmap.N, extend='neither')

        dataMin, dataMax = contourLevels[0], contourLevels[-1]

    elif cbarType == 'log':
        if cmap is None:
            cmap = 'inferno'

        if vlims is None:
            vlims = tuple(i for i in np.nanpercentile(plotData, [0, 100]))
        contourLevels = np.logspace(np.log10(vlims[0]), np.log10(vlims[1]), contourIntervals, base=10)

        norm = colors.LogNorm(vlims[0], vlims[1])

        dataMin, dataMax = contourLevels[0], contourLevels[-1]

    elif cbarType == 'diverging':
        if vlims is not None:
            warnings.warn('globalMap will ignore user-specified value for vmin and/or vmax because cbarType is diverging.', UserWarning)

        if cmap is None:
            cmap = 'seismic'

        halfRange = np.nanmax(np.abs(np.nanpercentile(plotData, [0, 100])))
        norm = colors.CenteredNorm(halfrange=halfRange)

        dataMin, dataMax = -halfRange, halfRange

    else:
        raise ValueError(f"Invalid cbarType option {cbarType} in greenlandPlotter. Must be one of 'linear', 'log', or 'diverging'")

    contour = plotAx.pcolormesh(xdim, ydim, plotData, transform=projection, cmap=cmap, norm=norm)

    # Create and nice-ify colorbar
    colorbar = fig.colorbar(contour, norm=norm, spacing='proportional', pad=0.1)

    ticks, tickLabels = cbarTicks(dataMin, dataMax, cbarType == 'log')
    colorbar.set_ticks(ticks, labels=tickLabels)

    colorbar.minorticks_off()
    colorbar.set_label(dataLabel)

    # General beauty and labelling
    plotAx.set_title(title)

    if globalMap:
        plotAx.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False)
        plotAx.coastlines(resolution='110m') # Options are 110, 50, or 10m. For a global map, higher resolution is less useful
        plotAx.add_feature(cfeature.LAND, edgecolor='none', facecolor='dimgray')
    else:
        plotAx.set_xlabel(xLabel)
        plotAx.set_ylabel(yLabel)

    # Either return the axis or save and clear the figure
    if ax is not None:
        return plotAx

    saveFig(fig, savePath, saveDpi = 200)
    plt.close(fig)

def profiles(pressure:_ndarray, data:list[_ndarray], savePath:str, title:str, xLabel:str, dataLabels:list[str]|None = None, diffs:bool = True, pMin = 300):
    """
    Plots vertical profiles of data (represented by the x axis) against pressure (represented by the y axis). Optionally, also plots differences between elements 1 on of data against element 0 of data.

    :param pressure: The pressure values to plot over.
    :type pressure: ndarray
    :param data: The profile(s) of data to plot over. Each element of data should be an array matching the shape of pressure.
    :type data: list[ndarray]
    :param savePath: The file to which the resulting figure will be saved.
    :type savePath: str or None, optional
    :param title: The title to display on the plot.
    :type title: str
    :param xLabel: The label to show on the x axis, which should correspond to the units of data (not pressure).
    :type xLabel: str
    :param dataLabels: Labels corresponding to the arrays within data to be used by the legend. This list should, therefore, be of the same length as data. Default is None, in which case no legend is created.
    :type dataLabels: list[str] or None, optional
    :param diffs: Determines whether to plot the difference between elements 1 on of data against element 0 of data (True) or to plot only the raw data (False). The differences are displayed on a second axis of the same figure.
    :type diffs: bool, optional
    :param pMin: Determines the minimum y value plotted. Default is 300, which is reasonable for plotting things in hPa in the troposphere.
    :type pMin: int or float, optional
    """
    import numpy as np
    import matplotlib.pyplot as plt

    pMax = np.max(pressure)

    diffs = diffs and len(data) > 1 # Ensure diff plot is only set up if it will actually have data

    if diffs:
        fig, axs = plt.subplots(1, 2, layout='tight', figsize=(8,5))
    else:
        fig, loneAx = plt.subplots(figsize=(4,5))
        axs = [loneAx]

    ticks = np.logspace(np.log10(pMax-10), np.log10(pMin+10), 6)
    ticks = np.round(ticks / 10) * 10

    # Axis setup
    for ax in axs:
        plotAx = yAxisPressure(plotAx, pressure, pMin)

        ax.set_xlabel(xLabel)
        ax.set_title(title)

        ax.axhline(pressure[0], c='grey', alpha=0.2, linewidth=1, label='Model Levels')
        for p in pressure[1:]:
            ax.axhline(p, c='grey', alpha=0.2, linewidth=1)
        if dataLabels is not None:
            ax.legend(loc='lower left')

    # Plot profiles directly
    for i, (prof, dataLabel) in enumerate(zip(data, dataLabels)):
        axs[0].plot(prof, pressure, label=dataLabel)

        if diffs and i != 0:
            # Plot differences between data's elements 1 on to element 0
            diff = prof - data[0]
            axs[1].plot(diff, pressure, label=f'{dataLabel} Minus {dataLabels[0]}')

    # Save and clear figure
    saveFig(fig, savePath, saveDpi = 200)
    plt.close(fig)

def threeVar(data1:_ndarray, data2:_ndarray, data3:_ndarray, long:_ndarray, lat:_ndarray, savePath:str, title:str, legend:bool = True, dataLabels:list|None = None):
    """
    A function built to map three variables, each as their own colour, with overlapping regions showing a mixture of the relevant colours. As an example of when this could be useful: this was originally developed to plot how much the three grass PFTs were increased in a deforested fsurdat file.

    :param data1: The first set of data to plot. This will correspond with blue.
    :type data1: ndarray
    :param data2: The second set of data to plot. This will correspond with orange. Must be the same shape as data1.
    :type data2: ndarray
    :param data3: The third set of data to plot. This will correspond with purple. Must be the same shape as data1.
    :type data3: ndarray
    :param long: The longitude array corresponding to the three datasets. Must be the same shape as data1.
    :type long: ndarray
    :param lat: The latitude array corresponding to the three datasets. Must be the same shape as data1.
    :type lat: ndarray
    :param savePath: The file to which the resulting figure will be saved.
    :type savePath: str
    :param title: The title to display on the plot.
    :type title: str
    :param legend: Whether or not to create a triangular legend showing which colour corresponds to each dataset/label.
    :type legend: bool, optional
    :param dataLabels: The list of labels to use, with three elements corresponding to data1, data2, and data3 respectively. Default is ['C3 Arctic', 'C3', 'C4'], used when plotting the three grass PFTs of CESM. Has no effect when legend = False.
    :type dataLabels: list or None, optional
    """
    import numpy as np
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

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
    def threeVarLegend(dataLabels, res = 500):
        """
        The kind of function you trust someone on Stack Overflow to provide, and don't question. Makes a triangle showing what each colour corresponds to.
        """
        # Legend dims
        h = np.sqrt(3)/2
        w = 1.

        # Legend grid
        x = np.linspace(0, 1, res)
        y = np.linspace(0, h, res)
        X, Y = np.meshgrid(x, y)

        # Triangle vertices
        v1 = np.array([w/2, h])
        v2 = np.array([0.0, 0.0])
        v3 = np.array([w, 0.0])

        # Crazy math to find distances to each vertex
        detT = (v2[1]-v3[1]) * (v1[0]-v3[0]) + (v3[0]-v2[0]) * (v1[1]-v3[1])

        A = ((v2[1]-v3[1]) * (X-v3[0]) + (v3[0]-v2[0]) * (Y-v3[1]))/detT
        B = ((v3[1]-v1[1]) * (X-v3[0]) + (v1[0]-v3[0]) * (Y-v3[1]))/detT
        C = 1 - A - B

        # Make image
        img = (A[...,None] * blue + B[...,None] * orange + C[...,None] * purple)
        mask = (A>=0) & (B>=0) & (C>=0)
        img[~mask] = 1

        # Plot
        ax2 = fig.add_axes([1.05, 0.4, 0.2, 0.2])
        ax2.axis('off')

        ax2.imshow(img, origin="lower", extent=[0,w,0,h])

        ax2.text(w/2, h * 1.03, dataLabels[0], ha='center')
        ax2.text(-w * .02, -h * 0.03, dataLabels[1], ha='right')
        ax2.text(w * 1.02, -h * 0.03, dataLabels[2], ha='left')

    if legend:
        threeVarLegend(dataLabels)

    # Save and clear figure
    saveFig(fig, savePath, saveDpi = 200)
    plt.close(fig)
