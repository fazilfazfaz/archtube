import json
import os
import random
import re


class DataPipe:
    infofile = '.ytcataloger.json'

    def __init__(self, vinclude='all'):
        self.vinclude = vinclude
        self.videos = {}
        self.videos_by_term = {}
        self.videos_by_channel = {}
        self.channels = {}
        self.channels_by_term = {}
        self.channel_counts = {}

    # video ops

    def get_info_file_absolute_path(self, drive):
        if os.getenv('FAKE_DISKS') == 'True':
            return os.path.join(os.getenv('FAKE_DISKS_FROM'), drive[0].lower())
        else:
            return os.path.join(drive, self.infofile)

    def load_videos(self, drives):
        if drives in self.videos:
            return
        print('Caching %s' % drives)
        self.videos[drives] = []
        for drive in drives.split(','):
            print('Caching {}'.format(drive))
            infofilepath = self.get_info_file_absolute_path(drive)
            with open(infofilepath, 'r') as f:
                if self.vinclude == 'yt':
                    self.videos[drives] += list(
                        filter(lambda x: x['video_id'] is not None, json.loads(f.read()).get('videos')))
                    # self.videos[drives].sort(key=lambda v: v['info']['snippet']['publishedAt'] if 'info' in v and v['info'] is not None else '1970-01-01T17:02:47.000Z', reverse=True)

                elif self.vinclude == 'nonyt':
                    self.videos[drives] += list(
                        filter(lambda x: 'alt_thumb' in x, json.loads(f.read()).get('videos')))
                else:
                    self.videos[drives] += json.loads(f.read()).get('videos')
                if os.getenv('FAKE_DISKS') == 'True':
                    self.videos[drives].sort(
                        key=lambda v: v['info']['snippet']['publishedAt'] if 'info' in v and v['info'] is not None else '1970-01-01T00:00:00.000Z', reverse=True)
                else:
                    self.videos[drives].sort(key=lambda v: self.getctime(v['path']), reverse=True)
                if os.getenv('RANDOMIZE') == 'True':
                    random.shuffle(self.videos[drives])
        print("Total Videos: " + str(len(self.videos[drives])))
        print("Total YT Videos: " + str(len(list(filter(lambda x: 'info' in x and x['info'] is not None, self.videos[drives])))))


    def load_videos_by_term(self, drives, term):
        if drives in self.videos_by_term and term in self.videos_by_term[drives]:
            return
        if drives not in self.videos_by_term:
            self.videos_by_term[drives] = {}
        pattern = re.compile(term, re.IGNORECASE)
        self.videos_by_term[drives][term] = list(
            filter(lambda v: pattern.search(v['path']) is not None or (
                    'info' in v and v['info'] is not None and pattern.search(
                v['info']['snippet']['title']) is not None),
                   self.videos[drives]))

    def sort_videos_by_channels(self, drives, channel_id, sort):
        if sort == 'oldest':
            self.videos_by_channel[drives][channel_id].sort(key=lambda v: v['info']['snippet']['publishedAt'])
        elif sort == 'newest':
            self.videos_by_channel[drives][channel_id].sort(key=lambda v: v['info']['snippet']['publishedAt'],
                                                            reverse=True)
        elif sort == 'created':
            if os.getenv('FAKE_DISKS') == 'True':
                self.videos_by_channel[drives][channel_id].sort(key=lambda v: v['info']['snippet']['publishedAt'], reverse=True)
            else:
                self.videos_by_channel[drives][channel_id].sort(key=lambda v: self.getctime(v['path']), reverse=True)

    def load_videos_by_channel(self, drives, channel_id, vchannelsort):
        if drives in self.videos_by_channel and channel_id in self.videos_by_channel[drives]:
            self.sort_videos_by_channels(drives, channel_id, vchannelsort)
            return
        if drives not in self.videos_by_channel:
            self.videos_by_channel[drives] = {}
        self.videos_by_channel[drives][channel_id] = list(
            filter(lambda v: 'info' in v and v['info'] is not None and v['info']['snippet']['channelId'] == channel_id,
                   self.videos[drives]))
        self.videos_by_channel[drives][channel_id].sort(key=lambda v: v['info']['snippet']['publishedAt'])
        self.sort_videos_by_channels(drives, channel_id, vchannelsort)

    def videos_after_quality_filter(self, videos, quality_filter):
        if quality_filter != 'all':
            return list(
                filter(lambda x: 'codec' in x and x['codec'] is not None and x['codec']['label'] == quality_filter,
                       videos))
        return videos

    def list_videos(self, drives, page, count, quality_filter='all'):
        self.load_videos(drives)
        start = (page - 1) * count
        end = start + count
        return self.videos_after_quality_filter(self.videos[drives], quality_filter)[start:end]

    def list_videos_by_term(self, drives, term, page, count, quality_filter='all'):
        self.load_videos(drives)
        self.load_videos_by_term(drives, term)
        start = (page - 1) * count
        end = start + count
        return self.videos_after_quality_filter(self.videos_by_term[drives][term], quality_filter)[start:end]

    def list_videos_by_channel(self, drives, channel_id, vchannelsort, page, count, quality_filter='all'):
        self.load_videos(drives)
        self.load_videos_by_channel(drives, channel_id, vchannelsort)
        start = (page - 1) * count
        end = start + count
        return self.videos_after_quality_filter(self.videos_by_channel[drives][channel_id], quality_filter)[start:end]

    # channels ops

    @staticmethod
    def get_channel_thumb(thumbs):
        if 'maxres' in thumbs:
            return thumbs['maxres']['url']
        if 'high' in thumbs:
            return thumbs['high']['url']
        if 'default' in thumbs:
            return thumbs['default']['url']

    def load_channels(self, drives):
        if drives in self.channels:
            return
        self.load_videos(drives)
        self.channels[drives] = []
        processed = []
        self.channel_counts[drives] = {}
        for v in self.videos[drives]:
            if v['info'] is not None:
                self.channel_counts[drives][v['info']['snippet']['channelId']] = 1 if v['info']['snippet'][
                                                                                          'channelId'] not in \
                                                                                      self.channel_counts[drives] else \
                    self.channel_counts[drives][v['info']['snippet']['channelId']] + 1
                if v['info']['snippet']['channelId'] not in processed:
                    processed.append(v['info']['snippet']['channelId'])
                    self.channels[drives].append({
                        'id': v['info']['snippet']['channelId'],
                        'title': v['info']['snippet']['channelTitle'],
                        'thumb': self.get_channel_thumb(v['info']['snippet']['thumbnails']),
                    })

    def load_channels_by_term(self, drives, term, sort):
        if drives in self.channels_by_term and term in self.channels_by_term[drives]:
            return
        if drives not in self.channels_by_term:
            self.channels_by_term[drives] = {}
        pattern = re.compile(term, re.IGNORECASE)
        self.channels_by_term[drives][term] = list(
            filter(lambda v: pattern.search(v['title']) is not None, self.channels[drives]))
        if sort == 'count':
            self.channels_by_term[drives][term].sort(key=lambda x: self.channel_counts[drives][x['id']], reverse=True)

    def list_channels(self, drives, page, count):
        self.load_channels(drives)
        start = (page - 1) * count
        end = start + count
        return self.channels[drives][start:end]

    def list_channels_by_term(self, drives, term, page, count, sort):
        self.load_channels(drives)
        self.load_channels_by_term(drives, term, sort)
        start = (page - 1) * count
        end = start + count
        return self.channels_by_term[drives][term][start:end]

    def getctime(self, path):
        if os.getenv('FAKE_DISKS') == 'True':
            return 0
        try:
            return os.path.getctime(path)
        except:
            return 0
