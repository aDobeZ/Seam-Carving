#修改内容：
#1.引入了skimage中计算local entropy的函数（localEntropy）(在你的task1中，实际上就是localEntropySkimage)
#2.main函数中，增加了计算灰度图的语句，并且修改了deleteOneRow和addKRow的参数个数，将灰度图直接输入
#3.deleteOneRow和addKRow中调用了localEntropy
#4.deleteOneRow中同时对灰度图进行了修改并且返回灰度图。
#5.已有改为torch的方法在该文件中也已经改为了torch
#待修改内容：
#1.只实现了横向
#2.不能同时对两个方向进行放缩。
#3.尚未实现两两种方法的比较。
#4.尚未实现bonus
from PIL import Image
import numpy as np
import numexpr as ne
import matplotlib.pyplot as plt
import cv2
import os
#from multiprocessing import Pool
import time
import skimage.filters.rank as sfr
from skimage.morphology import square

# NUM_OF_PROCESS = 8
# pool = Pool(processes=NUM_OF_PROCESS)
plt.ion()
#ne.set_num_threads(ne.detect_number_of_cores() // 2)
import torch
import torch.nn.functional as F

# gradient with pytorch
def computeGDTorch(npimg):
    tmp = npimg.astype(np.float32)
    tmp = torch.from_numpy(tmp)

    x = tmp.shape[0]
    y = tmp.shape[1]
    time = torch.ones((x,y)) * 5
    time[0, 0] = time[0, y - 1] = time[x - 1, 0] = time[x - 1, y - 1] = 3
    time[1: x - 1, 1: y - 1] += torch.ones((x - 2, y - 2)) * 3

    gdsum = torch.zeros((x, y, 3))
    V = torch.abs(tmp[0:x - 1, :, :] - tmp[1:x, :, :])
    H = torch.abs(tmp[:, 0:y - 1, :] - tmp[:, 1:y, :])
    lurd = torch.abs(tmp[0:x - 1, 0:y - 1, :] - tmp[1:x, 1:y, :])
    ldru = torch.abs(tmp[1:x, 0:y - 1, :] - tmp[0:x - 1, 1:y, :])

    gdsum += F.pad(V, (0, 0, 0, 0, 1, 0), "constant", 0)
    gdsum += F.pad(V, (0, 0, 0, 0, 0, 1), "constant", 0)
    gdsum += F.pad(H, (0, 0, 0, 1, 0, 0), 'constant', 0)
    gdsum += F.pad(H, (0, 0, 1, 0, 0, 0), 'constant', 0)
    gdsum += F.pad(lurd, (0, 0, 0, 1, 0, 1), 'constant', 0)
    gdsum += F.pad(lurd, (0, 0, 1, 0, 1, 0), 'constant', 0)
    gdsum += F.pad(ldru, (0, 0, 0, 1, 0, 1), 'constant', 0)
    gdsum += F.pad(ldru, (0, 0, 1, 0, 1, 0), 'constant', 0)

    '''
    gdsum[0:x - 1, :, :] += V
    gdsum[1:x, :, :] += V
    gdsum[:, 0:y - 1, :] += H
    gdsum[:, 1:y, :] += H
    gdsum[0:x - 1, 0:y - 1, :] += lurd
    gdsum[1:x, 1:y, :] += lurd
    gdsum[0:x - 1, 1:y, :] += ldru
    gdsum[1:x, 0:y - 1, :] += ldru
    '''
    gdsum = gdsum.sum(dim=2) / 3
    gdsum = gdsum / time
    return gdsum

def localEntropy(img):
    return sfr.entropy(img, square(9))

def computeGD(npimg):
    tmp = npimg
    tmp = tmp.astype('double')
    x = tmp.shape[0]
    y = tmp.shape[1]
    time = np.ones((x,y)) * 5
    time[0,0] = time[0,y-1] = time[x-1,0] = time[x-1,y - 1] = 3
    time[1 : x - 1, 1 : y - 1] += np.ones((x-2,y-2)) * 3
    gdsum = np.zeros((x,y,3))
    V = np.fabs(tmp[0:x-1,:,:]-tmp[1:x,:,:])
    H = np.fabs(tmp[:,0:y-1,:]-tmp[:,1:y,:])
    lurd = np.fabs(tmp[0:x-1,0:y-1,:]-tmp[1:x,1:y,:])
    ldru = np.fabs(tmp[1:x,0:y-1,:]-tmp[0:x-1,1:y,:])
    gdsum[0:x-1,:,:] += V
    gdsum[1:x,:,:] += V
    gdsum[:,0:y-1,:] += H
    gdsum[:,1:y,:] += H
    gdsum[0:x-1,0:y-1,:] += lurd
    gdsum[1:x,1:y,:] += lurd
    gdsum[0:x-1,1:y,:] += ldru
    gdsum[1:x,0:y-1,:] += ldru
    gdsum=gdsum.sum(axis=2)/3
    gdsum=gdsum / time
    return gdsum

def showGDimg(gdimg):
    plt.figure(figsize=(19.2, 10.8))
    plt.title("gradient image")
    plt.imshow(Image.fromarray((gdimg / gdimg.max() * 255).astype(np.uint8)))
    plt.show()

def generatePathTorch(gdimg):
    lastDir = torch.zeros_like(gdimg, dtype=torch.uint8)
    energy = torch.zeros_like(gdimg)
    energy[0] = gdimg[0]
    tmp = torch.ones((3,gdimg.shape[1])) * np.inf
    t = torch.arange(tmp.shape[1])

    for i in range(1,gdimg.shape[0]):
        tmp[0,1:] = energy[i-1,:-1]
        tmp[1] = energy[i-1]
        tmp[2,:-1] = energy[i-1,1:]
        #tmp[0] = F.pad(energy[i-1,:-1], (1,0),'constant',np.inf)
        #tmp[1] = energy[i - 1]
        #tmp[2] = F.pad(energy[i-1,1:], (0,1), 'constant', np.inf)
        tmp += gdimg[i]
        energy[i], lastDir[i] = torch.min(tmp, dim=0)
        #lastDir[i] = torch.argmin(tmp, dim=0)
    return energy.numpy(), lastDir.numpy()

def addKRow(npimg,npgray,k):
    npGD = npimg
    pos=np.add.accumulate(np.ones((npimg.shape[0],npimg.shape[1]),dtype = np.uint32),axis = 1)-np.ones((npimg.shape[0],npimg.shape[1]),dtype = np.uint32)
    for j in range(20):
        for i in range(10):
            npimg, npGD , npgray,pos = addOneRow(npimg, npGD, npgray,pos)
            print('finished', j * 10 + i + 1, ", ", time.asctime(time.localtime(time.time())))
    return npimg
def addOneRow(npimg,npGD,npgray,pos):
    #print(pos)
    gdimg = computeGDTorch(npGD).numpy()
    #gdimg = computeGDTorch(npGD)
    entropy = localEntropy(npgray).astype(np.float32)
    gdimg = torch.from_numpy(gdimg + entropy)
    energy, lastDir = generatePathTorch(gdimg)
    #mask = np.full(gdimg.shape, True)

    last = np.argmin(energy[-1])
    y = npimg.shape[1] + 1
    retpos = np.ndarray((gdimg.shape[0], gdimg.shape[1] - 1),dtype=np.uint32)
    retGD = np.ndarray((gdimg.shape[0], gdimg.shape[1] - 1, 3),dtype=np.uint8)
    retimg = np.ndarray((gdimg.shape[0], y, 3),dtype=np.uint8)
    retgray = np.ndarray((gdimg.shape[0], gdimg.shape[1] - 1),dtype=np.uint8)
    for i in range(gdimg.shape[0] - 1, -1, -1):
        '''
        sum = npimg[i,pos[i,last],:]
        count = 1
        if last - 1 >= 0 and pos[i,last - 1] >= 0:
            count += 1
            sum += npimg[i,pos[i,last - 1],:]
        if last + 1 <pos.shape[1] and pos[i,last + 1] < npimg.shape[1]:
            count += 1
            sum += npimg[i,pos[i,last + 1],:]
        ave = (sum / count).astype(np.uint8)
        '''
        #我不求平均值啦！！！！气死我了老是出问题！！！
        retimg[i] = np.insert(npimg[i],pos[i,last] + 1, npimg[i,pos[i,last],:] ,axis = 0)
        pos[i,last:] += np.ones(gdimg.shape[1]-last,dtype=np.uint32)
        retpos[i] = np.delete(pos[i], last, axis=0)
        #retimg[i] = np.insert(npimg[i],last + 1, 0,axis = 0)
        retGD[i] = np.delete(npGD[i], last, axis=0)
        retgray[i] = np.delete(npgray[i], last, axis=0)
        last = last + lastDir[i][last] - 1
    return retimg, retGD,retgray,retpos #npimg[mask].reshape((gdimg.shape[0], gdimg.shape[1] - 1, 3))
def deleteOneRow(npimg,npgray):
    gdimg = computeGDTorch(npimg).numpy()
    #gdimg = computeGDTorch(npimg)
    entropy = localEntropy(npgray).astype(np.float32)
    gdimg = torch.from_numpy(gdimg + entropy)
    energy, lastDir = generatePathTorch(gdimg)
    #mask = np.full(gdimg.shape, True)

    last = np.argmin(energy[-1])
    retimg = np.ndarray((gdimg.shape[0], gdimg.shape[1] - 1, 3),dtype=np.uint8)
    retgray = np.ndarray((gdimg.shape[0], gdimg.shape[1] - 1),dtype=np.uint8)
    for i in range(gdimg.shape[0] - 1, -1, -1):
        #mask[i][last] = False
        retimg[i] = np.delete(npimg[i], last, axis=0)
        retgray[i] = np.delete(npgray[i], last, axis=0)
        last = last + lastDir[i][last] - 1
    return retimg, retgray #npimg[mask].reshape((gdimg.shape[0], gdimg.shape[1] - 1, 3))


if __name__ == '__main__':
    print('start, ', time.asctime(time.localtime(time.time())))
    img = Image.open('D:/pics/fuji.jpg')
    gray = img.convert('L')
    #plt.figure(figsize=(19.2, 10.8))
    #plt.imshow(img)
    #plt.show()

    npimg = np.array(img)
    npgray = np.array(gray)
    #showGDimg(computeGD(npimg))

    # plt.imshow(img.convert('L'))
    #print('ready, ', time.asctime(time.localtime(time.time())))
    #for j in range(10):
    #    for i in range(10):
    #        npimg,npgray = deleteOneRow(npimg,npgray)
    #        print('finished', j * 10 + i + 1, ", ", time.asctime(time.localtime(time.time())))
    npimg = addKRow(npimg,npgray,100)
    #print('finished, ', time.asctime(time.localtime(time.time())))
    newimg=Image.fromarray(npimg)
    newimg.save('D:/pics/testpy.jpg')