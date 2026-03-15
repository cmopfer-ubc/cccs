"""
Created Feb 26, 2026 by Camden Opfer

Checks that a SOM forcing file has net zero heat flux convergence and, if not, creates a modified file that corrects this.
"""

import shutil
import numpy as np
import netCDF4 as nc
from .utils import log

def som_meanHeatFlux(path:str) -> float:
    """
    Finds the weighted mean heat flux convergence of the dataset at path. Although 'area' is provided in radians squared, no conversion to m^2 by Earth's radius is needed since the units cancel out (Wm^-2 * rad^2 / rad^2 = Wm^-2)
    
    :param path: Path to input file, from which area and heat flux convergence can be read.
    :type path: str
    :returns: The mean heat flux convergence (Wm^-2) from the data read in
    :rtype: float
    """
    with nc.Dataset(path, 'r') as ds:
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
    if outPath is None:
        outPath = inPath[:-2] + 'corrected.nc'

    shutil.copy2(inPath, outPath) # NOTE From some non-rigorous testing, this requires the original file to not be currently open. The use of "with" in meanHeatFlux() and any other Python scripts, and avoiding opening the file in a notebook, should allow this copy function to work as intended.

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
    q_bar = som_meanHeatFlux(inPath)
    log(f'Mean heat flux convergence is {q_bar} W/m^2')

    if np.abs(q_bar) > q_tol:
        log(f'Mean is greater than the tolerance, {q_tol}W/m^2. Correcting data...')
        outPath = som_correctHeatFlux(inPath, q_bar, outPath)
        log(f'All done. Corrected file is located at: {outPath}')
        log(f'Output has mean heat flux {som_meanHeatFlux(outPath)} W/m^2')
    else:
        log(f'Mean is less than tolerance, {q_tol} W/m^2, so no corrections are needed. Exiting...')

if __name__=="__main__":
    file = '/project/def-mlague/shared_sourcecode/cesm_source/cesm2_inputs/ocn/docn7/SOM/pop_frc.b.e21.BW1850.f09_g17.CMIP6-piControl.001.190514.nc'
    som_forcingChecker(file)
