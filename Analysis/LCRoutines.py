#################################################################
# Name:     LCRoutines.py                                       #
# Author:   Yuan Qi Ni                                          #
# Version:  Oct, 19, 2016                                       #
# Function: Program contains various routines for manipulating  #
#           multi-band light curve files and arrays.            #
#           In a MagCalc light curve, fluxes are more           #
#           informative than magnitudes about object brightness #
#           and SNRs are more informative than limiting         #
#           magnitudes about the reliability of a detection.    #
#           Hence whenever fluxes and SNR are given, they will  #
#           generally "take precendence" over magnitude and     #
#           limiting magnitude where determinations of          #
#           reliability are concerned.                          #
#################################################################

#essential modules
import numpy as np

#################################################################
# String Formatting Functions                                   #
#################################################################

#function: places right-aligned string in a string of space-padded chars
def padstr(string, l):
    '''
    ######################################################
    # Input                                              #
    # -------------------------------------------------- #
    # string: str to be padded                           #
    #      l: length of padded str                       #
    # -------------------------------------------------- #
    # Output                                             #
    # -------------------------------------------------- #
    # string: right-aligned space padded str of length l #
    ######################################################
    '''
    pad = l - len(string)
    for i in range(pad):
        string = " "+string
    return string

#function: places left-aligned string in a string of space-padded chars
def padstl(string, l):
    '''
    ######################################################
    # Input                                              #
    # -------------------------------------------------- #
    # string: str to be padded                           #
    #      l: length of padded str                       #
    # -------------------------------------------------- #
    # Output                                             #
    # -------------------------------------------------- #
    # string: left-aligned space padded str of length l  #
    ######################################################
    '''
    pad = l - len(string)
    for i in range(pad):
        string = string+" "
    return string

#function: split value(error) format into value
def splitval(string):
    '''
    ######################################
    # Input                              #
    # ---------------------------------- #
    # string: value(error) in str format #
    # ---------------------------------- #
    # Output                             #
    # ---------------------------------- #
    #       : value in float format      #
    ######################################
    '''
    try :
        return float(string.split('(')[0])
    except ValueError:
        return string
    
#function: split value(error) format into error
def spliterr(string):
    '''
    ######################################
    # Input                              #
    # ---------------------------------- #
    # string: value(error) in str format #
    # ---------------------------------- #
    # Output                             #
    # ---------------------------------- #
    #       : error in float format      #
    ######################################
    '''
    try:
        return float(string.split('(')[1].split(')')[0])/100.0
    except IndexError:
        return string
    
#function: format value and error as value(error)
def valerr(val, err):
    '''
    #########################################
    # Input                                 #
    # ------------------------------------- #
    #    val: value in float format         #
    #    err: error in float format         #
    # ------------------------------------- #
    # Output                                #
    # ------------------------------------- #
    #       : value(error) in string format #
    #########################################
    '''
    return ('%.3f'%val)+'('+str(int(err*1000))+')'

#################################################################
# Light Curve Processing Functions                              #
#################################################################

#function: split data formatting in light curve mag(err)
def LCsplit(valerrs):
    '''
    #####################################################################
    # Input                                                             #
    # ----------------------------------------------------------------- #
    # valerrs: list of light curves (eg. in different bands [B, V, I])  #
    #          where each is an array of value(error) in string format. #
    # ----------------------------------------------------------------- #
    # Output                                                            #
    # ----------------------------------------------------------------- #
    #    mags: array of light curves where each is an array of floats   #
    #          representing the magnitude value.                        #
    #    errs: array of light curves where each is an array of floats   #
    #          representing the magnitude error.                        #
    #####################################################################
    '''
    mags, errs = [[]]*len(valerrs), [[]]*len(valerrs)
    for i, valerr in enumerate(valerrs):
        mags[i] = np.array([splitval(string) for string in valerr])
        errs[i] = np.array([spliterr(string) for string in valerr])
    return mags, errs

#function: filter bad data from light curve
def LCpurify(ts, mags, errs, strs=None, fluxes=None, snrs=None, nthres=None, lims=None, fs=None, ras=None, decs=None, terrs=None, flags=None, aflag=None):
    '''
    #######################################################################
    # Input                                                               #
    # ------------------------------------------------------------------- #
    #   mags: list of light curves (eg. in different bands [B, V, I])     #
    #         where each is an array of magnitudes in float.              #
    #                                                                     #
    #   errs: list of light curves (eg. in different bands [B, V, I])     #
    #         where each is an array of magnitude errors in float.        #
    #                                                                     #
    #     ts: list of time arrays (eg. [tB, tV, tI]) where each is an     #
    #         array of time (in float) corresponding to the light curve.  #
    #                                                                     #
    #   strs; list of string arrays (eg. [sB, sV, sI]) where each is an   #
    #         array of str comments accompanying the light curve.         #
    #                                                                     #
    # fluxes; list of flux arrays (eg. [pB, pV, pI]) where each is an     #
    #         array of flux (in float) corresponding to the light curve.  # 
    #                                                                     #
    #   snrs; list of snr arrays (eg. [nB, nV, nI]) where each is an      #
    #         array of snr (in float) corresponding to the light curve.   # 
    #                                                                     #
    # nthres; float threshold SNR to flag data as proper detection.       #
    #         If given, routine would purge all corresponding light curve #
    #         values to snrs below above SNR threshold.                   #
    #                                                                     #
    #   lims; list of limiting magnitude arrays (eg. [Blim, Vlim, Ilim])  #
    #         where each is an array of limiting magnitudes in float      #
    #         evaluated at each sample of its corresponding light curve.  #
    #         If given, routine would purge all corresponding light curve #
    #         values to magnitudes measured below detection threshold.    #
    #         Applied only if nthres not applied.                         #
    #                                                                     #
    #     fs; list of string names for each datapoint                     #
    #                                                                     #
    #    ras; list of float ra locations                                  #
    #   decs; list of float dec locations                                 #
    #                                                                     #
    #  terrs; list of time errors                                         #
    #                                                                     #
    #  flags; list of str flags defining what values in strs would cause  #
    #         all corresponding light curve values to be purged.          #
    #                                                                     #
    #  aflag; antiflag defining what value in strs would protect light    #
    #         curve values corresponding to a magnitude below the         #
    #         detection limit from purging.                               #
    #         "" indicates don't purge at all based on lims.              #
    # ------------------------------------------------------------------- #
    # Output                                                              #
    # ------------------------------------------------------------------- #
    #     ts: list of light curve time float arrays where bad elements    #
    #         defined by flags, snrs, and lims were purged.               #
    #                                                                     #
    #   mags: list of float magnitude light curves where bad elements     #
    #         defined by flags, snrs, and lims were purged.               #
    #                                                                     #
    #   errs: list of float error light curves where bad elements         #
    #         defined by flags, snrs, and lims were purged.               #
    #                                                                     #
    # fluxes; list of float flux light curves where bad elements          #
    #         defined by flags, snrs, and lims were purged.               # 
    #                                                                     #
    #   snrs; list of float snr light curves where bad elements           #
    #         defined by flags, snrs, and lims were purged.               #
    #                                                                     #
    #   lims; list of float limiting magnitude arrays (if given) where    #
    #         bad elements defined by flags, snrs, and lims were purged.  #
    #                                                                     #
    #     fs; list of string names for each datapoint where bad elements  #
    #         defined by flags, snrs, and lims were purged.               #
    #                                                                     #
    #    ras; list of float ra locations                                  #
    #   decs; list of float dec locations                                 #
    #         bad elements defined by flags, snrs, and lims were purged.  #
    #                                                                     #
    #  terrs; list of time errors                                         #
    #         bad elements defined by flags, snrs, and lims were purged.  #
    #######################################################################
    '''
    #for each band
    for i in range(len(ts)):
        #base index
        index = np.array([True]*len(ts[i]))
        #remove elements with flag value for each flag
        if flags is not None:
            for flag in flags:
                if nthres is not None:
                    #fluxes better than mags, check where fluxes are available
                    #presumably when you give fluxes, you give SNR
                    index = np.logical_and(index, fluxes[i]!=flag)
                else:
                    #use light curve only where mags are available
                    index = np.logical_and(index, mags[i]!=flag)
                    index = np.logical_and(index, errs[i]!=flag)
        #check for string comments
        if strs is not None:
            #str flag values
            sflags = ['BAD_IMAGE', 'SATURATED', 'FALSE_DET']
            #remove elements with bad sflag value
            if flags is not None:
                for sflag in sflags:
                    #apply filter based on strs
                    strlist = np.array([streach[-len(sflag):] for streach in strs[i]])
                    index = np.logical_and(index,strlist!=sflag)
        #check for SNR filter (better than limiting magnitudes)
        if nthres is not None:
            index = np.logical_and(index, snrs[i] >= nthres)
        #check for limiting magnitudes
        elif lims is not None:
            #remove elements with bad lim value or beyond detection limit
            index = np.logical_and(index, mags[i].astype(float) < lims[i])
        if aflag is not None:
            #antiflag prevents deletion of points below det lim
            matches = np.array([strs[i][j][:len(aflag)]==aflag for j in range(len(strs[i]))])
            index = np.logical_or(index, matches)

        mags[i] = mags[i][index]
        errs[i] = errs[i][index]
        ts[i] = ts[i][index]
        retlist = [ts, mags, errs]
        if fluxes is not None:
            fluxes[i] = fluxes[i][index]
            retlist += [fluxes]
        if snrs is not None:
            snrs[i] = snrs[i][index]
            retlist += [snrs]
        if strs is not None:
            strs[i] = strs[i][index]
        if lims is not None:
            lims[i] = lims[i][index]
            retlist += [lims]
        if fs is not None:
            fs[i] = fs[i][index]
            retlist += [fs]
        if ras is not None:
            ras[i] = ras[i][index]
            retlist += [ras]
        if decs is not None:
            decs[i] = decs[i][index]
            retlist += [decs]
        if terrs is not None:
            terrs[i] = terrs[i][index]
            retlist += [terrs]
    return retlist

#function: crop time segment from dataset
def LCcrop(t, t1, t2, M, M_err=None, F=None, SN=None, Mlim=None, terr=None):
    '''
    ##############################################
    # Input                                      #
    # ------------------------------------------ #
    #      M: array of magnitudes in light curve #
    #  M_err; array of magnitude errors          #
    #   Mlim; array of limiting magnitudes       #
    #      t: array of time                      #
    #   terr: array of time errors               #
    #     t1: start of time segment crop         #
    #     t2: end of time segment crop           #
    # ------------------------------------------ #
    # Output                                     #
    # ------------------------------------------ #
    #      t: cropped time array                 #
    #   terr: cropped array of time errors       #
    #      M: cropped magnitude array            #
    #  M_err; cropped error array                #
    #   Mlim; cropped limiting magnitude array   #
    ##############################################
    '''
    index = np.logical_and(t<t2,t>t1)
    retlist = [t[index],M[index]]
    if M_err is not None:
        retlist += [M_err[index]]
    if F is not None:
        retlist += [F[index]]
    if SN is not None:
        retlist += [SN[index]]
    if Mlim is not None:
        retlist += [Mlim[index]]
    if terr is not None:
        retlist += [terr[index]]
    return retlist

#function: return first difference (color) between a set of light curves
def LCcolors(ts, mags, errs):
    '''
    #######################################################################
    # Input                                                               #
    # ------------------------------------------------------------------- #
    #   mags: list of light curves (eg. in different bands [B, V, I])     #
    #         where each is an array of magnitudes in float.              #
    #                                                                     #
    #   errs: list of light curves (eg. in different bands [B, V, I])     #
    #         where each is an array of magnitude errors in float.        #
    #                                                                     #
    #     ts: list of time arrays (eg. [tB, tV, tI]) where each is an     #
    #         array of time (in float) corresponding to the light curve.  #
    # ------------------------------------------------------------------- #
    # Output                                                              #
    # ------------------------------------------------------------------- #
    #  tdiff: list of color curve time float arrays.                      #
    #                                                                     #
    #  diffs: list of float first difference color curves.                #
    #                                                                     #
    #  derrs: list of float errors color curves.                          #
    #######################################################################
    '''
    tdiff, diffs, derrs = [], [], []
    #for each adjacent pair of light curve in mags
    for i in range(len(ts)-1):
        #create common axis (ordered union)
        tdiff.append(np.sort(np.concatenate((ts[i],ts[i+1]))))
        #interpolate light curves on matching axis
        interp1 = np.interp(tdiff[i],ts[i],mags[i])
        interp1_err2 = np.interp(tdiff[i],ts[i],np.square(errs[i]))
        interp2 = np.interp(tdiff[i],ts[i+1],mags[i+1])
        interp2_err2 = np.interp(tdiff[i],ts[i+1],np.square(errs[i+1]))
        #take first difference with light curves
        diffs.append(interp1 - interp2)
        derrs.append(np.sqrt(interp1_err2 + interp2_err2))
    #return first difference light curves
    return tdiff, diffs, derrs

#function: return corrected B band magnitude based on V band correlation
def BVcorrectMag(ts, mags, errs, Bcol=0, Vcol=1, mBVr=0, mBVrerr=0):
    '''
    #######################################################################
    # Input                                                               #
    # ------------------------------------------------------------------- #
    #   mags: list of light curves (eg. in different bands [B, V, I])     #
    #         where each is an array of magnitudes in float.              #
    #                                                                     #
    #   errs: list of light curves (eg. in different bands [B, V, I])     #
    #         where each is an array of magnitude errors in float.        #
    #                                                                     #
    #     ts: list of time arrays (eg. [tB, tV, tI]) where each is an     #
    #         array of time (in float) corresponding to the light curve.  #
    #                                                                     #
    #   Bcol: index of B band column                                      #
    #   Vcol: index of V band column                                      #
    #                                                                     #
    #   mBVr: mean color of reference stars used mBVr=<B-V>_r             #
    #mBVrerr: error in above color                                        #
    # ------------------------------------------------------------------- #
    # Output                                                              #
    # ------------------------------------------------------------------- #
    #    tcs: list of time arrays.                                        #
    #                                                                     #
    #  magcs: list of corrected light curves.                             #
    #                                                                     #
    #  errcs: list of corrected errors.                                   #
    #######################################################################
    '''
    import copy
    tcs, magcs, errcs = copy.deepcopy(ts), copy.deepcopy(mags), copy.deepcopy(errs)
    #B band correlation with B-V
    c = 0.27
    #correct B band using Bout = (B-Vin)*c + Bin
    Bin, Bin_err = mags[Bcol], errs[Bcol]
    Vin = np.interp(ts[Bcol], ts[Vcol], mags[Vcol])
    Vin_err = np.interp(ts[Bcol], ts[Vcol], errs[Vcol])
    Bout = (Bin - c*Vin - c*mBVr)/(1.-c)
    Bout_err = np.sqrt(np.square(c*Vin_err)+np.square(Bin_err)+np.square(c*mBVrerr))/(1.-c)
    magcs[Bcol] = Bout
    errcs[Bcol] = Bout_err
    #return corrected light curves
    return tcs, magcs, errcs

#function: return corrected B band limiting magnitude based reference star B-V
def BVcorrectLim(ts, lims, Bcol=0, mBVr=0):
    '''
    #######################################################################
    # Input                                                               #
    # ------------------------------------------------------------------- #
    #   lims: list of det limits (eg. in different bands [B, V, I])       #
    #         where each is an array of magnitudes in float.              #
    #                                                                     #
    #     ts: list of time arrays (eg. [tB, tV, tI]) where each is an     #
    #         array of time (in float) corresponding to the light curve.  #
    #                                                                     #
    #   Bcol: index of B band column                                      #
    #                                                                     #
    #   mBVr: mean color of reference stars used mBVr=<B-V>_r             #
    # ------------------------------------------------------------------- #
    # Output                                                              #
    # ------------------------------------------------------------------- #
    #    tcs: list of time arrays.                                        #
    #                                                                     #
    #  limcs: list of corrected det limits.                               #
    #######################################################################
    '''
    import copy
    tcs, limcs = copy.deepcopy(ts), copy.deepcopy(lims)
    #B band correlation with B-V
    c = 0.27
    #correct B band using Bout = (B-Vin)*c + Bin
    Bin = lims[Bcol]
    Bout = Bin - c*mBVr
    limcs[Bcol] = Bout
    #return corrected light curves
    return tcs, limcs

#function: return corrected B band magnitude based on V band correlation
#only to be applied over short times, where B-V doesn't vary much
def BVcorrectFlux(ts, mags, errs, te, Fe, SNe, plot=True):
    '''
    #######################################################################
    # Input                                                               #
    # ------------------------------------------------------------------- #
    #   mags: list of light curves (eg. in different bands [B, V, I])     #
    #         where each is an array of magnitudes in float.              #
    #                                                                     #
    #   errs: list of light curves (eg. in different bands [B, V, I])     #
    #         where each is an array of magnitude errors in float.        #
    #                                                                     #
    #     ts: list of time arrays (eg. [tB, tV, tI]) where each is an     #
    #         array of time (in float) corresponding to the light curve.  #
    # ------------------------------------------------------------------- #
    # Output                                                              #
    # ------------------------------------------------------------------- #
    #    tcs: list of time arrays.                                        #
    #                                                                     #
    #  magcs: list of corrected light curves.                             #
    #                                                                     #
    #  errcs: list of corrected errors.                                   #
    #######################################################################
    '''
    import copy
    from scipy.optimize import curve_fit
    from SNAP.Analysis.Cosmology import flux_0
    from SNAP.Analysis.LCFitting import linfunc
    
    tce, Fce, SNce = copy.deepcopy(te), copy.deepcopy(Fe), copy.deepcopy(SNe)
    #B band correlation with B-V
    c = 0.27
    #correct B band
    Bin, Bin_err = Fe[0], Fe[0]/SNe[0]
    #compute B-V color
    tdiff, C, C_err = LCcolors(ts, mags, errs)
    tBV, BV, BV_err = tdiff[0], C[0], C_err[0]
    #take only relevant interval
    mask = np.logical_and(tBV>te[0][0], tBV<te[0][-1])
    tBV, BV, BV_err = tBV[mask], BV[mask], BV_err[mask]
    #interpolate
    popt, pcov = curve_fit(linfunc,tBV,BV,p0=[0.0,0.0],sigma=BV_err,absolute_sigma=True)
    perr = np.sqrt(np.diag(pcov))
    #color at flux epochs
    BVe = popt[0]*te[0] + popt[1]
    print popt, perr
    BVe_err = np.sqrt(perr[1]**2 + (te[0]*perr[0])**2)
    #plot fit
    if plot:
        import matplotlib.pyplot as plt
        print "Plotting color interpolation"
        plt.title("B-V fit interpolation")
        plt.errorbar(tBV, BV, yerr=BV_err, fmt='k-')
        plt.errorbar(te[0], BVe, yerr=BVe_err, fmt='g-')
        plt.xlabel("Time")
        plt.ylabel("B-V")
        plt.show()
    #correct flux
    Bout = Bin*np.power(10., (-c/(1.-c))*(BVe/2.5))
    Bout_err = Bout*np.sqrt((Bin_err/Bin)**2+(c*np.log(10)*BVe_err/(2.5*(1.-c)))**2)
    Fce[0] = Bout
    SNce[0] = Bout/Bout_err
    #return corrected light curves
    return tce, Fce, SNce

#function: load light curve from text file
def LCload(filenames, tcol, magcols, errcols=None, fluxcols=None, SNcols=None, SNthres=None, limcols=None, fcols=None, racols=None, deccols=None, terrcols=None, scols=None, flags=None, aflag=None, mode='single'):
    '''
    #######################################################################
    # Input                                                               #
    # ------------------------------------------------------------------- #
    #      mode: 'single' => read from single txt containing all bands.   #
    #             'multi' => read from many txt each containing one band. #
    #                                                                     #
    # filenames: string file name (single), or list of file names (multi) #
    #                                                                     #
    #      tcol: int location of time column.                             #
    #                                                                     #
    #   magcols: int location of magnitude column (multi) or location of  #
    #            magnitude columns (single).                              #
    #                                                                     #
    #   errcols; int location of error column (multi) or location of      #
    #            error columns (single).                                  #
    #                                                                     #
    #  fluxcols; int location of error column (multi) or location of      #
    #            error columns (single).                                  #
    #                                                                     #
    #    SNcols; int location of SNR column (multi) or location of        #
    #            error columns (single).                                  #
    #            If given, rows of light curve will be purged when        #
    #            SNcol below SNthres.                                     #
    #                                                                     #
    #   SNthres; float threshold SNR to flag data as proper detection.    #
    #                                                                     #
    #   limcols; int location of limiting magnitude column (multi) or     #
    #            location of limiting magnitude columns (single).         #
    #            If given, rows of light curve will be purged when        #
    #            measured magnitude is below detection threshold.         #
    #                                                                     #
    #     fcols; int location of filename indicator column (multi) or     #
    #            location of filename columns (single).                   #
    #                                                                     #
    #    racols; int location of RA column (if given)                     #
    #   deccols; int location of DEc column (if given)                    #
    #                                                                     #
    #  terrcols; int location of time error columns (if given)            #
    #                                                                     #
    #     scols; int location of comments column (multi) or location of   #
    #            comments columns (single).                               #
    #                                                                     #
    #     flags; list of str flags defining what values in scol would     #
    #            cause a row in the file to be purged.                    #
    #                                                                     #
    #     aflag; antiflag defining what value in strs would protect rows  #
    #            corresponding to a measured magnitude below the          #
    #            detection limit from purging.                            #
    #            "" indicates don't purge at all based on lims.           #
    # ------------------------------------------------------------------- #
    # Output                                                              #
    # ------------------------------------------------------------------- #
    #     ts: list of light curve time float arrays where bad elements    #
    #         defined by flags, snrs, and lims were purged.               #
    #                                                                     #
    #   mags: list of float magnitude light curves where bad elements     #
    #         defined by flags, snrs, and lims were purged.               #
    #                                                                     #
    #   errs: list of float error light curves where bad elements         #
    #         defined by flags, snrs, and lims were purged.               #
    #                                                                     #
    # fluxes; list of float flux light curves where bad elements          #
    #         defined by flags, snrs, and lims were purged.               # 
    #                                                                     #
    #   snrs; list of float snr light curves (if given) where bad         #
    #         elements defined by flags, snrs, and lims were purged.      #
    #                                                                     #
    #   lims; list of float limiting magnitude arrays (if given) where    #
    #         bad elements defined by flags, snrs, and lims were purged.  #
    #                                                                     #
    #     fs; list of filename arrays (if given) where bad elements       #
    #         defined by flags, snrs, and lims were purged.               #
    #                                                                     #
    #     ra; list of RA (if given)                                       #
    #    dec; list of DEC (if given)                                      #
    #                                                                     #
    #  terrs; list of terr (if given)                                     #
    #######################################################################
    '''
    #check load mode, multifile or singlefile
    if mode == 'single':
        #load time column
        t = np.loadtxt(filenames,usecols=(tcol,),comments=';',unpack=True)
        ts = [t]*len(magcols)
        #load mag columns
        mags = list(np.loadtxt(filenames,dtype=str,usecols=magcols,comments=';',unpack=True))
        #retrieve mag errors
        if errcols == 'valerr': #error columns in formatting
            #extract errors from magnitude
            mags, errs = LCsplit(mags)
        elif errcols is not None: #error columns in file
            #load err columns
            errs = list(np.loadtxt(filenames,dtype=str,usecols=errcols,comments=';',unpack=True))
        else: #no errors given
            errs = [np.array(['1.0']*len(t)) for t in ts]
        #retrieve fluxes
        if fluxcols is not None:
            #load flux columns
            fluxes = list(np.loadtxt(filenames,dtype=str,usecols=fluxcols,comments=';',unpack=True))
        else: #no fluxes given
            fluxes = [np.array(['1.0']*len(t)) for t in ts]
        if SNcols is not None:
            #load SNR column
            snrs = list(np.loadtxt(filenames,usecols=SNcols,comments=';',unpack=True))
        else: #no SNR given
            snrs = [np.array([-1.0]*len(t)) for t in ts]
        if limcols is not None:
            #load Mlims column
            lims = np.loadtxt(filenames,usecols=limcols,comments=';',unpack=True)
        else: #no lims given
            lims = [np.array([-1.0]*len(t)) for t in ts]

        #check if comment strings are given
        if scols is not None:
            #extract comments from files
            strs = np.loadtxt(filenames,dtype=str,usecols=scols,comments=';',unpack=True)
        else: #no strings given
            strs = [np.array(['_']*len(t)) for t in ts]

        #check if filename strings are given
        if fcols is not None:
            #extract comments from files
            fs = np.loadtxt(filenames,dtype=str,usecols=fcols,comments=';',unpack=True)
        else: #no strings given
            fs = [np.array(['_']*len(t)) for t in ts]

        #check if locations are given
        if racols is not None:
            #extract comments from files
            ras = np.loadtxt(filenames,usecols=racols,comments=';',unpack=True)
        else: #no strings given
            ras = [np.array([0]*len(t)) for t in ts]
        if deccols is not None:
            #extract comments from files
            decs = np.loadtxt(filenames,usecols=deccols,comments=';',unpack=True)
        else: #no strings given
            decs = [np.array([0]*len(t)) for t in ts]
        if terrcols is not None:
            #extract comments from files
            terrs = np.loadtxt(filenames,usecols=terrcols,comments=';',unpack=True)
        else: #no strings given
            terrs = [np.array([0]*len(t)) for t in ts]
            
    elif mode == 'multi':
        #load from each file
        ts, mags = [], []
        for filename in filenames:
            #load time column
            ts.append(np.loadtxt(filename,usecols=(tcol,),comments=';',unpack=True))
            #load mag column
            mags.append(np.loadtxt(filename,dtype=str,usecols=(magcols,),comments=';',unpack=True))
        #retrieve mag errors
        if errcols == 'valerr': #error columns in formatting
            #extract errors from magnitude
            mags, errs = LCsplit(mags)
        elif errcols is not None: #error columns in files
            #extract errors from files
            errs = []
            for filename in filenames:
                #load err columns
                errs.append(np.loadtxt(filename,dtype=str,usecols=(errcols,),comments=';',unpack=True))
        else: #no errors given
            errs = [np.array(['1.0']*len(t)) for t in ts]
        #retrieve fluxes
        if fluxcols is not None:
            #extract fluxes from files
            fluxes = []
            for filename in filenames:
                #load flux columns
                fluxes.append(np.loadtxt(filename,dtype=str,usecols=(fluxcols,),comments=';',unpack=True))
        else: #no fluxes given
            fluxes = [np.array(['1.0']*len(t)) for t in ts]
        #check if SNR are given
        if SNcols is not None:
            #extract SNR from files
            snrs = []
            for filename in filenames:
                #load SNR column
                snrs.append(np.loadtxt(filename,usecols=(SNcols,),comments=';',unpack=True))
        else: #no SNR given
            snrs = [np.array([-1.0]*len(t)) for t in ts]
        #check if limiting magnitudes are given
        if limcols is not None:
            #extract mlims from files
            lims = []
            for filename in filenames:
                #load comment column
                lims.append(np.loadtxt(filename,usecols=(limcols,),comments=';',unpack=True))
        else: #no lims given
            lims = [np.array([1.0]*len(t)) for t in ts]

        #check if comment strings are given
        if scols is not None:
            #extract comments from files
            strs = []
            for filename in filenames:
                #load comment column
                s = np.loadtxt(filename,dtype=str,usecols=(scols,),comments=';',unpack=True)
                strs.append(s)
        else:
            strs = [np.array(['_']*len(t)) for t in ts]

        #check if filename strings are given
        if fcols is not None:
            #extract comments from files
            fs = []
            for filename in filenames:
                #load comment column
                f = np.loadtxt(filename,dtype=str,usecols=(fcols,),comments=';',unpack=True)
                fs.append(f)
        else: #no strings given
            fs = [np.array(['_']*len(t)) for t in ts]

        #check if locations are given
        if racols is not None:
            #extract comments from files
            ras = []
            for filename in filenames:
                #load comment column
                ra = np.loadtxt(filename,usecols=(racols,),comments=';',unpack=True)
                ras.append(ra)
        else: #no strings given
            ras = [np.array([0]*len(t)) for t in ts]
        if deccols is not None:
            #extract comments from files
            decs = []
            for filename in filenames:
                #load comment column
                dec = np.loadtxt(filename,usecols=(deccols,),comments=';',unpack=True)
                decs.append(dec)
        else: #no strings given
            decs = [np.array([0]*len(t)) for t in ts]
        if terrcols is not None:
            #extract comments from files
            terrs = []
            for filename in filenames:
                #load comment column
                terr = np.loadtxt(filename,usecols=(terrcols,),comments=';',unpack=True)
                terrs.append(terr)
        else: #no strings given
            terrs = [np.array([0]*len(t)) for t in ts]
    
    #check if SN filter is applied
    if SNthres is not None:
        #filter out bad data with all information
        ts, mags, errs, fluxes, snrs, lims, fs, ras, decs, terrs = LCpurify(ts, mags, errs, strs=strs, fluxes=fluxes, snrs=snrs, nthres=SNthres, lims=lims, fs=fs, ras=ras, decs=decs, terrs=terrs, flags=flags, aflag=aflag)
    #check if SNR are given
    else:
        #check if limiting magnitudes are given
        if limcols is not None:
            #filter out bad data with all information
            ts, mags, errs, fluxes, snrs, lims, fs, ras, decs, terrs = LCpurify(ts, mags, errs, strs=strs, fluxes=fluxes, snrs=snrs, lims=lims, fs=fs, ras=ras, decs=decs, terrs=terrs, flags=flags, aflag=aflag)
        else:
            if flags is not None:
                #filter out bad data with all information
                ts, mags, errs, fluxes, snrs, fs, ras, decs, terrs = LCpurify(ts, mags, errs, strs=strs, fluxes=fluxes, snrs=snrs, fs=fs, ras=ras, decs=decs, terrs=terrs, flags=flags, aflag=aflag)
            
    #convert mags to float
    mags = [mag.astype(float) for mag in mags]
    retlist = [ts, mags]
    if errcols is not None:
        #convert errors to float
        errs = [err.astype(float) for err in errs]
        retlist += [errs]
    if fluxcols is not None:
        #convert fluxes to float
        fluxes = [flux.astype(float) for flux in fluxes]
        retlist += [fluxes]
    if SNcols is not None:
        retlist += [snrs]
    if limcols is not None:
        retlist += [lims]
    if fcols is not None:
        retlist += [fs]
    if racols is not None:
        retlist += [ras]
    if deccols is not None:
        retlist += [decs]
    if terrcols is not None:
        retlist += [terrs]
    #return arrays of data
    return retlist

#function: load light curve from dlt file
def DLT_load(filename, tcol, magcol, errcol):
    
    from SNAP.Astrometry import isot_day

    #load time column, convert to day of year
    t = np.loadtxt(filename,usecols=(tcol,),comments='#',unpack=True, dtype=str)
    year = t[0][:4]
    t = np.array([isot_day(time, year) for time in t])
    #load magnitudes, filter out nans
    mag = np.loadtxt(filename,usecols=(magcol,),comments='#',unpack=True)
    err = np.loadtxt(filename,usecols=(errcol,),comments='#',unpack=True)
    mask = np.logical_and(np.invert(np.isnan(mag)), np.invert(np.isnan(err)))
    t, mag, err = t[mask], mag[mask], err[mask]
    #find lims vs detections
    limmask = err < -900
    detmask = np.invert(limmask)
    tlim, lim = t[limmask], mag[limmask]
    t, mag, err = t[detmask], mag[detmask], err[detmask]
    #return detections and limits
    return t, mag, err, tlim, lim

#function: load light curve from swift file
def Swift_load(filename, bcol, tcol, magcol, errcol, limcol=None, bands=['UVW2','UVM2','UVW1','U','B','V']):

    from astropy.time import Time

    #load band column
    b = np.loadtxt(filename,usecols=(bcol,),comments='#',unpack=True,dtype='str')
    #load time column, convert to day of year
    t = np.loadtxt(filename,usecols=(tcol,),comments='#',unpack=True)
    year = Time(t[0], format='mjd').isot[:4]
    year_isot = year + '-01-01T00:00:00.000'
    year = Time(year_isot, format='isot', scale='utc').mjd
    t = t - year
    #load magnitudes, divide into bands
    mag = np.loadtxt(filename,usecols=(magcol,),comments='#',unpack=True)
    err = np.loadtxt(filename,usecols=(errcol,),comments='#',unpack=True)
    lim = np.loadtxt(filename,usecols=(limcol,),comments='#',unpack=True)
    ts, mags, errs, lims = [], [], [], []
    for band in bands:
        mask = b == band
        ts.append(t[mask])
        mags.append(mag[mask])
        errs.append(err[mask])
        lims.append(lim[mask])
    return ts, mags, errs, lims

#function: load light curve from LCOGT file
def LCOGT_load(filename, bcol, tcol, magcol, errcol, bands=['U','B','V','g','r','i']):

    from astropy.time import Time
    
    #load band column
    b = np.loadtxt(filename,usecols=(bcol,),comments='#',unpack=True,dtype='str')
    #load time column, convert to day of year
    t = np.loadtxt(filename,usecols=(tcol,),comments='#',unpack=True)
    year = Time(t[0], format='jd').isot[:4]
    year_isot = year + '-01-01T00:00:00.000'
    year = Time(year_isot, format='isot', scale='utc').jd
    t = t - year
    #load magnitudes, divide into bands
    mag = np.loadtxt(filename,usecols=(magcol,),comments='#',unpack=True)
    err = np.loadtxt(filename,usecols=(errcol,),comments='#',unpack=True)
    ts, mags, errs = [], [], []
    for band in bands:
        mask = b == band
        ts.append(t[mask])
        mags.append(mag[mask])
        errs.append(err[mask])
    return ts, mags, errs
