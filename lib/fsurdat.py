"""
Created: Camden Opfer, November 2025
Last Modified: Camden Opfer, March 2026

Intended to be run on a copy of the fsurdat file, modifying it so that all of one PFT is transferred to another for any set of PFTs.
"""

import os
import shutil
import subprocess
import numpy as np
import netCDF4 as nc
import scipy
from .utils import log

# See PFTs at https://escomp.github.io/CTSM/tech_note/Ecosystem/CLM50_Tech_Note_Ecosystem.html#id15
# Forest, shrub, and grass PFT ids
forestIds = list(range(1,9))
shrubIds = list(range(9,12))
grassIds = list(range(12,15))

# Dicts with keys=target PFTs, args=list of source PFTs
forestToBare = {0:list(range(1,9))}
forestToShrub = {9:[1,4,5], 10:[6,7], 11:[2,3,8]}
vegToBare = {0:list(range(1,15))}

def fsurdat_checkValid(path:str, tol:float = 1e-5):
    """
    Confirms that the sum of the percent natural PFTs are the same in two files. Useful after having modified an fsurdat file.

    :param path1: A path to an fsurdat netCDF file.
    :type path1: str
    :return: A boolean which is True when the file is found to be valid.
    :rtype: bool
    """
    with nc.Dataset(path, 'r') as data:
        PCT_NAT_PFT = data.variables['PCT_NAT_PFT'][:]

    PCT_NAT_PFT_tot = np.sum(PCT_NAT_PFT, axis=0)
    PCT_NAT_PFT_maxErr = np.nanmax(np.abs(PCT_NAT_PFT_tot - 100))
    if PCT_NAT_PFT_maxErr < tol:
        log(f'File {path} has valid PCT_NAT_PFT')
        return True
    else:
        log(f'File {path} has invalid PCT_NAT_PFT, with one point having total PCT_NAT_PFT off by {PCT_NAT_PFT_maxErr} from 100.')
        return False

def confirmSuccess(inPath:str, outPath:str, diffPath:str|None = None):
    """
    After running ncdiff on an original copy and a modified version of the fsurdat file, this summarizes the total modified elements.

    :param inPath: Path to an unaletered fsurdat file.
    :type inPath: str
    :param outPath: Path to the output, modified fsurdat file.
    :type outPath: str
    :param diffPath: The file to which the difference between the input and output data will be written. Default is to construct a filename from outPath, avoiding overwriting existing files.
    :type diffPath: str or None, optional
    """
    if diffPath is None:
        outDir, outName = os.path.split(outPath)
        diffName = outName[:-3] + '_diff'
        existingFiles = os.listdir(outDir)

        n = 0
        while n < 100:
            if f'{diffName}{n}.nc' not in existingFiles:
                diffPath = os.path.join(outDir, f'{diffName}{n}.nc')
                break
            n += 1

    try:
        subprocess.run([f'module load nco && ncdiff {inPath} {outPath} {diffPath}'], shell=True, check=True)
    except subprocess.CalledProcessError:
        # Process failed, likely because you're on a device that doesn't need module load (e.g. a typical PC or laptop)
        subprocess.run([f'ncdiff {inPath} {outPath} {diffPath}'], shell=True, check=True)

    diffData = nc.Dataset(diffPath, 'r')
    PCT_NAT_PFT = diffData.variables['PCT_NAT_PFT'][:]
    log(f'Number of elements modified: {np.sum(PCT_NAT_PFT != 0)}')

def modify_PCT_NAT_PFT(inPath:str, outPath:str, modificationDict:dict|None = None):
    """
    Moves the percent of ground covered by one (or several) plant functional types to a new type, as represented by the PCT_NAT_PFT variable of the NetCDF file used as fsurdat. After the modification, confirms that the output file remains valid for use by CESM.

    :param inPath: The path to an unaltered fsurdat file, to be modified.
    :type inPath: str
    :param outPath: The path to which the modified fsurdat file will be written.
    :type outPath: str
    :param changeDict: The dictionary from which to sourge the modification. Keys correspond to the PFT in the output, and the corresponding values are lists of PFTs from which to "take" percentages. Defaults to changing all vegetation to bare soil.
    :type changeDict: dict or None, optional
    """
    if modificationDict is None:
        modificationDict = vegToBare

    shutil.copy2(inPath, outPath) # NOTE From some non-rigorous testing, this requires the original file to not be currently open. The use of "with" in meanHeatFlux() and any other Python scripts, and avoiding opening the file in a notebook, should allow this copy function to work as intended.

    with nc.Dataset(outPath, 'r+') as data:
        PCT_NAT_PFT = data.variables['PCT_NAT_PFT'][:]

        for target, sources in modificationDict.items():
            modification = np.zeros((PCT_NAT_PFT.shape[1], PCT_NAT_PFT.shape[2]))

            for source in sources:
                log(f'Changing PFT from {source} to {target}')
                source_PCT_NAT_PFT = PCT_NAT_PFT[source]
                modification += source_PCT_NAT_PFT
                PCT_NAT_PFT[source][:] = 0

            PCT_NAT_PFT[target] += modification
        data.variables['PCT_NAT_PFT'][:] = PCT_NAT_PFT

    log('Checking output file is valid to use as fsurdat, and is different from the input')
    fsurdat_checkValid(inPath, outPath)
    confirmSuccess(inPath, outPath)

def smartDeforestation(inPath:str, outPath:str, grassFracs:np.ndarray|None = None, latLonRatio:float|int = 3):
    """
    Replaces forest and shrubland in each grid cell with grassland. This is proportioned between PFTs 12, 13, and 14 (C3 Arctic, C3, and C4 grass) according to the existing ration between the grass types in that cell. If no grass exists, takes the percentage to use from the nearest cell.

    This follows the methodology of a couple of papers: https://doi.org/10.5194/esd-11-183-2020 and https://doi.org/10.1016/j.jhydrol.2025.133781, though they base the C3/C4 ratios off of observations, rather than the model.

    After the modification, confirms that the output file remains valid for use by CESM.

    :param inPath: The path to an unaltered fsurdat file, to be modified.
    :type inPath: str
    :param outPath: The path to which the modified fsurdat file will be written.
    :type outPath: str
    :param grassFracs: The fraction of each grass type to use at each cell. By default, this is calculated from the existing data.
    :type grassFracs: np.ndarray or None, optional
    :param latLonRatio: The stretch factor to apply to the nearest neighbour search when calculating grassFracs. Usually >1 to have a zonal bias, since that's how climatologies/biomes tend to sort themselves. Default is 3.
    :type latLonRatio: float or int, optional
    """
    shutil.copy2(inPath, outPath) # NOTE From some non-rigorous testing, this requires the original file to not be currently open. The use of "with" in meanHeatFlux() and any other Python scripts, and avoiding opening the file in a notebook, should allow this copy function to work as intended.

    with nc.Dataset(outPath, 'r+') as data:
        PCT_NAT_PFT = data.variables['PCT_NAT_PFT'][:]

        if grassFracs is None:
            log('Getting ratios between grass PFTs')
            grasses = np.zeros((len(grassIds), PCT_NAT_PFT.shape[1], PCT_NAT_PFT.shape[2]))
            for i, grassId in enumerate(grassIds):
                grasses[i] = PCT_NAT_PFT[grassId][:]

            grassTot = np.sum(grasses, axis=0)
            grassless = grassTot == 0
            grassTot[grassless] = np.nan

            grassFracs = grasses/grassTot

            # Fill empty data with nearest neighbour, prioritizing by a factor given above
            # This follows the papers listed above, which use the nearest zonal point, but is slightly more sophisticated by allowing some meridional shifts if the nearest zonal neighbour is absurdly far away.
            indices = np.indices(grassFracs.shape[1:])
            rows = indices[0].flatten() # Corresponds to latitude
            cols = indices[1].flatten() * latLonRatio # Correspons to longitude, hence multiplied by ratio
            indices = np.column_stack((rows, cols))

            indeces_noNans = indices[~grassless.flatten()]
            grassFracs_noNans = grassFracs[:, ~grassless].T

            interpolator = scipy.interpolate.NearestNDInterpolator(indeces_noNans, grassFracs_noNans)

            indeces_nans = indices[grassless.flatten()]
            grassFracs[:, grassless] = interpolator(indeces_nans).T

        log('Finding total percent forest PFT by location')
        forestTot = np.zeros((PCT_NAT_PFT.shape[1], PCT_NAT_PFT.shape[2]))
        for woodedId in forestIds + shrubIds: # If wanting to change only forest or only shrub, this would be the line to change
            forestTot += PCT_NAT_PFT[woodedId][:]
            PCT_NAT_PFT[woodedId][:] = 0

        log('Applying new grass percentages')
        for j, grassId in enumerate(grassIds):
            grassModifier = forestTot * grassFracs[j]
            PCT_NAT_PFT[grassId][:] += grassModifier

        data.variables['PCT_NAT_PFT'][:] = PCT_NAT_PFT

    log('Checking output file is valid to use as fsurdat, and is different from the input')
    fsurdat_checkValid(inPath, outPath)
    confirmSuccess(inPath, outPath)

if __name__ == '__main__':
    inFile = '/project/def-mlague/cmopfer/surfdata_0.9x1.25_hist_78pfts_CMIP6_simyr2000_c190214.nc'

    # out_file = '/project/def-mlague/cmopfer/surfdata_forestToShrub.nc'
    # modify_PCT_NAT_PFT(in_file, out_file)

    outFile = '/project/def-mlague/cmopfer/surfdata_woodedToGrass.nc'
    smartDeforestation(inFile, outFile)
