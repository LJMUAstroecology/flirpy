Thermal cameras
=======================================================

Flirpy is designed primarily to control FLIR's camera cores - the Lepton, the Boson and the Tau 2. Each core has slightly different characteristics and use cases, so this overview will help you decide which one you need for your project and what Flirpy can and can't do with them.

Camera cores
*********

Lepton

Boson

Tau

Resolution
*********

The obvious difference between the various cores is their resolution. The Lepton has the lowest resolution, at either 80x60 or 160x120 pixels. The Boson and Tau are available in either 320x240 or 640x512 (a bit bigger than VGA).

Form factor
*********

Interface
*********

Radiometry
==========

Radiometry means that the images you capture from the camera contain absolute temperature values, rather than "counts". The value, brightness or intensity of an individual pixel is directly related to the temperature of the object being imaged. It is important to understand the processing pipeline that happens to produce these radiometric images.

Thermal imaging sensors can be crudely viewed as a 2D array of resistors - this is not entirely accurate, but it is sufficient to understand how thermal cameras work. When a material heats up or cools down, its resistance changes. The camera is able to measure changes in resistance over the entire sensor area by, for example, passing a reference voltage or current through each pixel. The resistance of each pixel is digitised by an analogue to digital converter (ADC) and stored as an image. This is what we might call a *raw* image.

Radiant flux
************

In order to convert raw counts from the ADC into temperature values, we use Planck's law for spectral radiance

.. math::
    I(\nu, T) = \frac{2h\nu^3}{c^2} \frac{1}{\left(e^{\frac{h\nu}{k_BT}} - 1\right)}

where:

    * :math:`I` is spectral irradiance (often :math:`B` is used here, but for whatever reason, FLIR's calibration coefficients use :math:`B` for something else.)
    * :math:`T` is object Temperature (Kelvin)
    * :math:`\nu` is frequency
    * :math:`c` is the speed of light
    * :math:`k_B` is the Boltzmann constant
    * :math:`h` is Planck's constant 
    * :math:`e` is Euler's constant

We can make some substitutions:

.. math::
    R = \frac{2h\nu^3}{c^2}
.. math::
    B = \frac{h\nu}{k_B}

to give:

.. math::
    S = \frac{R}{\left(e^{\frac{B}{T_K}} - 1\right)}

This formula is described in the *FLIR Tau 2 advanced radiometry application note* (section 8) and in the *FLIR Lepton with Radiometry Quickstart Guide*:

.. math::
    S = W(T) = \frac{R}{\left(\exp{\frac{B}{T_K}} - F\right)} + O

and rearranging for :math:`T`:

.. math::
    T_K = \frac{B}{\ln \left( \frac{R}{S - O} + F \right) } 


where :math:`S` is the counts from the ADC and :math:`O` is some offset. Here we've assumed that the response from the detector is linear with respect to object radiance. This actually requires another calibration which ensures that the signal is corrected for the temperature of the detector. Here we introduce :math:`F` as a free calibration parameter with a typical value of 0.5 - 2, rather than 1 in the original derivation.

This formula is used for the radiometric Lepton and Tau2 operating in TLinear mode and the coefficients can be read from the camera internal memory directly. In practice you don't need to do this and the cameras will return pre-calibrated images if you've enabled radiometry internally (TLinear mode on). Some FLIR cameras (such as the Duo Pro R) use a slightly different parameterisation:

.. math::
    T_K = \frac{B}{\ln \left( \frac{R_1}{R_2(S - O)} + F \right) } 

These coefficients are then are stored in the camera, or in image metadata. Here is a snippet from flirpy, reading from image metadata (Duo Pro R):

.. code-block python:
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

As you can see above, the conversion actually takes into account atmospheric conditions, object distance and so on. These tend to be fairly small effects, but they are important for precision radiometry. The most significant factor is usually emissivity. For a perfect blackbody, the emissivity is 1. Most objects are not blackbodies, however, and to accurately measure temperature on a particular object you need to dial in the correct emissivity (quite often you will find that IR "gun" thermometers have presets for common industrial materials like concrete). Similarly if you are integrating your camera into another system, for example with a window or other filters then you need to re-calibrate the system to take into account the additional optics.

TLinear mode
************

FLIR describes TLinear mode as follows:

    *In normal mode with TLinear disabled, the Tau camera outputs digital data linear in radiometric flux. In TLinear mode, the Tau camera outputs digital data linear in scene temperature.*

The raw image alone is not terribly helpful, because as you might expect, the sensor itself can heat up and cool due to ambient conditions or heat generated internally by the electronics in the camera. The first issue this causes is noise, you can also buy cooled thermal imaging cameras, but they tend to be a lot more expensive.

In summary there are two corrections. The first is a linear correction to adjust for changes in the focal plane array (FPA) temperature. The second is a fit to the Planck equation to calculate the object temperature.

Out of the box, currently only the Lepton 3.5 and the Tau 2 are available with radiometry.

Radiometric chain
******************

What determines how much signal falls on our detector?

.. image:: thermal_chain.png

Consider a camera pointed at an object. The object has some emissivity, :math:`\epsilon` and it has a radiated flux proportional to its temperature, :math:`\epsilon W(T_{\text{object}})`. Of course if we had a perfect blackbody, we could assume that :math:`\epsilon=1`. Since the object is not a blackbody, it also reflects radiation (:math:`r = 1- \epsilon`).

Suppose that there is also some background radiation, such as the Sun, or a hot lamp. The material will absorb some of that heat, and it will reflect the rest: :math:`rW(T_{\text{background}})`.

Now we have two components: radiation emitted by the surface, and background radiation reflected by the surface.

This radiation then passes through the atmosphere, which attenuates some of it - it has a transmittance :math:`\tau_{\text{atm}}`. And of course since the atmosphere is also made up of matter at some temperature, :math:`T_{\text{atm}}`, it will also emit radiation (and that radiation will also be partially attenuated). We now can compute the flux at the detector, :math:`S`:

.. math::
    S = \tau_{\text{atm}}(\epsilon W(T_{\text{object}}) + (1-\epsilon)W(T_{\text{background}})) + (1-\tau_{\text{atm}})W(T_\text{atm})

If there is also a window in the way, then we need to correct for that as well. In this case, the window also has a transmittance :math:`\tau_{\text{win}}` and a temperature :math:`T_{\text{win}}`. To add to the confusion, there will also be radiation emitted from the detector, with :math:`T_{\text{det}}` that reflects off the window (which has reflectivity :math:`r_{\text{win}}`). Some of *that* radiation will pass through the window and out into the scene, never to be seen again:

.. math::
    S = \tau_{\text{win}}\left(\tau_{\text{atm}}[\epsilon W(T_{\text{object}}) + (1-\epsilon)W(T_{\text{background}})] + (1-\tau_{\text{atm}})W(T_\text{atm})\right) +\\ r_{\text{win}} W(T_{\text{det}})+(1 - \tau_{\text{win}} - r_{\text{win}})W(T_{\text{win}})

Fortunately, we can approximate atmospheric parameters to a reasonable degree, which is a function of ambient temperature and humidity, as well as the distance to the object. For most use cases you don't need to worry too much about this, especially if your object is fairly close. This is all calculated automatically by flirpy, but bear in mind that most drone cameras such as the Duo store fixed parameters for the scene (temperature, humidity, etc). For the most accurate results, you should monitor ambient conditions throughout your data capture process and correct each frame individually with the conditions at the time it was captured.

How much difference does all this make? In practice not very much for most people. In the equations above, your object is probably bright enough that atmospheric transmission is negligible compared to your uncertainty on the object's emissivity. Before putting a lot of effort into worrying about temperature and humidity, consider what measurement error is acceptable to you. Typically thermal imaging cameras are capable of highlighting very small temperature differences *within a scene*. This is a subtle, but important point. If your comparison objects are in the same image, then you can effectively ignore the atmosphere as it will attenuate/emit the same amount throughout the image.

Further reading
===============

For a more exhaustive overview, you are recommended to have a look at these books:

* Infrared Thermal Imaging, Vollmer and Mollman
* Infrared Thermography: Errors and Uncertainties, Minkina and Dudzik's 

Vollmer and Mollman, in particular, is comprehensive at just shy of 800 pages. It covers a lot of common use-cases for thermal imaging such as building/infrastructure monitoring. It also has plenty of good illustrations and images.