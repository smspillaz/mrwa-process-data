# /mrwaprocess/main.py
#
# Entry point for the data processing script. It uses subprocess to shell
# out to a lot of stuff. Sorry :(
#
# See /LICENCE.md for Copyright information

import argparse
import csv
import errno
import fnmatch
import os
import re
import shutil
import subprocess
import sys
import tempfile

from contextlib import contextmanager


@contextmanager
def temporary_directory(**kwargs):
    """Do something in a temporary directory, yielding it."""
    tempdir = tempfile.mkdtemp(**kwargs)

    try:
        yield tempdir
    finally:
        pass
        # shutil.rmtree(tempdir)


@contextmanager
def ffmpeg_decompose_video(video_file):
    """Use ffmpeg to break down a video file into its frames.

    The frames themselves are stored in a temporary directory
    relative to the present working directory. This context manager
    yields that directory.
    """
    with temporary_directory(prefix="decomposed", dir=os.getcwd()) as tempdir:
        abs_video_file = os.path.abspath(video_file)
        subprocess.check_call(["ffmpeg", "-i", abs_video_file, "%04d.jpg"],
                              cwd=tempdir)
        try:
            yield tempdir
        finally:
            shutil.rmtree(tempdir)


@contextmanager
def ffmpeg_decompose_srt(video_file):
    """Use ffmpeg to extract a subtitle file from a video file

    The frames themselves are stored in a temporary directory
    relative to the present working directory. This context manager
    yields that subtitles file.
    """
    with temporary_directory(prefix="subtitle", dir=os.getcwd()) as tempdir:
        abs_video_file = os.path.abspath(video_file)
        try:
            subprocess.check_call([
                "ffmpeg",
                "-i",
                abs_video_file,
                "-map",
                "0:s:0?",
                "subs.srt",
                "%04d.jpg"
            ], cwd=tempdir)
        except subprocess.CalledProcessError:
            with open(os.path.join(tempdir, "subs.srt"), "w") as f:
                f.write("\n\n")


        try:
            yield os.path.join(tempdir, "subs.srt")
        finally:
            pass
            #shutil.rmtree(tempdir)


def darknet_run_detections(darknet_executable,
                           darknet_model_config,
                           darknet_yolo_config,
                           darknet_weights,
                           images_directory):
    """Use darknet to run detections on the images.

    Provide the full path to the darknet executable, a set of
    trained weights, a YOLOv2 config, a model config
    and the directory to the images. This function yields
    three-tuples of images filenames and bounding boxes
    along with the classification and percentage probability
    that the bounding box is that classification.
    """

    images = [
        os.path.join(images_directory, i)
        for i in fnmatch.filter(os.listdir(images_directory), "*.jpg")
    ]
    proc = subprocess.Popen([os.path.abspath(darknet_executable),
                             "detector",
                             "testmany",
                             os.path.abspath(darknet_model_config),
                             os.path.abspath(darknet_yolo_config),
                             os.path.abspath(darknet_weights)] + images,
                            cwd=os.path.dirname(darknet_executable),
                            stdout=subprocess.PIPE)
    output, error = proc.communicate()

    for line in output.decode().splitlines():
        filename, label, prob, left, right, top, bottom = line.strip().split(",")
        yield (filename, label, prob, (left, right, top, bottom))


FRAMES_PER_SECONDS = 5


def timecode(subtitle, frame):
    """Tells at which time on the video the frame has been taken """
    with open(subtitle, "r") as f:
        lines = f.readlines()
        res = lines[frame * 4 + 1]
    res = float(res[7:10].replace(",", "."))  # time elapsed between the start and the first subtitle
    return res


def first_frame(subtitle):
    """Finds the frame with some subtitles """
    try:
        return int(FRAMES_PER_SECONDS * timecode(subtitle, 0))  # consider substracting 1 if needed
    except ValueError:
        return 0


def check_correspondance_frame_subtitle(subtitle, last_frame, last_timecode):
    """Checks whether the next frame is subbed (not in use) """
    return timecode(subtitle, last_frame) == last_timecode + 1 / FRAMES_PER_SECONDS


def find_frames_from_images_directory(images_directory):
    """Find and sort all frame images from the images directory."""
    return sorted([os.path.join(images_directory, fn)
                   for fn in os.listdir(images_directory)],
                  key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))


def match_frame_images_to_subtitles(frame_images, subtitles_file):
    """Open the subtitles file and match frame images to it."""
    first_frame_no = first_frame(subtitles_file)

    with open(subtitles_file, "r") as fp:
        lines = fp.readlines()
        lines_len = len(lines)
        for i in range(first_frame_no, len(frame_images)):
            line = (i - first_frame_no) * 4 + 2

            # We are slightly out of sync. Return early.
            if line >= lines_len:
                break

            yield (frame_images[i], lines[line].strip())


_RE_PARSE_SUBTITLE = r".*?(?P<name>[\w\d\s]+?)(?P<dist>\b[0-9\.a-z]+)\s\((?P<date>[\d\/]+)\)"


def parse_subtitle(subtitle):
    """Parse a subtitle into its components."""
    match = re.match(_RE_PARSE_SUBTITLE, subtitle)
    if match:
        return match.groupdict()

    return {
        "name": "",
        "dist": "",
        "date": ""
    }


def result_tuples_for_video(darknet_executable,
                            darknet_model_config,
                            darknet_yolo_config,
                            darknet_weights,
                            images_directory,
                            subtitles_filename):
    """Yield tuples of results for this video.

    The results can be placed in a CSV file, for instance.
    """
    matched_frames = dict(
	match_frame_images_to_subtitles(
	    find_frames_from_images_directory(images_directory),
	    subtitles_filename
	)
    )

    detection_results = darknet_run_detections(darknet_executable,
					       darknet_model_config,
					       darknet_yolo_config,
					       darknet_weights,
					       images_directory)

    for image_filename, label, probability, box in detection_results:
        # If this fails, then we'll just have no subtitle data for this image
	matched_frame = matched_frames.get(image_filename, "")
        subtitle_components = parse_subtitle(matched_frame)
	yield (image_filename,
	       subtitle_components["name"],
	       subtitle_components["dist"],
	       subtitle_components["date"],
	       label,
	       probability,
	       box[0],
               box[1],
               box[2],
               box[3])


def process_video(video,
                  darknet_executable,
                  darknet_model_config,
                  darknet_yolo_config,
                  darknet_weights,
                  output_directory):
    """Process a video, moving its files into the output directory."""
    with ffmpeg_decompose_video(video) as images_directory:
        with ffmpeg_decompose_srt(video) as subtitles_filename:
            video_directory = os.path.join(output_directory,
                                           os.path.splitext(os.path.basename(video))[0])
            try:
                os.makedirs(video_directory)
            except OSError as error:
                if error.errno != errno.EEXIST:
                    raise error

            with open(os.path.join(video_directory, "results.csv"), "w") as f:
                writer = csv.writer(f)

                for tup in result_tuples_for_video(darknet_executable,
                                                   darknet_model_config,
                                                   darknet_yolo_config,
                                                   darknet_weights,
                                                   images_directory,
                                                   subtitles_filename):
                    image_filename = tup[0]
                    image_base_filename = os.path.basename(image_filename)

                    shutil.copyfile(image_filename, os.path.join(video_directory,
                                                                 image_base_filename))
                    writer.writerow([image_base_filename] + list(tup[1:]))


def main(argv=None):
    """Take a video, some weights and model configs and recognize."""
    parser = argparse.ArgumentParser("""MRWA Autotagger.""")
    parser.add_argument("videos",
                        nargs="+",
                        help="""The videos to process.""",
                        metavar="VIDEO")
    parser.add_argument("--darknet-model-config",
                        type=str,
                        help="""The path to the cfg/obj.data file.""",
                        metavar="MODEL_CONFIG",
                        required=True)
    parser.add_argument("--darknet-yolo-config",
                        type=str,
                        help="""The path to the cfg/yolo-obj.cfg file.""",
                        metavar="YOLO_CONFIG",
                        required=True)
    parser.add_argument("--darknet-weights",
                        type=str,
                        help="""The path to the trained darknet weights.""",
                        metavar="WEIGHTS",
                        required=True)
    parser.add_argument("--darknet-executable",
                        type=str,
                        help="""The path to the darknet executable.""",
                        metavar="DARKNET_EXECUTABLE",
                        required=True)
    parser.add_argument("--output",
                        type=str,
                        help="""DIRECTORY file to write results to.""",
                        metavar="OUTPUT",
                        required=True)
    result = parser.parse_args(argv or sys.argv[1:])

    for video in result.videos:
        process_video(video,
                      result.darknet_executable,
                      result.darknet_model_config,
                      result.darknet_yolo_config,
                      result.darknet_weights,
                      result.output)

