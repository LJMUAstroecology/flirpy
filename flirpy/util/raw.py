import numpy as np
import math

def from_string_or_float(value):
    if type(value) is float:
        return value
    else:
        return float(value.strip().split(" ")[0])

def raw2temp(raw, meta):
    """
    Convert raw pixel values to temperature, if calibration coefficients are known. The
    equations for atmospheric and window transmission are found in Minkina and Dudzik, as 
    well as some of FLIR's documentation.

    Roughly ported from ThermImage: https://github.com/gtatters/Thermimage/blob/master/R/raw2temp.R

    """

    ATA1 = float(meta["Atmospheric Trans Alpha 1"])
    ATA2 = float(meta["Atmospheric Trans Alpha 2"])
    ATB1 = float(meta["Atmospheric Trans Beta 1"])
    ATB2 = float(meta["Atmospheric Trans Beta 2"])
    ATX = float(meta["Atmospheric Trans X"])
    PR1 = float(meta["Planck R1"])
    PR2 = float(meta["Planck R2"])
    PO = float(meta["Planck O"])
    PB = float(meta["Planck B"])
    PF = float(meta["Planck F"])
    E = float(meta["Emissivity"])
    IRT = float(meta["IR Window Transmission"])
    IRWTemp = from_string_or_float(meta["IR Window Temperature"])
    OD = from_string_or_float(meta["Object Distance"])
    ATemp = from_string_or_float(meta["Atmospheric Temperature"])
    RTemp = from_string_or_float(meta["Reflected Apparent Temperature"])
    humidity = from_string_or_float(meta["Relative Humidity"])

    # Equations to convert to temperature
    # See http://130.15.24.88/exiftool/forum/index.php/topic,4898.60.html
    # Standard equation: temperature<-PB/log(PR1/(PR2*(raw+PO))+PF)-273.15
    # Other source of information: Minkina and Dudzik's Infrared Thermography: Errors and Uncertainties

    window_emissivity = 1 - IRT
    window_reflectivity = 0

    # Converts relative humidity into water vapour pressure (mmHg)
    water = (humidity/100.0)*math.exp(1.5587+0.06939*(ATemp)-0.00027816*(ATemp)**2+0.00000068455*(ATemp)**3)

    #tau1 = ATX*np.exp(-np.sqrt(OD/2))
    tau1 = ATX*np.exp(-np.sqrt(OD/2)*(ATA1+ATB1*np.sqrt(water)))+(1-ATX)*np.exp(-np.sqrt(OD/2)*(ATA2+ATB2*np.sqrt(water)))
    tau2 = tau1

    # transmission through atmosphere - equations from Minkina and Dudzik's Infrared Thermography Book
    # Note: for this script, we assume the thermal window is at the mid-point (OD/2) between the source
    # and the camera sensor

    raw_refl = PR1/(PR2*(np.exp(PB/(RTemp+273.15))-PF))-PO   # radiance reflecting off the object before the window
    raw_refl_attn = (1-E)/E*raw_refl   # attn = the attenuated radiance (in raw units) 

    raw_atm1 = PR1/(PR2*(np.exp(PB/(ATemp+273.15))-PF))-PO # radiance from the atmosphere (before the window)
    raw_atm1_attn = (1-tau1)/E/tau1*raw_atm1 # attn = the attenuated radiance (in raw units) 

    raw_window = PR1/(PR2*(np.exp(PB/(IRWTemp+273.15))-PF))-PO
    einv = 1./E/tau1/IRT
    raw_window_attn = window_emissivity*einv*raw_window

    raw_refl2 = raw_refl   
    raw_refl2_attn = window_reflectivity*einv*raw_refl2

    raw_atm2 = raw_atm1
    ediv = einv/tau2
    raw_atm2_attn = (1-tau2)*ediv*raw_atm2

    # These last steps are pretty slow and 
    # could probably be sped up a lot
    raw_sub = -raw_atm1_attn-raw_atm2_attn-raw_window_attn-raw_refl_attn-raw_refl2_attn
    raw_object = np.add(np.multiply(raw, ediv), raw_sub)

    raw_object = np.add(raw_object, PO)
    raw_object = np.multiply(raw_object, PR2)
    raw_object_inv = np.multiply(np.reciprocal(raw_object), PR1)
    raw_object_inv = np.add(raw_object_inv, PF)    
    raw_object_log = np.log(raw_object_inv)
    temp = np.multiply(np.reciprocal(raw_object_log), PB)

    return temp - 273.15
