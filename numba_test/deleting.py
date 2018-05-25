from numba_test.gradient import computeGD
from numba_test.utils import transposeImg, transposeGray
from numba_test.energy import computeEnergy
import numpy as np
from numba import jit, njit, prange

@njit(parallel=True,nogil=True)
def generateColumn(gdimg):
    x = gdimg.shape[0]
    y = gdimg.shape[1]
    lastDir = np.zeros((x,y),np.int8)
    energy = np.zeros((x,y),np.uint32)
    for i in range(y):
        energy[0,i] = gdimg[0,i]
    for i in range(1,x):
        for j in range(y):
            idx = 0
            tmp = energy[i-1,j]
            if j != 0:
                a1 = energy[i-1,j-1]
                if a1 < tmp:
                    tmp = a1
                    idx = -1
            if j != y - 1:
                a2 = energy[i-1,j+1]
                if a2 < tmp:
                    tmp = a2
                    idx = 1
            lastDir[i,j] = idx
            energy[i,j] = tmp + gdimg[i,j]
    return energy, lastDir

@njit(parallel=True,nogil=True)
def deleteOneColumn(npimg,npgray,gdratio):
    energy, lastDir = generateColumn(computeEnergy(npimg, npgray,gdratio))

    lastArray = np.zeros((npimg.shape[0]),dtype=np.int16)
    lastArray[-1] = np.argmin(energy[-1])
    for i in range(npimg.shape[0] - 1, 0, -1):
        lastArray[i - 1] = lastArray[i] + lastDir[i,lastArray[i]]
    ret = np.zeros((npimg.shape[0], npimg.shape[1] - 1, 3), dtype=np.uint8)
    for i in prange(0, npimg.shape[0]):
        for j in range(0,lastArray[i]):
            ret[i, j, 0] = npimg[i, j, 0]
            ret[i, j, 1] = npimg[i, j, 1]
            ret[i, j, 2] = npimg[i, j, 2]
        for j in range(lastArray[i], ret.shape[1]):
            ret[i, j, 0] = npimg[i, j + 1, 0]
            ret[i, j, 1] = npimg[i, j + 1, 1]
            ret[i, j, 2] = npimg[i, j + 1, 2]
    return ret

@njit(parallel=True,nogil=True)
def deleteOneRow(npimg,npgray,gdratio):
    npimgt = transposeImg(npimg)
    npgrayt = transposeGray(npgray)
    return transposeImg(deleteOneColumn(npimgt, npgrayt,gdratio))
