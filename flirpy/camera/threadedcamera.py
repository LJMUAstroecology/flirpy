from threading import Thread, Lock
import time
import numpy as np
import abc
import cv2
from . timedservice import TimedService

class ThreadedCamera(object):
    """
    A generic class for capturing images from a camera using threading

    You should subclass this and implement _grab() yourself.

    This class supports adding timer callbacks which can be used for 
    diagnostics or other periodic functionality. Note that precise timing
    is not guaranteed. In fact the _minimum_ timing resolution is limited
    by the effective framerate of the camera (since timers are serviced
    after each image capture.)

    """

    def __init__(self):
        self.latest_image = None
        self.should_stop = False
        self.new_image = False
        self.thread = None
        self.capturing = False
        self.latency = np.zeros(60)
        self.n_frames = 0
        self.target_fps = None
        self.timers = []
        self.last_new_frame_time = 0
        self.meta = {}
        self.frame_lock = Lock()

        self.post_callbacks = []
        self.pre_callbacks = []

    def start(self, target_fps = None):
        """
        Start capture thread with an optional target framerate.

        This can be combined with post-capture hooks to effectively
        throttle the rate of "new images" events that are signaled to
        other software using this code.

        Setting target_fps does _not_ affect the base framerate of the camera.
        That should be set using a subclass and is camera-specific. In general it
        is not a problem to capture images at full speed on an embedded system,
        the problems start when passing them on as messages.

        """

        if target_fps is not None:
            self.target_fps = target_fps

        self.thread = Thread(target=self.update)
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        """
        Main capture loop. This performs the following actions:

        * Calculates the timeout for new frames, if throttling is enabled
        * Tracks inter-frame latency for monitoring against the camera's 
          expected framerate.
        * Calls the pre-capture hook
        * Requests an image from the camera
        * Calls the post-capture hook
        * Checks if the new_image flag should be set
        * Tracks the number of frames

        """
        self.should_stop = False
        self.capturing = True
        self.n_frames = 0

        if self.target_fps:
            self.last_new_frame_time = 0
            self.new_frame_thresh = 1. / self.target_fps

        while True:

            # Track frame start time
            self.frame_time = time.time()

            if self.should_stop:
                break

            # Capture image
            self._pre_capture()
            self.frame_lock.acquire()
            self.latest_image = self._grab()
            self.frame_lock.release()
            self._post_capture()

            # Report new frame (check if throttling)
            self._check_new_frame()

            # Check timers
            self._service_timers()

            # Track frame latency
            self.last_frame_time = time.time()
            if  self.n_frames > 0:
                idx = self.n_frames % len(self.latency)
                self.latency[idx] = self.last_frame_time - self.frame_time

            if self.latest_image is not None:
                self.n_frames += 1

        self.capturing = False

    def _check_new_frame(self):
        """
        Check if the new_image flag should be set. This is:

        * Every new image, if there is no target fps
        * Or if throttling is enabled with target fps, whenever the 
          timeout occurs (e.g. the elapsed time since the previous new
          image exceeds 1/target fps)

        The on_new_capture hook is called afterwards.

        """
        if self.target_fps and (time.time() - self.last_new_frame_time) < self.new_frame_thresh:
            return
        else:
            self.last_new_frame_time = time.time()
            self.new_image = True

            self._on_new_capture()

    def _service_timers(self):
        """
        Service user-added timers. Called in the event loop. The timer
        class is directly responsible for whether it does something or not.

        """

        for timer in self.timers:
            timer.service()

    def add_timer(self, frequency, function, args=[]):
        """
        Add a new timer that will run function every
        `timeout` seconds. This is useful for periodically monitoring
        camera telemetry.

        """
        self.timers.append(TimedService(frequency, function, args))

    def clear_timers(self):
        """
        Remove associated timers

        """
        self.timers = []

    def mean_latency(self):
        """
        Returns the mean capture latency in seconds

        """
        return self.latency[self.latency > 0].mean()

    def stop(self):
        """
        Stop capturing and wait for thread to finish

        """
        if self.thread:
            self.should_stop = True
            self.thread.join()

    def latest(self):
        """
        Returns the latest image captured by the camera.

        Note that this function will always return the last image
        captured by the camera, regardless of target fps.

        Calling this function clears the new_image flag.

        This function acquires a lock on the latest image buffer so that
        it cannot be overwritten while copying out.

        """
        self.frame_lock.acquire()
        image = np.array(self.latest_image)
        self.frame_lock.release()

        self.new_image = False
        return image

    def latest_compressed(self, format=".tiff"):
        """
        Returns a compressed image captured by the camera, in the format
        specified by `format`.

        """

        image = np.array(self.latest())

        if image is not None:
            res, image = cv2.imencode(format, image)

            if not res:
                image = None

        return image

    def get_meta(self):
        return self.meta

    def add_post_callback(self, callback):
        self.post_callbacks.append(callback)

    def _post_capture(self):
        """
        Hook for performing an action post image capture.

        """
        for c in self.post_callbacks:
            c(np.array(self.latest_image))


    def _pre_capture(self):
        """
        Hook for performing an action prior to image capture.

        """
        for c in self.pre_callbacks:
            c()

    @abc.abstractmethod
    def _grab(self):
        """
        Function for capturing an image, should return a numpy array.
        Implementation specific.

        """
        pass

    @abc.abstractmethod
    def _on_new_capture(self):
        """
        Hook for performing an action after the new frame flag
        has been set (useful, for example with ROS to publish
        images at a lower rate).

        """
        pass

    @abc.abstractmethod
    def close(self):
        """
        Abstract method for closing the camera. Implementation specific.

        """
        pass
