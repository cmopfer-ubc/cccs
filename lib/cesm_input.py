"""
Created: Camden Opfer, November 2025
Last Modified: Camden Opfer, May 2026

Modifies various input files to CESM.
"""
# Imports for typing
from numpy import ndarray as _ndarray

### FSURDAT ###

# See all PFTs at https://escomp.github.io/CTSM/tech_note/Ecosystem/CLM50_Tech_Note_Ecosystem.html#id15
# Forest, shrub, and grass PFT ids
_forestIds = list(range(1,9))
_shrubIds = list(range(9,12))
_grassIds = list(range(12,15))

def fsurdat_checkValid(path:str, tol:float = 1e-5):
    """
    Confirms that the PCT_NAT_PFT values of an fsurdat file add to 100%. Useful after having modified an fsurdat file.

    :param path: A path to an fsurdat netCDF file.
    :type path: str
    :return: A boolean which is True when the file is found to be valid.
    :rtype: bool
    """
    import numpy as np
    import netCDF4 as nc
    from .utils import log

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

def confirmDiff(inPath:str, outPath:str, diffPath:str|None = None):
    """
    After running ncdiff on an original copy and a modified version of the fsurdat file, this summarizes the total modified elements.

    :param inPath: Path to an unaletered fsurdat file.
    :type inPath: str
    :param outPath: Path to the output, modified fsurdat file.
    :type outPath: str
    :param diffPath: The file to which the difference between the input and output data will be written. Default is to construct a filename from outPath, avoiding overwriting existing files.
    :type diffPath: str or None, optional
    """
    import os
    import subprocess
    import numpy as np
    import netCDF4 as nc
    from .utils import log

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
    import shutil
    import numpy as np
    import netCDF4 as nc
    from .utils import log

    # Dicts with keys=target PFTs, args=list of source PFTs
    #forestToBare = {0:list(range(1,9))}
    #forestToShrub = {9:[1,4,5], 10:[6,7], 11:[2,3,8]}
    vegToBare = {0:list(range(1,15))}

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
    fsurdat_checkValid(inPath)
    confirmDiff(inPath, outPath)

def smartDeforestation(inPath:str, outPath:str, grassFracs:_ndarray|None = None, latLonRatio:float|int = 3):
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
    import shutil
    import numpy as np
    import netCDF4 as nc
    from  scipy.interpolate import NearestNDInterpolator
    from .utils import log

    shutil.copy2(inPath, outPath) # NOTE From some non-rigorous testing, this requires the original file to not be currently open. The use of "with" in meanHeatFlux() and any other Python scripts, and avoiding opening the file in a notebook, should allow this copy function to work as intended.

    with nc.Dataset(outPath, 'r+') as data:
        PCT_NAT_PFT = data.variables['PCT_NAT_PFT'][:]

        if grassFracs is None:
            log('Getting ratios between grass PFTs')
            grassMask = [False] * PCT_NAT_PFT.shape[0]
            for grassId in _grassIds:
                grassMask[grassId] = True
            grasses = PCT_NAT_PFT[grassMask]

            grassTot = np.sum(grasses, axis=0)
            grassless = grassTot == 0
            grassTot[grassless] = np.nan # Avoid divide by error. Nans will propagate through and be handled by interpolation later

            grassFracs = grasses/grassTot

            # Fill empty data with nearest neighbour, prioritizing by a factor given above
            # This follows the papers listed above, which use the nearest zonal point, but is slightly more sophisticated by allowing some meridional shifts if the nearest zonal neighbour is absurdly far away.
            indices = np.indices(grassFracs.shape[1:])
            rows = indices[0].flatten() # Corresponds to latitude
            cols = indices[1].flatten() * latLonRatio # Correspons to longitude, hence multiplied by ratio
            indices = np.column_stack((rows, cols))

            indeces_noNans = indices[~grassless.flatten()] # Tells interpolation the distance between points
            grassFracs_noNans = grassFracs[:, ~grassless].T # Tells interpolation the value at points

            grassInterpolator = NearestNDInterpolator(indeces_noNans, grassFracs_noNans)

            indeces_nans = indices[grassless.flatten()]
            grassFracs[:, grassless] = grassInterpolator(indeces_nans).T

        log('Finding total percent forest PFT by location')
        woodedMask = [False] * PCT_NAT_PFT.shape[0]
        for woodedId in _forestIds + _shrubIds: # If wanting to change only forest or only shrub, this would be the line to change
            woodedMask[woodedId] = True

        forestTot = np.sum(PCT_NAT_PFT[woodedMask], axis=0)
        PCT_NAT_PFT[woodedMask] = 0

        log('Applying new grass percentages')
        # Could make this more vectorized by making a version of grassFracs that matches PCT_NAT_PFT's shape, with 0's for all non-grass PFTs. But that's less readable and uses extra memory. This runs fast enough for most conceivable use cases anyways.
        for i, grassId in enumerate(_grassIds):
            grassModifier = forestTot * grassFracs[i]
            PCT_NAT_PFT[grassId] += grassModifier

        data.variables['PCT_NAT_PFT'][:] = PCT_NAT_PFT

    log('Checking output file is valid to use as fsurdat, and is different from the input')
    fsurdat_checkValid(inPath)
    confirmDiff(inPath, outPath)

### SOM Forcing ###

def som_meanHeatFlux(path:str) -> float:
    """
    Finds the weighted mean heat flux convergence of the dataset at path. Although 'area' is provided in radians squared, no conversion to m^2 by Earth's radius is needed since the units cancel out (Wm^-2 * rad^2 / rad^2 = Wm^-2)

    :param path: Path to input file, from which area and heat flux convergence can be read.
    :type path: str
    :returns: The mean heat flux convergence (Wm^-2) from the data read in
    :rtype: float
    """
    import numpy as np
    import netCDF4 as nc

    with nc.Dataset(path, 'r') as ds:
        # Read in raw data as np ndarray (get rid of default masking)
        a = np.array(ds.variables['area'][:]) #rad^2 Surface area of each cell
        q = np.array(ds.variables['qdp'][:]) #Wm^-2 Heat flux convergence (net heat flux) of each cell

        mask = q < 1e30

        q_tot = np.sum(a * q * mask)
        a_tot = np.sum(a * mask)

        return q_tot/a_tot

def som_correctHeatFlux(inPath:str, q_bar:float, outPath:str|None = None) -> str:
    """
    Docstring for correctHeatFlux
    
    :param inPath: Path to input file, from which to make a corrected copy.
    :type inPath: str
    :param q_bar: The mean heat flux convergence corresponding to this data.
    :type q_bar: float
    :param outPath: The file to which a corrected copy will be written. By default, is constructed based on inPath.
    :type outPath: str or None, optional
    :returns: The path at which the corrected file is stored. Useful when the default argument (None) is used, and this function constructs the output file name.
    :rtype: str
    """
    import shutil
    import netCDF4 as nc

    if outPath is None:
        outPath = inPath[:-2] + 'corrected.nc'

    shutil.copy2(inPath, outPath) # NOTE From some non-rigorous testing, this requires the original file to not be currently open. The use of "with" or "close" in meanHeatFlux() and any other Python scripts, and avoiding opening the file in a notebook, should allow this copy function to work as intended.

    with nc.Dataset(outPath, 'r') as ds:
        if ds.variables is None:
            raise FileNotFoundError(f'Unable to create copy of netCDF file {inPath}. Confirm that the file is not currently open and retry.')

    with nc.Dataset(outPath, 'r+') as ds:
        ds.variables['qdp'][:] -= q_bar

    return outPath

def som_forcingChecker(inPath:str, outPath:str|None = None, q_tol:float = 1e-5):
    """
    Checks if a forcing file has a net zero heat flux convergence in the ocean, and corrects it if not.

    :param inPath: Path to file which will be checked and, possibly, modified.
    :type inPath: str
    :param outPath: The file to which a corrected copy will be written if needed. By default, is constructed based on inPath.
    :type outPath: str or None, optional
    :param q_tol: The allowed error (from 0) of mean heat flux convergence. If the mean has a greater value than q_tol, a correction is initiated.
    :type q_tol: float
    """
    import numpy as np
    from .utils import log

    q_bar = som_meanHeatFlux(inPath)
    log(f'Mean heat flux convergence is {q_bar} W/m^2')

    if np.abs(q_bar) > q_tol:
        log(f'Mean is greater than the tolerance, {q_tol}W/m^2. Correcting data...')
        outPath = som_correctHeatFlux(inPath, q_bar, outPath)
        log(f'All done. Corrected file is located at: {outPath}')
        log(f'Output has mean heat flux {som_meanHeatFlux(outPath)} W/m^2')
    else:
        log(f'Mean is less than tolerance, {q_tol} W/m^2, so no corrections are needed. Exiting...')

if __name__ == '__main__':
    ## Sample Fsurdat modification
    # originalFsurdatFile = '/project/rrg-mlague/cmopfer/cesm_cases/NdgParams_Ctrl_NoCrop/surfdata_1.9x2.5_simyr1850_glcmec10_c120927.nc'
    originalFsurdatFile = '/project/def-mlague/shared_sourcecode/cesm_source/cesm2_inputs/lnd/clm2/surfdata_map/surfdata_0.9x1.25_16pfts_simyr1850_c170428.nc'

    # out_file = '/project/def-mlague/cmopfer/surfdata_forestToShrub.nc'
    # modify_PCT_NAT_PFT(in_file, out_file)

    # newFsurdatFile = '/project/def-mlague/cmopfer/surfdata_woodedToGrass.nc'
    newFsurdatFile = '/project/def-mlague/cmopfer/surfdata_woodedToGrass_1850.nc'
    smartDeforestation(originalFsurdatFile, newFsurdatFile)

    ## Sample SOM File Correction
    somFile = '/project/def-mlague/shared_sourcecode/cesm_source/cesm2_inputs/ocn/docn7/SOM/pop_frc.b.e21.BW1850.f09_g17.CMIP6-piControl.001.190514.nc'
    som_forcingChecker(somFile)
