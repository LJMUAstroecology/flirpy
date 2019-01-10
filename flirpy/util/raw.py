import numpy as np
import math

def raw2temp(raw, meta):
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
        IRWTemp = float(meta["IR Window Temperature"].split('C')[0])
        OD = float(meta["Object Distance"].split('m')[0])
        ATemp = float(meta["Atmospheric Temperature"].split('C')[0])
        RTemp = float(meta["Reflected Apparent Temperature"].split('C')[0])
        humidity = float(meta["Relative Humidity"].split('%')[0])

      # Equations to conert to temperature
      # See http://130.15.24.88/exiftool/forum/index.php/topic,4898.60.html
      # Standard equation: temperature<-PB/log(PR1/(PR2*(raw+PO))+PF)-273.15
      # Other source of information: Minkina and Dudzik's Infrared Thermography: Errors and Uncertainties

        window_emissivity = 1 - IRT
        window_reflectivity = 0

        # Converts relative humidity into water vapour pressure (mmHg)
        water = (humidity/100.0)*math.exp(1.5587+0.06939*(ATemp)-0.00027816*(ATemp)**2+0.00000068455*(ATemp)**3)

        #tau1 = ATX*np.exp(-np.sqrt(OD/2))
        tau1 = ATX*np.exp(-np.sqrt(OD/2)*(ATA1+ATB1*np.sqrt(water)))+(1-ATX)*np.exp(-np.sqrt(OD/2)*(ATA2+ATB2*np.sqrt(water)))
        tau2 = ATX*np.exp(-np.sqrt(OD/2)*(ATA1+ATB1*np.sqrt(water)))+(1-ATX)*np.exp(-np.sqrt(OD/2)*(ATA2+ATB2*np.sqrt(water)))

        # transmission through atmosphere - equations from Minkina and Dudzik's Infrared Thermography Book
        # Note: for this script, we assume the thermal window is at the mid-point (OD/2) between the source
        # and the camera sensor

        raw_refl = PR1/(PR2*(np.exp(PB/(RTemp+273.15))-PF))-PO   # radiance reflecting off the object before the window
        raw_refl_attn = (1-E)/E*raw_refl   # attn = the attenuated radiance (in raw units) 

        raw_atm1 = PR1/(PR2*(np.exp(PB/(ATemp+273.15))-PF))-PO # radiance from the atmosphere (before the window)
        raw_atm1_attn = (1-tau1)/E/tau1*raw_atm1 # attn = the attenuated radiance (in raw units) 

        raw_window = PR1/(PR2*(math.exp(PB/(IRWTemp+273.15))-PF))-PO
        raw_window_attn = window_emissivity/E/tau1/IRT*raw_window

        raw_refl2 = PR1/(PR2*(np.exp(PB/(RTemp+273.15))-PF))-PO   
        raw_refl2_attn = window_reflectivity/E/tau1/IRT*raw_refl2

        raw_atm2 = PR1/(PR2*(np.exp(PB/(ATemp+273.15))-PF))-PO
        raw_atm2_attn = (1-tau2)/E/tau1/IRT/tau2*raw_atm2

        raw_object = raw/E/tau1/IRT/tau2-raw_atm1_attn-raw_atm2_attn-raw_window_attn-raw_refl_attn-raw_refl2_attn

        temp = PB/np.log(PR1/(PR2*(raw+PO))+PF)-273.15

        return temp