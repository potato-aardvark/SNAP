#################################################################
# Name:     DiffFits.py                                         #
# Author:   Yuan Qi Ni                                          #
# Date:     July 14, 2017                                       #
# Function: Program uses DiffIm routine to subtract images.     #
#           Update /raw files and ObjData.py before running.    #
#################################################################

#essential modules
import numpy as np
import os
from glob import glob
import math

#essential files from SNAP
from SNAP.DiffIm import make_diff_image
from SNAP.Analysis.LCRoutines import*
from SNAP.MagCalc import*
from SNAP.Catalog import*
from SNAP.Photometry import*
from SNAP.Astrometry import*
from SNAP.PSFlib import*
#essential data
from ObjData import *

#reference files
bands = ['B','V','I']
bindex = {'B':0, 'V':1, 'I':2}
refs = ['../ref/'+Brefname, '../ref/'+Vrefname, '../ref/'+Irefname]
refmasks = ['.'.join(ref.split('.')[:-1])+".diff.fits" for ref in refs]

#make directory for diff images
with cd(wd+"/../"):
    if not os.path.isdir("diff"): os.mkdir('diff')
    if not os.path.isdir("conv"): os.mkdir('conv')

#for each band
for i in range(len(bands)):
    #get all band files
    files = sorted(glob('../raw/'+prefix+band[i]+'*.fits'))
    for n, filename in enumerate(files):
        #output filename
        diffname = '.'.join(filename.split('.')[:-1])+".diff.fits"
        diffname = '../diff/'+'/'.join(diffname.split('/')[2:])
        convname = '.'.join(filename.split('.')[:-1])+".conv.fits"
        convname = '../conv/'+'/'.join(convname.split('/')[2:])
        #mask image
        maskname='.'.join(filename.split('.')[:-1])+".mask.fits"
        maskname='../mask/'+'/'.join(maskname.split('/')[2:])
        cleanname='.'.join(filename.split('.')[:-1])+".clean.fits"
        cleanname='../clean/'+'/'.join(maskname.split('/')[2:])
        #other parameters
        fo = '.'.join(filename.split('.')[2:5])
        band = fo[0]

        #subtract if not already subtracted
        if os.path.exists(diffname) and os.path.exists(convname):
            print "Already subtracted "+filename
        else:
            print "subtracting "+filename
            #retrieve parameters from image
            Mtest = True
            try: #try to load image
                image, to, wcs = loadFits("../crop/"+filename, year=year, getwcs=True, verbosity=0)
            except FitsError:
                #image critically failed to load
                Mtest = False
                so = "FITS_ERROR"
                to = 0
                print "Critical error loading image!"
            if Mtest:
            try:
                PSF, PSFerr, Med, Noise = magnitude(image, image, wcs, cattype, catname, (ra,dec), radius=size, psf=1, name=name, band=band, fwhm=5.0, limsnr=SNRnoise, satmag=satlvl, refmag=rellvl, fitsky=True, satpix=satpix, verbosity=0, diagnosis=True)
                #image fwhm
                fwhm = np.mean(E2moff_toFWHM(*PSF[:-1]))
                if fwhm == 0:
                    raise PSFError('Unable to perform photometry on reference stars.')
                #image size
                imsize = np.mean(image.shape)
                #image negative limit
                ilim = Med - 10*Noise
                #check if mask already created
                if os.path.exists(maskname):
                    print "Already created mask for: "+filename
                else:
                    print "Creating mask for: "+filename
                    crmask, cleanarr = detect_cosmics(image, sigclip=4.0, readnoise=Noise, satlevel=satpix, psffwhm=fwhm, psfsize=2.5*fwhm)
                    hdu = fits.PrimaryHDU(crmask.astype(int))
                    hdu.header = hdr
                    hdu.writeto(maskname)
                    hdu = fits.PrimaryHDU(cleanarr)
                    hdu.header = hdr
                    hdu.writeto(cleanname)
                #subtract reference image
                make_diff_image(filename, refs[i], diffname, convname,
                                fwhm=fwhm, imsize=imsize,
                                tmp_sat=reflims[i][0], src_sat=satpix,
                                tmp_neg=reflims[i][1], src_neg=ilim,
                                tmp_mask=refmasks[i], src_mask=maskname,
                                "DITemp"+str(n))
            except PSFError:
                Mtest = False
                print "PSF can't be extracted!"
                print "Not performing subtraction."
            except: #General catastrophic failure
                Mtest = False
                print "Unknown catastrophic failure!"
                print "Not performing subtraction."


