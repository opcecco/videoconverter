#!/usr/bin/env python3

import datetime as dt
import os
import re
import subprocess

from gooey import Gooey, GooeyParser, local_resource_path

IMAGES_PATH = local_resource_path('images')
FFPROBE_PATH = local_resource_path('ffmpeg-7.1-essentials_build/bin/ffprobe.exe')
FFMPEG_PATH = local_resource_path('ffmpeg-7.1-essentials_build/bin/ffmpeg.exe')


def parse_time(timestring):

    time_formats = [
        '%H:%M:%S.%f',
        '%H:%M:%S',
        '%M:%S.%f',
        '%M:%S',
        '%S.%f',
        '%S',
    ]

    for tform in time_formats:
        try:
            return dt.datetime.strptime(timestring,tform)
        except ValueError:
            pass
    raise Exception(f'Could not parse time string: "{timestring}"')


def ffprobe_duration(input_filename):

    ffprocess = subprocess.Popen([
        FFPROBE_PATH,
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        input_filename
    ],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    stdin=subprocess.DEVNULL, shell=True, universal_newlines=True)

    ffprocess.wait()
    if ffprocess.returncode:
        raise Exception(f'Error in ffprobe')

    output = ffprocess.communicate()[0]
    return float(output)


def process_ff_output(ffprocess,
                      clip_duration,
                      part = 0,
                      total_parts = 2,
                      time_regex = re.compile(r'time=\s*([\d\:\.]+)\s+'),
                      zero_time = dt.datetime(1900, 1, 1, 0, 0)):

    for line in ffprocess.stdout:
        print(line.rstrip())

        if match := time_regex.search(line):
            timecode = match.groups()[0]
            delta = parse_time(timecode) - zero_time
            progress = clip_duration * part + delta.total_seconds()
            print(f'PROGRESS: {int(progress)}/{int(clip_duration * total_parts)}')

    ffprocess.wait()
    if ffprocess.returncode:
        raise Exception(f'Error in ffmpeg pass {part + 1}')


def convert(input_filename,
            output_filename,
            clip_enabled,
            clip_from,
            clip_to,
            scale_width,
            scale_height,
            framerate,
            aspect_enabled,
            aspect_width,
            aspect_height,
            target_video_size_mb,
            encoding_speed,
            audio_bitrate_kbps,
            output_format,
            video_lib,
            audio_lib):

    if clip_enabled:
        clip_duration = (parse_time(clip_to) - parse_time(clip_from)).total_seconds()
        clip_args = [
            '-ss', clip_from,
            '-to', clip_to,
        ]
    else:
        clip_duration = ffprobe_duration(input_filename)
        clip_args = []

    desired_bitrate_kbps = (target_video_size_mb * 8192) / (clip_duration * 1.05)
    target_video_bitrate_kbps = desired_bitrate_kbps - audio_bitrate_kbps

    crop_string = ''
    if aspect_enabled:
        crop_string = f'crop=ih/{aspect_height}*{aspect_width}:ih,'

    print('working dir:', os.getcwd())
    print('clip duration:', clip_duration)
    print('video bitrate:', target_video_bitrate_kbps)

    ffprocess = subprocess.Popen([
        FFMPEG_PATH,
        '-y',
        '-i', input_filename,
        *clip_args,
        '-r', f'{framerate}',
        '-vf', f'{crop_string}scale={scale_width}:{scale_height}',
        '-c:v', video_lib,
        '-b:v', f'{target_video_bitrate_kbps}k',
        '-preset', encoding_speed,
        '-c:a', audio_lib,
        '-b:a', f'{audio_bitrate_kbps}k',
        '-f', output_format,
        '-pass', '1',
        'NUL'
    ],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    stdin=subprocess.DEVNULL, shell=True, universal_newlines=True)

    print(ffprocess.args)
    process_ff_output(ffprocess, clip_duration, part=0)

    ffprocess = subprocess.Popen([
        FFMPEG_PATH,
        '-y',
        '-i', input_filename,
        *clip_args,
        '-r', f'{framerate}',
        '-vf', f'{crop_string}scale={scale_width}:{scale_height}',
        '-c:v', video_lib,
        '-b:v', f'{target_video_bitrate_kbps}k',
        '-preset', encoding_speed,
        '-c:a', audio_lib,
        '-b:a', f'{audio_bitrate_kbps}k',
        '-f', output_format,
        '-pass', '2',
        output_filename
    ],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    stdin=subprocess.DEVNULL, shell=True, universal_newlines=True)

    print(ffprocess.args)
    process_ff_output(ffprocess, clip_duration, part=1)


@Gooey(
    program_name='Zutano\'s Video Converter Script v1.7',
    image_dir=IMAGES_PATH,
    default_size=(800, 900),
    progress_regex=r'^PROGRESS: (?P<current>\d+)/(?P<total>\d+)$',
    progress_expr='current / total * 100',
    hide_progress_msg=True,
    clear_before_run=True
)
def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    parser = GooeyParser(description="Convert a video to the desired file size")

    basic_settings = parser.add_argument_group()
    basic_settings.add_argument(
        'input_filename', metavar='Input File', type=str,
        help='Video file to convert',
        widget='FileChooser',
        gooey_options={
            'wildcard': "MP4 (*.mp4)|*.mp4|All files (*.*)|*.*",
        }
    )
    basic_settings.add_argument(
        'output_filename', metavar='Output File', type=str,
        help='Output file name',
        widget='FileSaver',
        gooey_options={
            'wildcard': "MP4 (*.mp4)|*.mp4|All files (*.*)|*.*",
        }
    )
    basic_settings.add_argument(
        'clip_from', metavar='Clip Start (MM:SS)', type=str,
        help='Starting timepoint to clip in the format MM:SS',
        default='00:00'
    )
    basic_settings.add_argument(
        'clip_to', metavar='Clip End (MM:SS)', type=str,
        help='Ending timepoint to clip in the format MM:SS',
        default='00:30'
    )
    basic_settings.add_argument(
        '--clip', metavar='Clip Video', action='store_true',
        help='Enable clipping the video to the desired timepoints'
    )

    advanced_settings = parser.add_argument_group(
        'Advanced Settings',
        gooey_options={'show_border': True}
    )
    advanced_settings.add_argument(
        'resolution', metavar='Resolution', type=str,
        help='Output video resolution',
        choices=['480p', '720p', '1080p'], default='1080p'
    )
    advanced_settings.add_argument(
        'framerate', metavar='Frame Rate', type=int,
        help='Output video frames per second',
        default=60
    )
    advanced_settings.add_argument(
        'aspect', metavar='Aspect Ratio', type=str,
        help='Output video aspect ratio',
        choices=['Original', '16:9', '21:9'], default='Original'
    )
    advanced_settings.add_argument(
        'target_size', metavar='Target File Size (MB)', type=float,
        help='Desired size of the output video file in megabytes',
        default=10
    )
    advanced_settings.add_argument(
        'encoding_speed', metavar='Encoding Speed', type=str,
        help='Encoding speed preset (slowest for best quality)',
        choices=[
            'ultrafast',
            'superfast',
            'veryfast',
            'faster',
            'fast',
            'medium',
            'slow',
            'slower',
            'veryslow',
        ], default='veryslow'
    )
    advanced_settings.add_argument(
        'format', metavar='Output File Format', type=str,
        help='Format of the output video file',
        choices=['mp4'], default='mp4'
    )
    advanced_settings.add_argument(
        'audio_bitrate', metavar='Audio Bitrate (kbps)', type=int,
        help='Output audio bitrate in kilobits per second',
        default=128
    )
    advanced_settings.add_argument(
        'video_lib', metavar='Video Encoder', type=str,
        help='Encoder library for output video',
        choices=['libx264'], default='libx264'
    )
    advanced_settings.add_argument(
        'audio_lib', metavar='Audio Encoder', type=str,
        help='Encoder library for output audio',
        choices=['aac'], default='aac'
    )

    args = parser.parse_args()
    print(args)

    height = {
        '480p': 480,
        '720p': 720,
        '1080p': 1080,
    }[args.resolution]

    should_crop = (args.aspect != 'Original')
    aspect_width, aspect_height = {
        'Original': (0, 0),
        '16:9': (16, 9),
        '21:9': (21, 9),
    }[args.aspect]

    convert(
        args.input_filename,
        args.output_filename,
        args.clip,
        args.clip_from,
        args.clip_to,
        -2,
        height,
        args.framerate,
        should_crop,
        aspect_width,
        aspect_height,
        args.target_size,
        args.encoding_speed,
        args.audio_bitrate,
        args.format,
        args.video_lib,
        args.audio_lib
    )


if __name__ == '__main__':
    main()
