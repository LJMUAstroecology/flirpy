import logging
import os

from PIL import Image
from tqdm.auto import tqdm

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path  # python 2 backport

from flirpy.io.fff import (
    _FFF_HEADER_STRUCT,
    _FFF_RECORD_STRUCT,
    Fff,
    FffHeader,
    FffRecord,
)
from flirpy.util.exiftool import Exiftool

logger = logging.getLogger(__name__)


class Seq:
    def __init__(self, input_file, height=None, width=None, raw=False):
        """
        Load a FLIR SEQ file. Currently this must be a SEQ
        file containing FFF files. The resulting object can
        be indexed as a normal array and will return the
        """
        with open(input_file, "rb") as seq_file:
            self.seq_blob = seq_file.read()

        self.raw = raw
        self.pos = self._get_frame_positions(self.seq_blob)

        self.width = width
        self.height = height

    @staticmethod
    def _get_frame_positions(seq_blob):
        """
        Walk the SEQ blob by parsing each FFF header to determine the
        frame extent from its record directory. FFF entries start with a
        magic byte sequence, but this can also appear inside image data.

        Returns a list of (offset, size) tuples.
        """
        FFF_MAGIC = b"FFF\x00"

        pos = []
        cursor = 0
        blob_len = len(seq_blob)

        while cursor + _FFF_HEADER_STRUCT.size <= blob_len:
            if seq_blob[cursor : cursor + 4] != FFF_MAGIC:
                break

            bigendian = FffHeader.detect_bigendian(seq_blob, cursor)
            header = FffHeader.from_buffer(seq_blob, cursor, bigendian=bigendian)

            # Frame extent is at least the end of the record directory
            frame_size = (
                header.record_dir_offset + header.record_count * _FFF_RECORD_STRUCT.size
            )

            # Extend to cover every record's data region
            for i in range(header.record_count):
                rec_abs = (
                    cursor + header.record_dir_offset + i * _FFF_RECORD_STRUCT.size
                )
                if rec_abs + _FFF_RECORD_STRUCT.size > blob_len:
                    break
                rec = FffRecord.from_buffer(seq_blob, rec_abs, bigendian)
                rec_end = rec.record_offset + rec.record_length
                frame_size = max(frame_size, rec_end)

            pos.append((cursor, frame_size))
            cursor += frame_size

        return pos

    def __len__(self):
        """
        Returns the length of the sequence
        """
        return len(self.pos)

    def __getitem__(self, index):
        """
        Retuns a FFF image in the sequence
        """

        offset, chunksize = self.pos[index]
        chunk = self.seq_blob[offset : offset + chunksize]

        if self.raw:
            return chunk
        else:
            return Fff(chunk)


class Splitter:
    def __init__(
        self,
        output_folder="./",
        exiftool_path=None,
        start_index=0,
        step=1,
        split_folders=True,
        preview_format="jpg",
        width=None,
        height=None,
    ):

        self.exiftool = Exiftool(exiftool_path)

        self.start_index = start_index
        self.step = step
        self.frame_count = self.start_index
        self.export_tiff = True
        self.export_meta = True
        self.export_preview = True
        self.export_radiometric = True
        self.overwrite = True
        self.split_folders = split_folders
        self.split_filetypes = True
        self.width = width
        self.height = height

        if preview_format in ["jpg", "jpeg", "png", "tiff"]:
            self.preview_format = preview_format
        else:
            raise ValueError("Preview format not recognised")

        self.output_folder = os.path.expanduser(output_folder)
        Path(self.output_folder).mkdir(exist_ok=True)

    def set_start_index(self, index):
        self.start_index = int(index)

    def process(self, file_list):

        if isinstance(file_list, str):
            file_list = [file_list]

        file_list = [os.path.expanduser(f) for f in file_list]

        logger.info("Splitting {} files".format(len(file_list)))

        self.frame_count = self.start_index

        folders = []

        for seq in tqdm(file_list):
            if self.split_folders:
                subfolder, _ = os.path.splitext(os.path.basename(seq))
                folder = os.path.join(self.output_folder, subfolder)
                folders.append(folder)
            else:
                folder = self.output_folder

            Path(folder).mkdir(exist_ok=True)

            logger.info("Splitting {} into {}".format(seq, folder))
            self._process_seq(seq, folder)

            # Batch export meta data
            if self.export_meta and self.exiftool.path is not None:
                logger.info("Extracting metadata")

                if self.split_filetypes:
                    filemask = os.path.join(folder, "raw", "frame_*.fff")
                    copy_filemask = os.path.normpath("./raw/%f.fff")
                    radiometric_folder = os.path.normpath("./radiometric")
                    preview_folder = os.path.normpath("./preview")
                else:
                    filemask = os.path.join(folder, "frame_*.fff")
                    copy_filemask = os.path.normpath("%f.fff")
                    radiometric_folder = os.path.normpath("./")
                    preview_folder = os.path.normpath("./")

                self.exiftool.write_meta(filemask)

            # Copy geotags
            if self.export_tiff and self.exiftool.path is not None:
                logger.info("Copying tags to radiometric")
                self.exiftool.copy_meta(
                    folder,
                    filemask=copy_filemask,
                    output_folder=radiometric_folder,
                    ext="tiff",
                )

            if self.export_preview and self.exiftool.path is not None:
                logger.info("Copying tags to preview")
                self.exiftool.copy_meta(
                    folder,
                    filemask=copy_filemask,
                    output_folder=preview_folder,
                    ext=self.preview_format,
                )

        return folders

    def _write_tiff(self, filename, data):
        logger.debug("Writing %s", filename)
        Image.fromarray(data.astype("uint16")).save(filename)

    def _write_preview(self, filename, data):
        drange = data.max() - data.min()
        preview_data = 255.0 * ((data - data.min()) / drange)
        logger.debug("Writing %s", filename)
        Image.fromarray(preview_data.astype("uint8")).save(filename)

    def _make_split_folders(self, output_folder):
        Path(os.path.join(output_folder, "raw")).mkdir(exist_ok=True)
        Path(os.path.join(output_folder, "radiometric")).mkdir(exist_ok=True)
        Path(os.path.join(output_folder, "preview")).mkdir(exist_ok=True)

    def _check_overwrite(self, path):
        exists = os.path.exists(path)
        return (not exists) or (exists and self.overwrite)

    def _get_seq(self, input_file):
        return Seq(input_file, self.height, self.width)

    def _process_seq(self, input_file, output_subfolder):

        logger.debug("Processing {}".format(input_file))

        for count, frame in enumerate(tqdm(self._get_seq(input_file))):
            if frame.meta is None:
                self.frame_count += 1
                continue

            if self.split_filetypes:
                self._make_split_folders(output_subfolder)

                filename_fff = os.path.join(
                    output_subfolder,
                    "raw",
                    "frame_{0:06d}.fff".format(self.frame_count),
                )
                filename_tiff = os.path.join(
                    output_subfolder,
                    "radiometric",
                    "frame_{0:06d}.tiff".format(self.frame_count),
                )
                filename_preview = os.path.join(
                    output_subfolder,
                    "preview",
                    "frame_{:06d}.{}".format(self.frame_count, self.preview_format),
                )
                filename_meta = os.path.join(
                    output_subfolder,
                    "raw",
                    "frame_{0:06d}.txt".format(self.frame_count),
                )
            else:
                filename_fff = os.path.join(
                    output_subfolder, "frame_{0:06d}.fff".format(self.frame_count)
                )
                filename_tiff = os.path.join(
                    output_subfolder, "frame_{0:06d}.tiff".format(self.frame_count)
                )
                filename_preview = os.path.join(
                    output_subfolder,
                    "frame_{:06d}.{}".format(self.frame_count, self.preview_format),
                )
                filename_meta = os.path.join(
                    output_subfolder, "frame_{0:06d}.txt".format(self.frame_count)
                )

            if self.frame_count % self.step == 0:
                if self.export_meta and self._check_overwrite(filename_fff):
                    frame.write(filename_fff)

                # Export raw files and/or radiometric convert them
                if self.export_tiff and self._check_overwrite(filename_tiff):
                    if self.export_radiometric:
                        # Use Exiftool to extract metadata
                        if (
                            self.width is not None
                            and self.height is not None
                            and self.exiftool.path is not None
                        ):
                            # Export the first metadata
                            if count == 0:
                                self.exiftool.write_meta(filename_fff)
                                meta = self.exiftool.meta_from_file(filename_meta)
                        else:
                            meta = None

                        image = frame.get_radiometric_image(meta=meta)
                        image += 273.15  # Convert to Kelvin
                        image /= 0.04  # Standard FLIR scale factor
                    else:
                        image = frame.get_image()

                    self._write_tiff(filename_tiff, image)

                # Export preview frame (crushed to 8-bit)
                if self.export_preview and self._check_overwrite(filename_preview):
                    self._write_preview(filename_preview, image)

            self.frame_count += 1

    def _write_frame(self, frame, filename):
        logger.debug("Writing %s", filename)
        frame.write(filename)


class ExifToolSplitter(Splitter):
    def _get_seq(self, input_file):
        return Seq(input_file, self.height, self.width, raw=True)

    def _write_frame(self, frame, filename):

        # Write file
        with open(filename, "wb") as f:
            f.write(frame)

        if self.exiftool.path is not None:
            self.exiftool.write_meta(filename)

    def _process_seq(self, input_file, output_subfolder):
        logger.debug("Processing {}".format(input_file))

        for count, frame in enumerate(tqdm(self._get_seq(input_file))):
            if self.split_filetypes:
                self._make_split_folders(output_subfolder)

                filename_fff = os.path.join(
                    output_subfolder,
                    "raw",
                    "frame_{0:06d}.fff".format(self.frame_count),
                )
                filename_tiff = os.path.join(
                    output_subfolder,
                    "radiometric",
                    "frame_{0:06d}.tiff".format(self.frame_count),
                )
                filename_preview = os.path.join(
                    output_subfolder,
                    "preview",
                    "frame_{:06d}.{}".format(self.frame_count, self.preview_format),
                )
                filename_meta = os.path.join(
                    output_subfolder,
                    "raw",
                    "frame_{0:06d}.txt".format(self.frame_count),
                )
            else:
                filename_fff = os.path.join(
                    output_subfolder, "frame_{0:06d}.fff".format(self.frame_count)
                )
                filename_tiff = os.path.join(
                    output_subfolder, "frame_{0:06d}.tiff".format(self.frame_count)
                )
                filename_preview = os.path.join(
                    output_subfolder,
                    "frame_{:06d}.{}".format(self.frame_count, self.preview_format),
                )
                filename_meta = os.path.join(
                    output_subfolder, "frame_{0:06d}.txt".format(self.frame_count)
                )

            self._write_frame(frame, filename_fff)

            if self.frame_count % self.step == 0:
                self._write_frame(frame, filename_fff)
                meta = self.exiftool.meta_from_file(filename_meta)

                self.width = int(meta["Raw Thermal Image Width"])
                self.height = int(meta["Raw Thermal Image Height"])

                frame = Fff(  # noqa: PLW2901
                    filename_fff,
                    width=self.width,
                    height=self.height,
                    use_exiftool=True,
                )

                # Export raw files and/or radiometric convert them
                if self.export_tiff and self._check_overwrite(filename_tiff):
                    if self.export_radiometric:
                        image = frame.get_radiometric_image(meta=meta)
                        image += 273.15  # Convert to Kelvin
                        image /= 0.04  # Standard FLIR scale factor
                    else:
                        image = frame.get_image()

                    self._write_tiff(filename_tiff, image)

                # Export preview frame (crushed to 8-bit)
                if self.export_preview and self._check_overwrite(filename_preview):
                    self._write_preview(filename_preview, image)

            self.frame_count += 1
