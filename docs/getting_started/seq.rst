SEQ Files
=======================================================

Some cameras, like the FLIR Duo capture files in a format called `SEQ` or "sequence". This is a semi-proprietary format containing raw thermal images and metadata associated with them. That metadata includes things like the geolocation of the image, if available, and the calibration coefficients used to convert the raw image to radiometric. SEQ files are simply a bunch of images stacked one after the other.

The reason that these files exist is that there is no universally adopted standard for saving raw video along with the necessary metadata. There *are* formats which could be used, like the Flexible Image Transport System (FITS) format used ubiquitously in astronomy, but that doesn't seem to have caught on anywhere else.

There is limited documentation online about the format of an SEQ file, but through a combination of FLIR's documentation and enterprising developers it has been reverse engineered to the point where we can write software to split an SEQ file into its constituent images. This is useful for a few purposes including

* You want to do some sort of analysis on individual frames, for example as a dataset for machine learning
* You want to create a movie

Flirpy offers a simple utility to split out SEQ files into constituent files, as well as synchronising with videos captured with the RGB camera (as on the Duo Pro). Assuming you have a folder containing all the infrared and visible data, i.e. SEQ files and MOVs, just run:

.. code-block bash:
    split_seqs -i "*.SEQ" -o split --rgb "*.MOV" --jpeg_quality 80

This will create a folder called split subfolders for each data type.

* Preview images are 8-bit versions of the radiometric image (similar to "AGC" mode on the camera). This is useful for easy inspection of data.
* Radiometric images are 16-bit TIFFs which can be converted to physical units (multiply pixel value by 0.04)
* Raw images are FLIR FFF files, also stored here is the metadata for each frame in a text file
* RGB images are stored as JPEGs and are time-synchronised to match the IR frames.

Note that JPEG/TIFFs are preferred because they can be geotagged. Flirpy will automatically copy geolocation information from the base SEQ file to the preview, radiometric and RGB images ready for use with photogrammetry software like Pix4D.

Full documentation can be seen by calling `split_seqs -h`:

.. code-block bash:

   usage: split_seqs [-h] [-o OUTPUT] -i INPUT [-v VERBOSITY]
                     [--preview_format PREVIEW_FORMAT] [--rgb RGB]
                     [--jpeg_quality JPEG_QUALITY] [--use_gstreamer]
                     [--width WIDTH] [--height HEIGHT] [--rgb_fps RGB_FPS]
                     [--merge_folders | --no_merge_folders]
                     [--split_filetypes | --no_split_filetypes]
                     [--export_meta | --no_export_meta]
                     [--export_tiff | --no_export_tiff]
                     [--export_preview | --no_export_preview]
                     [--skip_thermal | --no_skip_thermal]

   Split all files in folder

   optional arguments:
     -h, --help            show this help message and exit
     -o OUTPUT, --output OUTPUT
                           Output folder
     -i INPUT, --input INPUT
                           Input file mask, e.g. "/path/*.SEQ"
     -v VERBOSITY, --verbosity VERBOSITY
                           Logging level
     --preview_format PREVIEW_FORMAT
                           Output preview format (png, jpg, tiff)
     --rgb RGB             If provided, split videos too e.g. "/path/*.MOV"
     --jpeg_quality JPEG_QUALITY
                           RGB Output quality (0-100)
     --use_gstreamer       Use Gstreamer for video decoding
     --width WIDTH         Thermal image width
     --height HEIGHT       Thermal image height
     --rgb_fps RGB_FPS     RGB framerate if different from thermal
     --merge_folders       Merge output folders (and remove intermediates
                           afterwards)
     --no_merge_folders    Merge output folders (and remove intermediates
                           afterwards)
     --split_filetypes     Split output files by type (make
                           raw/preview/radiometric folders)
     --no_split_filetypes  Split output files by type (make
                           raw/preview/radiometric folders)
     --export_meta         Export meta information files (also for geotagging)
     --no_export_meta      Export meta information files (also for geotagging)
     --export_tiff         Export radiometric tiff files
     --no_export_tiff      Export radiometric tiff files
     --export_preview      Export 8-bit preview png files
     --no_export_preview   Export 8-bit preview png files
     --skip_thermal        Skip thermal processing
     --no_skip_thermal     Skip thermal processing

