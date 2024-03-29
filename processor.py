import argparse
import json
import os
import re
import string
import subprocess
import time
from ctypes import windll
from itertools import islice
from threading import Thread

import googleapiclient.discovery
import googleapiclient.errors
import math
from dotenv import dotenv_values

config = dotenv_values('.env')

api_service_name = 'youtube'
api_version = 'v3'
devKey = config['GOOGLE_KEY']
logfile = '.ytcataloger.json'
infofile = '.ytcataloger-info.json'


def chunk(it, size):
    it = iter(it)
    return iter(lambda: tuple(islice(it, size)), ())


def get_video_info(videos):
    video_map = {}
    for video in videos:
        video_map[video['video_id']] = video
    youtube_ids = list(map(lambda x: x['video_id'], videos))

    youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey=devKey)
    request = youtube.videos().list(
        part="snippet,contentDetails,statistics",
        id=",".join(youtube_ids[0:50])
    )
    response = request.execute()
    return response['items']


def log(txt):
    print(txt)


def writelog(videos, pathkey):
    with open(logfile, 'w') as f:
        f.write(json.dumps({
            'drives': pathkey,
            'videos': videos
        }))


def gen_fake_thumbs(videos):
    for video in videos:
        try:
            folders = video['path'].split("\\")
            output_path = "static"
            for folder in folders[0:-1]:
                if len(folder) == 2 and folder[1:] == ':':
                    output_path = os.path.join(output_path, folder[0])
                else:
                    output_path = os.path.join(output_path, folder)
            command = 'ffprobe -v quiet -print_format json -show_format -show_streams "%s"' % video['path']
            out = subprocess.check_output(command)
            j = json.loads(out)
            duration = math.floor(float(j['format']['duration']))
            capture_time = math.floor(duration / 2)
            basename = os.path.basename(video['path'])
            output_file = os.path.join(output_path, basename + '.png')
            command = 'ffmpeg -y -ss %s -i "%s" -frames:v 1 "%s"' % (capture_time, video['path'], output_file)
            if not os.path.isdir(output_path):
                os.makedirs(output_path)
            picproduced = subprocess.call(command, stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, 'wb'))
            assert picproduced == 0
            video['alt_thumb'] = output_file
            print('Generated thumb for %s' % video['path'])
        except Exception as e:
            print(e)
            print('Thumb not generated for %s' % video['path'])


def get_video_quality_label(video_width):
    if video_width < 1200:
        return 'SD'
    elif video_width < 1920:
        return 'HD'
    elif video_width < 3800:
        return 'FHD'
    else:
        return 'UHD+'


def get_video_codec_info(video_with_no_info):
    command = 'ffprobe -i "{}" -show_streams -select_streams v -print_format json -v quiet'.format(
        video_with_no_info['path'])
    out = subprocess.check_output(command, shell=True)
    assert out is not None
    data = json.loads(out.decode('utf-8'))
    if len(data['streams']) < 1:
        return None
    return {
        'width': data['streams'][0]['width'],
        'height': data['streams'][0]['height'],
        'label': get_video_quality_label(data['streams'][0]['width']),
    }


def process_videos_for_codec(videos, drive, gen_thumbs, startpaths):
    scanpath = drive
    if startpaths is not None:
        for path in startpaths:
            if path[0:3] == drive:
                scanpath = path
                break

    videos_without_info = filter(lambda x: 'codec' not in x and x['path'].startswith(scanpath), videos)
    remaining = len(videos)
    # log("Queued for video info: {}".format(len(videos_without_info)))

    MAX_THREAD_COUNT = 10
    CURRENT_THREAD_COUNT = 0

    def info_processor(video):
        nonlocal CURRENT_THREAD_COUNT
        nonlocal remaining
        try:
            video['codec'] = get_video_codec_info(video_with_no_info)
            # remaining = remaining - len(set)
        except Exception as e:
            print("Could not resolve info with ffprobe {}".format(str(e)))
            video['codec'] = None
        CURRENT_THREAD_COUNT = CURRENT_THREAD_COUNT - 1

    setc = 0
    for video_with_no_info in videos_without_info:
        while CURRENT_THREAD_COUNT > MAX_THREAD_COUNT:
            time.sleep(2)
        setc += 1
        CURRENT_THREAD_COUNT = CURRENT_THREAD_COUNT + 1
        Thread(target=info_processor, args=(video_with_no_info,)).start()

    while CURRENT_THREAD_COUNT > 0:
        time.sleep(5)

    write_drive_log(drive, videos)


def process_videos(videos, drive, gen_thumbs, startpaths):
    videos_without_info = filter(lambda x: 'info' not in x and x['video_id'] is not None, videos)
    videos_without_info = filter(lambda x: not os.path.exists(os.path.join(os.path.dirname(x['path']), '.nomedia')),
                                 videos_without_info)
    video_chunks = chunk(videos_without_info, 50)
    remaining = len(videos)

    MAX_THREAD_COUNT = 10
    CURRENT_THREAD_COUNT = 0

    def info_processor(set):
        nonlocal CURRENT_THREAD_COUNT
        nonlocal remaining
        try:
            infos = get_video_info(set)
            for video in set:
                info = list(filter(lambda x: x['id'] == video['video_id'], infos))
                if len(info) > 0:
                    video['info'] = info[0]
                else:
                    video['info'] = None
            # remaining = remaining - len(set)
        except Exception as e:
            print("Couldn not resolve info from yt {}".format(str(e)))
        CURRENT_THREAD_COUNT = CURRENT_THREAD_COUNT - 1

    setc = 0
    for video_set in video_chunks:
        while CURRENT_THREAD_COUNT > MAX_THREAD_COUNT:
            time.sleep(2)
        setc += 1
        log("Queued: %s" % setc)
        CURRENT_THREAD_COUNT = CURRENT_THREAD_COUNT + 1
        Thread(target=info_processor, args=(video_set,)).start()

    while CURRENT_THREAD_COUNT > 0:
        time.sleep(5)
    if gen_thumbs:
        videos_with_empty_info = filter(lambda x: 'alt_thumb' not in x and ('info' not in x or x['info'] is None),
                                        videos)
        scanpath = drive
        if startpaths is not None:
            for path in startpaths:
                if path[0:3] == drive:
                    scanpath = path
                    break
        videos_with_empty_info = filter(lambda x: x['path'].startswith(scanpath), videos_with_empty_info)
        gen_fake_thumbs(videos_with_empty_info)

    write_drive_log(drive, videos)


def write_drive_log(drive, tempvideos):
    # return
    with open(os.path.join(drive, logfile), 'w') as f:
        f.write(json.dumps({
            'videos': tempvideos,
            'drive': drive
        }))


def main():
    parser = argparse.ArgumentParser(description="YouTube Cataloging Tool")
    parser.add_argument("-drives", nargs="+")
    parser.add_argument("-startpaths", nargs="+")
    parser.add_argument("-no_gen_thumbs", action='store_true')
    parser.add_argument("-force_clean_missing", action='store_true')
    parser.add_argument("-no_youtube_fetch", action='store_true')
    args = parser.parse_args()
    drives = []

    if devKey is None:
        raise Exception("Set the YouTube / Google API access token in the devKey variable first!")

    if args.drives is not None and len(args.drives) > 0:
        for drive in args.drives:
            if not os.path.ismount(drive):
                raise Exception("Invalid mount point passed")
            if not os.path.isdir(drive):
                raise Exception("Invalid drive passed")
            drives.append(drive)
    else:
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                if os.path.isfile(os.path.join(letter + ':\\', '.ytcataloger.json')):
                    drives.append(letter + ':\\')
            bitmask >>= 1

    video_file_pattern = re.compile(r'(-(.{11}))?\.(mp4|mkv|webm|ts|m2ts)$')
    dataset = {}
    vidcount = 0

    for drive in drives:
        log("Processing drive %s" % drive)
        logfilepath = os.path.join(drive, logfile)
        tempvideos = []
        if os.path.isfile(logfilepath):
            with open(logfilepath, 'r') as f:
                json_data = json.loads(f.read())
                if json_data.get('drive') != drive:
                    raise Exception("One of the drives are misconfigured!")
                tempvideos = json_data.get('videos')
                # vidcount = vidcount + len(dataset[drive])
                log("Read files from log for %s" % drive)
                # continue
        # for index, video in enumerate(tempvideos):
        #     if not os.path.isfile(video['path']):
        #         tempvideos.pop(index)
        scanpath = drive
        if args.startpaths is not None:
            for path in args.startpaths:
                if path[0:3] == drive:
                    scanpath = path
                    break
        if scanpath == drive or args.force_clean_missing:
            missingfiles = filter(lambda x: not os.path.isfile(x['path']), tempvideos)
            for missingfile in missingfiles:
                print(missingfile['path'])
            tempvideos = list(filter(lambda x: os.path.isfile(x['path']), tempvideos))
            log("Cleaned missing files")
        for root, curdir, files in os.walk(scanpath):
            for file in files:
                m = re.search(video_file_pattern, file)
                abspath_file = os.path.join(root, file)
                if m is not None:
                    vid = m.group(2)
                    if vid is not None:
                        vsearch = filter(lambda x: x['video_id'] == vid, tempvideos)
                        if any(True for _ in vsearch):
                            continue
                    else:
                        vsearch = filter(lambda x: x['path'] == abspath_file, tempvideos)
                        if any(True for _ in vsearch):
                            continue
                    tempvideos.append({
                        'path': abspath_file,
                        'video_id': vid,
                        'size': os.path.getsize(abspath_file)
                    })
        write_drive_log(drive, tempvideos)
        dataset[drive] = tempvideos.copy()
        vidcount = vidcount + len(dataset[drive])

    log("Discovered %s videos" % vidcount)

    totsize = 0
    for drive in dataset:
        if args.no_youtube_fetch is False:
            process_videos(dataset[drive], drive, args.no_gen_thumbs is False, args.startpaths)
        process_videos_for_codec(dataset[drive], drive, args.no_gen_thumbs is False, args.startpaths)
        for v in dataset[drive]:
            totsize += v.get('size')
        # break

    # print(totsize)


if __name__ == '__main__':
    main()
