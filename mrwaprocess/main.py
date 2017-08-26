# /mrwaprocess/main.py
#
# Entry point for the data processing script. It uses subprocess to shell
# out to a lot of stuff. Sorry :(
#
# See /LICENCE.md for Copyright information

import argparse
import os
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
            pass
            #shutil.rmtree(tempdir)


@contextmanager
def ffmpeg_decompose_srt(video_file):
    """Use ffmpeg to extract a subtitle file from a video file

    The frames themselves are stored in a temporary directory
    relative to the present working directory. This context manager
    yields that subtitles file.
    """
    with temporary_directory(prefix="subtitle", dir=os.getcwd()) as tempdir:
        abs_video_file = os.path.abspath(video_file)
        subprocess.check_call([
            "ffmpeg",
            "-i",
            abs_video_file,
            "-map",
            "0:s:0",
            "subs.srt",
            "%04d.jpg"
        ], cwd=tempdir)
        try:
            yield os.path.join(tempdir, "subs.srt")
        finally:
            pass
            #shutil.rmtree(tempdir)


def main(argv=None):
    """Take a video, some weights and model configs and recognize."""
    parser = argparse.ArgumentParser("""MRWA Autotagger.""")
    parser.add_argument("videos",
                        nargs="+",
                        help="""The videos to process.""",
                        metavar="VIDEO")
    result = parser.parse_args(argv or sys.argv[1:])

    for video in result.videos:
        with ffmpeg_decompose_video(video) as images_directory:
            with ffmpeg_decompose_srt(video) as subtitles_filename:
                print("Images directory: {}".format(images_directory))
                print("Subtitles filename: {}".format(subtitles_filename))
