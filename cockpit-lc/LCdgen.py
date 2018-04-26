#################################################################
# Name:     LCgen.py                                            #
# Author:   Yuan Qi Ni                                          #
# Date:     July 10, 2017                                       #
# Function: Program uses MagCalc routine to generate light      #
#           curve file of magnitudes and limiting magnitudes.   #
#################################################################

#essential modules
import numpy as np
import os
from glob import glob
import math

#essential files from SNAP
from SNAP.Analysis.LCRoutines import *
from SNAP.MagCalc import*
from SNAP.Catalog import*
from SNAP.Photometry import*
from SNAP.Astrometry import*
#essential data
from ObjData import *

#observation filters
bands = ['B','V','I']
bindex = {'B':0, 'V':1, 'I':2}
#observatory positions
observatories = {'A':[210.9383,-31.2712,1143.0], 'S':[339.8104,-32.3789,1762.0], 'C':[70.8040,-30.1672,2167.0]}

#function which fills a row with column entries
def rowGen(to,fo,RAo,DECo,Io,SNo,Mo,Mo_err,Mlimo,so):
    sto = padstr("%.5f"%to,10)
    sfo = padstr(fo,27)
    sRAo = padstr("%.1f"%RAo,10)
    sDECo = padstr("%.1f"%DECo,10)
    sIo = padstr(str(Io)[:9],10)
    sSNo = padstr(str(SNo)[:5],10)
    sMo = padstr("%.3f"%Mo,10)
    sMo_err = padstr("%.3f"%Mo_err,10)
    sMlimo = padstr("%.3f"%Mlimo,10)
    ss = "   "+so
    out = '\n  '+sto+sfo+sRAo+sDECo+sIo+sSNo+sMo+sMo_err+sMlimo+ss
    return out
#fills first row with column headers
def headGen():
    sto = padstr("OBSDAY"+str(year),10)
    sfo = padstr("STRTXT",27)
    sRAo = padstr("RA_MC(\")",10)
    sDECo = padstr("DEC_MC(\")",10)
    sIo = padstr("Flux(uJy)",10)
    sSNo = padstr("SNR",10)
    sMo = padstr("MAG_MC",10)
    sMo_err = padstr("MAGERR_MC",10)
    sMlimo = padstr("LIM_MC",10)
    ss = "   "+"NOTE"
    out = "\n; "+sto+sfo+sRAo+sDECo+sIo+sSNo+sMo+sMo_err+sMlimo+ss
    return out

#generate output files
os.system('touch '+outBname)
os.system('touch '+outVname)
os.system('touch '+outIname)
outs = [outBname, outVname, outIname]
#write headers for BVI light curve output files
for i in range(len(bands)):
    outfile = open(outs[i], 'a')
    outfile.write("; SOURCE_RA_DEC\t"+str(ra)+"\t"+str(dec))
    outfile.write("\n; NUMBER_OF_REFERENCES\t"+str(nrefs[bindex[bands[i]]]))
    outfile.write("\n; "+str(user)+"\t"+str(t_now))
    outfile.write(headGen())
    outfile.close()

#search for fits files with which to construct light curve
files = sorted(glob('../conv/'+prefix+'B*.fits'))
diffs = sorted(glob('../diff/'+prefix+'B*.fits'))
refs = ['../ref/'+Brefname, '../ref/'+Vrefname, '../ref/'+Irefname]

#generate light curve
for i in range(len(files)):
    filename = files[i].split('/')[-1]
    diffname = diffs[i].split('/')[-1]
    print "Computing file "+str(i+1)+"/"+str(len(files))+": "+filename
    #decipher information from KMTNet filename convention
    fo = '.'.join(filename.split('.')[2:5])
    band = fo[0]

    #compute magnitude
    Mtest = True
    so = "_"
    try: #try to load image
        image, to, wcs = loadFits("../diff/"+diffname, year=year, getwcs=True, verbosity=0)
        catimage, to, wcs = loadFits("../conv/"+filename, year=year, getwcs=True, verbosity=0)
    except FitsError:
        #image critically failed to load
        Mtest = False
        so = "FITS_ERROR"
        to = 0
        print "Critical error loading image!"

    if Mtest:
        #get moon ephemeris
        obs = fo[-1]
        loc = observatories[obs]
        time = day_isot(to,year)
        RAmoon, DECmoon = moonEQC(time,loc)
        ALTmoon, AZmoon = moonLC(time,loc)
        #check if moon bright
        if ALTmoon > 15.0:
            so = "MOON_BRIGHT"
        elif ALTmoon > 0.0 and sepAngle((ra,dec),(RAmoon,DECmoon)) < 90.0:
            so = "MOON_BRIGHT"

    if Mtest:
        try:
            
            RAo, DECo, Io, SNo, Mo, Mo_err, Mlimo = magnitude(image, catimage, wcs, cattype, catname, (ra,dec), radius=size, psf=2, name=name, band=band, fwhm=5.0, limsnr=SNRnoise, satmag=satlvl, refmag=rellvl, verbosity=0)
            
            #check if MagCalc returns nonsense
            if any([math.isnan(Mo),math.isinf(Mo),math.isnan(Mo_err),math.isinf(Mo_err)]):
                Mo, Mo_err = -99.999, -99.999
            
            if any([math.isnan(Io),math.isinf(Io),math.isnan(SNo),math.isinf(SNo)]):
                Io, SNo = -99.99999, -99.99
                if any([math.isnan(Mlimo),math.isinf(Mlimo)]):
                    Mlimo = -99.999
                    RAo, DECo = -99.9, -99.9
                    Mtest = False
            
            if any([math.isnan(Mlimo),math.isinf(Mlimo)]):
                Mlimo = -99.999
                if any([math.isnan(Io),math.isinf(Io),math.isnan(SNo),math.isinf(SNo)]):
                    Io, SNo = -99.99999, -99.99
                    RAo, DECo = -99.9, -99.9
                    Mtest = False
                else:
                    RAo = RAo - ra
                    DECo = DECo - dec
            else:
                RAo = RAo - ra
                DECo = DECo - dec

        except PSFError: #if image PSF cant be extracted
            RAo, DECo, Io, SNo, Mo, Mo_err, Mlimo  = -99.9, -99.9, -99.99999, -99.99, -99.999, -99.999, -99.999
            so = "PSF_ERROR"
            Mtest = False
            print "PSF can't be extracted!"
        except: #General catastrophic failure
            RAo, DECo, Io, SNo, Mo, Mo_err, Mlimo  = -99.9, -99.9, -99.99999, -99.99, -99.999, -99.999, -99.999
            Mtest = False
            print "Unknown catastrophic failure!"

    else:
        RAo, DECo, Io, SNo, Mo, Mo_err, Mlimo  = -99.9, -99.9, -99.99999, -99.99, -99.999, -99.999, -99.999

    #check for total failure
    if not Mtest:
        so = so + "_BAD_IMAGE"
    else:
        if any([math.isnan(RAo),math.isinf(RAo),math.isnan(DECo),math.isinf(DECo)]):
            RAo, DECo = 0.0, 0.0
        if Mlimo < 0:
            so = "INCONV"

    #format output
    out = rowGen(to,fo,RAo,DECo,Io,SNo,Mo,Mo_err,Mlimo,so)
    print out+'\n'

    if band in bands:
        outfile = open(outs[bindex[band]], 'a')
        outfile.write(out)
        outfile.close()
