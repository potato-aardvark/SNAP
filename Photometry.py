#################################################################
# Name:     Photometry.py                                       #
# Author:   Yuan Qi Ni                                          #
# Version:  August 25, 2016                                     #
# Function: Program contains functions that perform essential   #
#           photometric tasks.                                  #
#################################################################

#essential modules
import numpy as np

#function: estimate snr using mag_err
def limErr(snrerr):
    return (2.512/np.log(10))/snrerr

#function: distance metric on images
def dist(x1, y1, x2, y2):
    #Euclidean distance
    return np.sqrt(np.square(x1-x2)+np.square(y1-y2))

#function: photmetric aperture at (x0,y0) from r1 to r2
def ap_get(image, x0, y0, r1, r2):
    xaxis = np.arange(max([0,x0-r2]), min(image.shape[0],x0+r2+1), dtype=int)
    yaxis = np.arange(max([0,y0-r2]), min(image.shape[0],y0+r2+1), dtype=int)
    api = np.array([image[y][x] for x in xaxis for y in yaxis if (dist(x0,y0,x,y)<=r2 and dist(x0,y0,x,y)>=r1)])
    apx = np.array([x for x in xaxis for y in yaxis if (dist(x0,y0,x,y)<=r2 and dist(x0,y0,x,y)>=r1)])
    apy = np.array([y for x in xaxis for y in yaxis if (dist(x0,y0,x,y)<=r2 and dist(x0,y0,x,y)>=r1)])
    return api, apx, apy

#function: synthesize star from PSF and aperture
def ap_synth(psf, popt, r):
    if psf == D2moff:
        #PSF is moffat
        A,a,b,x0,y0 = popt[0],popt[1],popt[2],popt[3],popt[4]
        xaxis = np.arange(x0-r, x0+r+1, dtype=int)
        yaxis = np.arange(y0-r, y0+r+1, dtype=int)
        ap = np.array([psf((x,y),*popt) for x in xaxis for y in yaxis if (dist(x0,y0,x,y)<=r)])
        return ap

#function: general 2D background sky plane
def D2plane((x, y), a, b, c):
    return (a*x + b*y + c).ravel()

#function: fits background sky plane and noise
def SkyFit(image, x0, y0, fwhm=5.0, verbosity=0):

    from scipy.optimize import curve_fit
    
    #get background sky annulus
    inner_annulus, inner_x, inner_y = ap_get(image, x0, y0, 4*fwhm, 5*fwhm)
    outer_annulus, outer_x, outer_y = ap_get(image, x0, y0, 6*fwhm, 7*fwhm)
    #get first estimate mean background value
    innerB = np.mean(inner_annulus)
    outerB = np.mean(outer_annulus)
    skyB = outerB if outerB<innerB else innerB
    skyi, skyx, skyy = (outer_annulus, outer_x, outer_y) if outerB<innerB else (inner_annulus, inner_x, inner_y)
    #fit sky background
    try:
        skypopt, skypcov = curve_fit(D2plane, (skyx, skyy), skyi, p0=[0,0,skyB], maxfev=100000)
        try:
            #try to calculate fit error
            skyperr = np.sqrt(np.diag(skypcov))
        except:
            try:
                #take closer initial conditions
                skypopt, skypcov = curve_fit(D2plane, (skyx, skyy), skyi, p0=skypopt, maxfev=100000)
                skyperr = np.sqrt(np.diag(skypcov))
            except:
                skyperr = [0]*3
        #calculate sky noise near source
        skyTheo = D2plane((skyx,skyy),*skypopt)
        skyN = np.std(skyi-skyTheo)
        #calculate goodness of fit
        skyX2dof = np.square((skyi-skyTheo)/skyN)/(len(skyi)-3)
    except:
        #catastrophic failure of sky plane fitting
        print "Sky fitting catastrophic failure"
        skypopt = [0]*3
        skyperr = [0]*3
        skyX2dof = 0
        skyN = 0
    if verbosity > 0:
        print "sky plane fit parameters"
        print "[a, b, c] = "+str(skypopt)
        print "errors = "+str(skyperr)
    #return sky plane, sky noise, and goodness of fit
    return skypopt, skyperr, skyX2dof, skyN

#function: general 2D moffat function
def D2moff((x, y), A, a, b, x0, y0):
    """
    This is the most frequently used function to model PSFs,
    but it is not perfect! Expect residuals!
    Residuals of fit is not a good estimator of noise in PSF.
    Don't make the same mistake as I did.
    Problem fixed in 2016, noise now measured from sky, not from residual.
    """
    m = A*np.power(1+np.square(dist(x,y,x0,y0)/a),-b)
    return m.ravel()
#function: moffat a, b paramters -> fwhm
def moff_toFWHM(a,b):
    if b != 0 and np.power(2,1.0/b)-1 > 0:
        return np.abs(a)*(2*np.sqrt(np.power(2,1.0/b)-1))
    else:
        return 0
#function: integrate moffat function
def moff_integrate(A,a,b,A_err=0,a_err=None,b_err=None,f=0.9):
    if b != 0 and np.power(2,1.0/b)-1 > 0:
        Int = f*np.pi*np.square(a)*A/(b-1)
        opt_r = a*np.sqrt(np.power(1 - f,1/(1-b)) - 1)
        if a_err is None or b_err is None:
            return Int, opt_r
        else:
            #calculate errors
            sig = Int*np.sqrt((2*a_err/a)**2+(A_err/A)**2+(b_err/(b-1))**2)
            return Int, sig, opt_r 
    else:
        return 0

#function: clean out cosmic rays and junk from PSF
def PSFclean(x,y,psf,skyN):
    #remove pixels that are 5sigma below the noise floor(dead? hot?)
    x = x[psf+5*skyN>0]
    y = y[psf+5*skyN>0]
    psf = psf[psf+5*skyN>0]
    return x, y, psf

#function: check veracity of PSF fit
def PSFverify(PSFpopt, x0=None, y0=None):
    if len(PSFpopt) == 5: #moffat PSF
        #extract values from PSF
        A = PSFpopt[0]
        a = abs(PSFpopt[1])
        b = PSFpopt[2]
        X0 = PSFpopt[3]
        Y0 = PSFpopt[4]
        FWHM = moff_toFWHM(a, b)
        #check all manner of ridiculous scenarios
        if FWHM > 20.0 or FWHM < 1.0:
            #unphysical FWHM
            return False
        elif dist(X0,Y0,x0,y0)>10:
            #not our source
            return False
        elif b <= 1.0:
            #divergent PSF
            return False
        else:
            #seems legit
            return True
    if len(PSFpopt) == 2: #moffat shape
        #extract values from PSF
        a = abs(PSFpopt[0])
        b = PSFpopt[1]
        FWHM = moff_toFWHM(a, b)
        #check all manner of ridiculous scenarios
        if FWHM > 20.0 or FWHM < 1.0:
            #unphysical FWHM
            return False
        elif b <= 1.0:
            #divergent PSF
            return False
        else:
            #seems legit
            return True

#function: extracts PSF from source
def PSFextract(image, x0, y0, fwhm=5.0, fitsky=True, verbosity=0):

    from scipy.optimize import curve_fit

    #fit sky background in an annulus
    skypopt, skyperr, skyX2dof, skyN = SkyFit(image, x0, y0, fwhm=5.0, verbosity=0)

    #get fit box to fit psf
    fsize = 3
    x = np.arange(x0-fsize*fwhm,x0+fsize*fwhm+1,dtype=int)
    y = np.arange(y0-fsize*fwhm,y0+fsize*fwhm+1,dtype=int)
    intens = np.array([image[yi][xi] for yi in y for xi in x])
    x, y = np.meshgrid(x, y)
    x = x.ravel()
    y = y.ravel()
    #filter out bad pixels
    #x, y, intens = PSFclean(x, y, intens, skyN)
    if fitsky:
        #get sky background
        sky = D2plane((x,y),*skypopt)
        #subtract sky background
        intens = intens - sky
    
    try:
        #fit 2d psf to background subtracted source light
        est = [image[int(y0)][int(x0)],fwhm/0.7914,4.765,x0,y0]
        PSFpopt, PSFpcov = curve_fit(D2moff, (x, y), intens, sigma=np.sqrt(np.absolute(intens)+skyN**2), p0=est, maxfev=1000000)
        try:
            #try to calculate fit error
            PSFperr = np.sqrt(np.diag(PSFpcov))
        except:
            try:
                #take closer initial conditions
                PSFpopt, PSFpcov = curve_fit(D2moff, (x, y), intens, sigma=np.sqrt(np.absolute(intens)+skyN**2) , p0=PSFpopt, maxfev=100000)
                PSFperr = np.sqrt(np.diag(PSFpcov))
            except:
                PSFperr = [0]*5
        #calculate goodness of fit
        I_theo = D2moff((x, y),*PSFpopt)
        X2dof = np.sum(np.square((intens-I_theo)/np.sqrt(intens+skyN**2)))/(len(intens)-6)
    except:
        #catastrophic failure of PSF fitting
        print "PSF fitting catastrophic failure"
        PSFpopt = [0]*5
        PSFperr = [0]*5
        X2dof = 0
    if verbosity > 0:
        print "PSF moffat fit parameters"
        print "[A,a,b,X0,Y0] = "+str(PSFpopt)
        print "parameter errors = "+str(PSFperr)
        print "Chi2 = "+str(X2dof)
    #get values from fit
    A = PSFpopt[0]
    a = abs(PSFpopt[1])
    b = PSFpopt[2]
    X0 = PSFpopt[3]
    Y0 = PSFpopt[4]
    PSFpopt = [A, a, b, X0, Y0]
    FWHM = moff_toFWHM(a, b)
        
    #graph fits if verbosity is high enough
    if verbosity > 1 and FWHM != 0:
        PSF_plot(image, PSFpopt, X2dof, skypopt, skyN, fitsky, fsize)
    elif verbosity > 1 and FWHM == 0:
        print "Unable to plot, catastrophic failure to extract PSF"

    #check if fit is ridiculous for bright object, give back no fit
    if PSFverify(PSFpopt, x0, y0) and PSFpopt[0]>0:
        return PSFpopt, PSFperr, X2dof, skypopt, skyN
    else:
        return [0]*5, [0]*5, 0, [0]*3, skyN
    
#function: fits PSF to source
def PSFfit(image, PSF, PSFerr, x0, y0, fitsky=True, verbosity=0):

    from scipy.optimize import curve_fit

    #get given fit parameters
    a, aerr = abs(PSF[0]), PSFerr[0]
    b, berr = PSF[1], PSFerr[1]
    FWHM = moff_toFWHM(a, b)

    #fit sky background in an annulus
    skypopt, skyperr, skyX2dof, skyN = SkyFit(image, x0, y0, fwhm=5.0, verbosity=0)
    
    #get fit box to fit parameters to psf
    fsize = 3
    x = np.arange(x0-fsize*FWHM,x0+fsize*FWHM+1,dtype=int)
    y = np.arange(y0-fsize*FWHM,y0+fsize*FWHM+1,dtype=int)
    intens = np.array([image[yi][xi] for yi in y for xi in x])
    x, y = np.meshgrid(x, y)
    x = x.ravel()
    y = y.ravel()
    #filter out bad pixels
    #x, y, intens = PSFclean(x, y, intens, skyN)
    if fitsky:
        #get sky background
        sky = D2plane((x,y),*skypopt)
        #subtract sky background
        intens = intens - sky
    
    try:
        #fit 2d fixed psf to background subtracted source light
        est = [image[int(y0)][int(x0)],x0,y0]
        fitpopt, fitpcov = curve_fit(lambda (x, y),A,x0,y0: D2moff((x, y),A,a,b,x0,y0), (x,y), intens, sigma=np.sqrt(np.absolute(intens)+skyN**2), p0=est, maxfev=100000)
        try:
            #try to calculate fit error
            fitperr = np.sqrt(np.diag(fitpcov))
        except:
            try:
                #take closer initial conditions
                fitpopt, fitpcov = curve_fit(lambda (x, y),A,x0,y0: D2moff((x, y),A,a,b,x0,y0), (x,y), intens, sigma=np.sqrt(np.absolute(intens)+skyN**2), p0=fitpopt, maxfev=100000)
                fitperr = np.sqrt(np.diag(fitpcov))
            except:
                fitperr = [0]*3
        #parameters fitted to source
        A, Aerr = fitpopt[0], fitperr[0]
        X0, X0err = fitpopt[1], fitperr[1]
        Y0, Y0err = fitpopt[2], fitperr[2]
        PSFpopt = [A,a,b,X0,Y0]
        PSFperr = [Aerr,aerr,berr,X0err,Y0err]
        #calculate goodness of fit
        I_theo = D2moff((x, y),*PSFpopt)
        X2dof = np.sum(np.square((intens-I_theo)/np.sqrt(np.abs(intens))))/(len(intens)-6)
    except:
        #catastrophic failure of PSF fitting
        print "PSF fitting catastrophic failure"
        PSFpopt = [0]*5
        PSFperr = [0]*5
        X2dof = 0
    if verbosity > 0:
        print "PSF moffat fit parameters"
        print "[A,a,b,X0,Y0] = "+str(PSFpopt)
        print "parameter errors = "+str(PSFperr)
        print "Chi2 = "+str(X2dof)

    #graph fits if verbosity is high enough
    if verbosity > 1 and FWHM != 0:
        PSF_plot(image, PSFpopt, X2dof, skypopt, skyN, fitsky, fsize)
    elif verbosity > 1 and FWHM == 0:
        print "Unable to plot, FWHM of PSF is nonsensical"
        
    #check if fit is ridiculous
    if PSFverify(PSFpopt, x0, y0):
        #not ridiculous, give back fit
        return PSFpopt, PSFperr, X2dof, skypopt, skyN
    else:
        return [0]*5, [0]*5, 0, [0]*3, skyN

#function: scales PSF to source location
def PSFscale(image, PSF, PSFerr, x0, y0, fitsky=True, verbosity=0):
    
    from scipy.optimize import curve_fit
    
    #fit sky background in an annulus
    skypopt, skyperr, skyX2dof, skyN = SkyFit(image, x0, y0, fwhm=5.0, verbosity=0)
    
    #get given fit parameters
    a, aerr = abs(PSF[0]), PSFerr[0]
    b, berr = PSF[1], PSFerr[1]
    FWHM = moff_toFWHM(a, b)
    
    #get fit box to fit parameters to psf
    fsize = 3
    x = np.arange(x0-fsize*FWHM,x0+fsize*FWHM+1,dtype=int)
    y = np.arange(y0-fsize*FWHM,y0+fsize*FWHM+1,dtype=int)
    intens = np.array([image[yi][xi] for yi in y for xi in x])
    x, y = np.meshgrid(x, y)
    x = x.ravel()
    y = y.ravel()
    #filter out bad pixels
    #x, y, intens = PSFclean(x, y, intens, skyN)
    if fitsky:
        #get sky background
        sky = D2plane((x,y),*skypopt)
        #subtract sky background
        intens = intens - sky
    
    try:
        #fit 2d fixed psf to background subtracted source light
        est = [image[int(y0)][int(x0)]]
        fitpopt, fitpcov = curve_fit(lambda (x, y),A: D2moff((x, y),A,a,b,x0,y0), (x,y), intens, sigma=np.sqrt(np.absolute(intens)+skyN**2), p0=est, maxfev=100000)
        try:
            #try to calculate fit error
            fitperr = np.sqrt(np.diag(fitpcov))
        except:
            try:
                #take closer initial conditions
                fitpopt, fitpcov = curve_fit(lambda (x, y),A: D2moff((x, y),A,a,b,x0,y0), (x,y), intens, sigma=np.sqrt(np.absolute(intens)+skyN**2), p0=fitpopt, maxfev=100000)
                fitperr = np.sqrt(np.diag(fitpcov))
            except:
                fitperr = [0]
        #parameters fitted to source
        A, Aerr = fitpopt[0], fitperr[0]
        PSFpopt = [A,a,b,x0,y0]
        PSFperr = [Aerr,aerr,berr,0,0]
        #calculate goodness of fit
        I_theo = D2moff((x, y),*PSFpopt)
        X2dof = np.sum(np.square((intens-I_theo)/np.sqrt(np.abs(intens))))/(len(intens)-6)
    except:
        #catastrophic failure of PSF fitting
        print "PSF fitting catastrophic failure"
        PSFpopt = [0]*5
        PSFperr = [0]*5
        X2dof = 0
    if verbosity > 0:
        print "PSF moffat fit parameters"
        print "[A,a,b,X0,Y0] = "+str(PSFpopt)
        print "parameter errors = "+str(PSFperr)
        print "Chi2 = "+str(X2dof)

    #graph fits if verbosity is high enough
    if verbosity > 1 and FWHM != 0:
        PSF_plot(image, PSFpopt, X2dof, skypopt, skyN, fitsky, fsize)
    elif verbosity > 1 and FWHM == 0:
        print "Unable to plot, FWHM of PSF is nonsensical"
        
    #check if fit is ridiculous, give back no fit
    if PSFverify(PSFpopt, x0, y0):
        return PSFpopt, PSFperr, X2dof, skypopt, skyN
    else:
        return [0]*5, [0]*5, 0, [0]*3, skyN

#function: plot PSF fitting
def PSF_plot(image, PSFpopt, X2dof, skypopt, skyN, fitsky, fsize):

    import matplotlib.pyplot as plt
    
    #get fit parameters
    A = PSFpopt[0]
    a = abs(PSFpopt[1])
    b = PSFpopt[2]
    X0 = PSFpopt[3]
    Y0 = PSFpopt[4]
    FWHM = moff_toFWHM(a, b)
    
    #compute PSF fit
    xt = np.arange(X0-fsize*FWHM,X0+fsize*FWHM+1,0.1)
    x = np.arange(X0-fsize*FWHM,X0+fsize*FWHM+1,dtype=int)
    Ix_theo = D2moff((xt,np.array([int(Y0)]*len(xt))),*PSFpopt)
    Ix_im = np.array([image[int(Y0)][i] for i in x])
    Ix_res = Ix_im - D2moff((x,np.array([int(Y0)]*len(x))),*PSFpopt)
    
    yt = np.arange(Y0-fsize*FWHM,Y0+fsize*FWHM+1,0.1)
    y = np.arange(Y0-fsize*FWHM,Y0+fsize*FWHM+1,dtype=int)
    Iy_theo = D2moff((np.array([int(X0)]*len(yt)),yt),*PSFpopt)
    Iy_im = np.array([image[i][int(X0)] for i in y])
    Iy_res = Iy_im - D2moff((np.array([int(X0)]*len(y)),y),*PSFpopt)

    if fitsky:
        Ix_theo = Ix_theo+D2plane((xt,np.array([int(Y0)]*len(xt))),*skypopt)
        Ix_res = Ix_res-D2plane((x,np.array([int(Y0)]*len(x))),*skypopt)
        Iy_theo = Iy_theo+D2plane((np.array([int(X0)]*len(yt)),yt),*skypopt)
        Iy_res = Iy_res-D2plane((np.array([int(X0)]*len(y)),y),*skypopt)
        
    #plot psf moffat in X and Y slice side by side
    f, ax = plt.subplots(2, 2, sharex="col", sharey="row")
    ax[0][0].errorbar(x,Ix_im,yerr=np.sqrt(np.absolute(Ix_im)+skyN**2),fmt='r+', label='slice at Y='+str(int(Y0)))
    ax[0][0].plot(xt, Ix_theo, label='fit X2/dof='+str(X2dof)[:6])
    ax[0][0].set_xlabel('x-pixel')
    ax[0][0].set_ylabel('data #')
    ax[0][0].set_xlim(min(x),max(x))
    ax[0][0].legend()
    ax[1][0].errorbar(x,Ix_res,yerr=np.sqrt(np.absolute(Ix_im)+skyN**2),fmt='r+', label='residuals')
    ax[1][0].plot(x,np.zeros(len(x)))
    ax[1][0].legend()
    ax[0][1].errorbar(y,Iy_im,yerr=np.sqrt(np.absolute(Iy_im)+skyN**2),fmt='r+', label='slice at X='+str(int(X0)))
    ax[0][1].plot(yt, Iy_theo, label='fit X2/dof='+str(X2dof)[:6])
    ax[0][1].set_xlabel('y-pixel')
    ax[0][1].set_ylabel('data #')
    ax[0][1].set_xlim(min(y),max(y))
    ax[0][1].legend()
    ax[1][1].errorbar(y,Iy_res,yerr=np.sqrt(np.absolute(Iy_im)+skyN**2),fmt='r+', label='residuals')
    ax[1][1].plot(y,np.zeros(len(y)))
    ax[1][1].legend()
    f.subplots_adjust(wspace=0)
    f.subplots_adjust(hspace=0)
    plt.setp([a.get_xticklabels()[0] for a in ax[1, :]], visible=False)
    plt.setp([a.get_yticklabels()[0] for a in ax[:, 0]], visible=False)
    plt.setp([a.get_xticklabels()[-1] for a in ax[1, :]], visible=False)
    plt.setp([a.get_yticklabels()[-1] for a in ax[:, 0]], visible=False)
    plt.suptitle("PSF Moffat Fit")
    plt.show()
    
#function: calculates photometric intensity and sky background using PSF
def PSF_photometry(image, x0, y0, PSFpopt, PSFperr, skypopt, skyN, verbosity=0):
    #get some critical values
    A, Aerr = PSFpopt[0], PSFperr[0]
    a, aerr = abs(PSFpopt[1]), PSFperr[1]
    b, berr = PSFpopt[2], PSFperr[2]
    X0 = PSFpopt[3]
    Y0 = PSFpopt[4]
    FWHM = moff_toFWHM(a, b)
            
    #compute optimal aperture
    Io = 0
    SNo = 0
    opt_r = 0
    #fraction of light to include (Kron)
    frac = 0.9
    if PSFverify(PSFpopt, x0, y0):
        #compute optimal aperture radius (90% source light)
        Io, sigmao, opt_r = moff_integrate(A,a,b,Aerr,aerr,berr,frac)
        opt_r = opt_r/FWHM
        #check if wings are too large to be sensical
        opt_r = min(opt_r, 3.0)
        #check if psf is too small
        opt_r = max(opt_r, 1.0/FWHM)
        
        #extract PSF aperture
        PSF_extract, x, y = ap_get(image, x0, y0, 0, opt_r*FWHM)
        #calculate PSF fit
        PSF_fit = D2moff((x,y),*PSFpopt)
        Io = np.sum(PSF_fit)
        #Note: moffat function is not good enough fit
        #residuals contain fit residuals dues to bad fit
        #calculate noise in aperture
        PSF_sky = D2plane((x,y),*skypopt)
        PSF_nosky = PSF_extract - PSF_sky
        PSF_res = np.square(PSF_fit-PSF_nosky)
        sigmao = np.sqrt(PSF_res.sum())
        SNo = Io/sigmao
        
    else:
        print "Fit not viable for aperture photometry"
        Io = 0
        SNo = 0
        SNr = 0
    #output information
    if verbosity > 0:
        print "\noutput values"
        print "signal to noise: "+str(SNo)
        print "full width half maximum: "+str(FWHM)
        print "optimal at aperture: "+str(opt_r)+"FWHM"
        print "\n"
        
    #graph photometry if verbosity is high enough
    if verbosity > 1 and FWHM != 0:
        
        import matplotlib.pyplot as plt
    
        #plot psf aperture to snr, intensity
        ap_r = np.linspace(1.0/FWHM,3.0,100)
        Is = np.zeros(len(ap_r))
        sigmas = np.zeros(len(ap_r))
        for i, radius in enumerate(ap_r):
            #aperture = ap_synth(D2moff, PSFpopt, radius*FWHM)
            #Is[i] = np.sum(aperture)
            #sigmas[i] = np.sqrt(Is[i] + (skyN**2)*aperture.size)

            #extract PSF aperture
            PSF_extract, x, y = ap_get(image, x0, y0, 0, radius*FWHM)
            
            #calculate noise in aperture
            PSF_fit = D2moff((x,y),*PSFpopt)
            Is[i] = np.sum(PSF_fit)
            #sigmas[i] = np.sqrt(np.absolute(Is[i]) + (skyN**2)*PSF_fit.size)

            PSF_sky = D2plane((x,y),*skypopt)
            PSF_nosky = PSF_extract - PSF_sky
            PSF_res = np.square(PSF_fit-PSF_nosky)
            sigmas[i] = np.sqrt(PSF_res.sum())
        SNs = Is/sigmas

        f, ax = plt.subplots(2, sharex=True)
        ax[0].set_title("Aperture Signal to Noise")
        ax[0].plot(ap_r,SNs,label='SNR')
        ax[0].set_ylabel("SN")
        ax[0].legend()
        ax[1].errorbar(ap_r,Is,yerr=sigmas,fmt='r+',label='summed intens')
        ax[1].set_ylabel("I")
        ax[1].set_xlabel("Aperture R (FWHM)")
        ax[1].legend()
        plt.setp([a.get_yticklabels()[0] for a in ax], visible=False)
        plt.setp([a.get_yticklabels()[-1] for a in ax], visible=False)
        f.subplots_adjust(hspace=0)
        plt.show()
    elif verbosity > 1 and FWHM == 0:
        print "Unable to plot, FWHM of PSF is nonsensical. Fit failed."

    #return intensity, and signal to noise
    return Io, SNo

#function: calculates photometric intensity and sky background using aperture
def Ap_photometry(image, x0, y0, skypopt, skyN, radius=None, PSF=None, fitsky=True, verbosity=0):
    if radius is None:
        #get some critical values
        frac = 0.9 #Kron aperture light fraction
        a = abs(PSF[0])
        b = PSF[1]
        FWHM = moff_toFWHM(a, b)
        radius = a*np.sqrt(np.power(1 - frac,1/(1-b)) - 1)
    #extract PSF aperture
    PSF_extract, x, y = ap_get(image, x0, y0, 0, radius)
    if fitsky:
        #subtract sky background
        PSF_sky = D2plane((x,y),*skypopt)
        PSF_extract = PSF_extract - PSF_sky
    #clean out bad pixels
    #xf, yf, PSF_final = PSFclean(x, y, PSF_extract, skyN)
    #integrate aperture
    Io = np.sum(PSF_extract)
    #proper signal to noise calculation for unscaled intensities
    #noise is sqrt(intensity) is the best we can do
    sigmar = np.sqrt(np.absolute(Io) + (skyN**2)*PSF_extract.size)
    SNo = Io/sigmar
    
    if verbosity > 0:
        print "\noutput values"
        print "signal to noise: "+str(SNo)
        print "full width half maximum: "+str(FWHM)
        print "optimal at aperture: "+str(radius/FWHM)+"FWHM"
        print "Pixel aperture radius: "+str(radius)
        print "\n"

    #graph photometry if verbosity is high enough
    if verbosity > 1 and FWHM != 0:

        import matplotlib.pyplot as plt

        #compute PSF fit
        x = np.arange(x0-radius,x0+radius+1,dtype=int)
        Ix_im = np.array([image[int(y0)][i] for i in x])  
        y = np.arange(y0-radius,y0+radius+1,dtype=int)
        Iy_im = np.array([image[i][int(x0)] for i in y])
        
        if fitsky:
            Ix_im = Ix_im-D2plane((x,np.array([int(y0)]*len(x))),*skypopt)
            Iy_im = Iy_im-D2plane((np.array([int(x0)]*len(y)),y),*skypopt)
        
        #plot psf moffat in X and Y slice side by side
        f, ax = plt.subplots(1, 2, sharey="row")
        ax[0].errorbar(x,Ix_im,yerr=np.sqrt(np.absolute(Ix_im)+skyN**2),fmt='r+', label='slice at Y='+str(int(y0)))
        ax[0].set_xlabel('x-pixel')
        ax[0].set_ylabel('data #')
        ax[0].set_xlim(min(x),max(x))
        ax[0].legend()
        ax[1].errorbar(y,Iy_im,yerr=np.sqrt(np.absolute(Iy_im)+skyN**2),fmt='r+', label='slice at X='+str(int(x0)))
        ax[1].set_xlabel('y-pixel')
        ax[1].set_ylabel('data #')
        ax[1].set_xlim(min(y),max(y))
        ax[1].legend()
        f.subplots_adjust(wspace=0)
        plt.suptitle("Aperture Section")
        plt.show()
        plt.setp([a.get_yticklabels()[0] for a in ax], visible=False)
        plt.setp([a.get_yticklabels()[-1] for a in ax], visible=False)
    
        #plot psf aperture to snr, intensity
        ap_r = np.linspace(1.0/FWHM,3.0,100)
        Is = np.zeros(len(ap_r))
        sigmas = np.zeros(len(ap_r))
        for i, radius in enumerate(ap_r):
            #extract PSF aperture
            PSF_extract, x, y = ap_get(image, x0, y0, 0, radius*FWHM)
            if fitsky:
                #subtract sky background
                PSF_sky = D2plane((x,y),*skypopt)
                PSF_extract = PSF_extract - PSF_sky
            #clean out bad pixels
            xf, yf, PSF_final = PSFclean(x, y, PSF_extract, skyN)
            #integrate aperture
            Is[i] = np.sum(PSF_final)
            sigmas[i] = np.sqrt(np.absolute(Is[i]) + (skyN**2)*PSF_final.size)
        SNs = Is/sigmas

        f, ax = plt.subplots(2, sharex=True)
        ax[0].set_title("Aperture Signal to Noise")
        ax[0].plot(ap_r,SNs,label='SNR')
        ax[0].set_ylabel("SN")
        ax[0].legend()
        ax[1].errorbar(ap_r,Is,yerr=sigmas,fmt='r+',label='summed intens')
        ax[1].set_ylabel("I")
        ax[1].set_xlabel("Aperture R (FWHM)")
        ax[1].legend()
        plt.setp([a.get_yticklabels()[0] for a in ax], visible=False)
        plt.setp([a.get_yticklabels()[-1] for a in ax], visible=False)
        f.subplots_adjust(hspace=0)
        plt.show()
    elif verbosity > 1 and FWHM == 0:
        print "Unable to plot, FWHM of PSF is nonsensical. Aperture=0."

    #return intensity, and signal to noise
    return Io, SNo
