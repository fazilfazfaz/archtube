import json
import mimetypes
import os
from wsgiref.util import FileWrapper
import string
from ctypes import windll

from django.shortcuts import render
from ytxplorer_web.repositories import datapipe
from ytxplorer_web.utilities import renderJSON, range_re, RangeFileWrapper
from django.http import HttpResponseBadRequest, FileResponse, StreamingHttpResponse
from dotenv import load_dotenv

allvideodatapipe = datapipe.DataPipe(vinclude='all')
ytvideodatapipe = datapipe.DataPipe(vinclude='yt')
nonytvideodatapipe = datapipe.DataPipe(vinclude='nonyt')
load_dotenv()

def getpipe(include):
    if include == 'yt':
        return ytvideodatapipe
    elif include == 'nonyt':
        return nonytvideodatapipe
    else:
        return allvideodatapipe


# Create your views here.

def index(request):
    drives = []
    bitmask = windll.kernel32.GetLogicalDrives()
    if os.getenv('FAKE_DISKS') == 'True':
        for drive in os.listdir(os.getenv('FAKE_DISKS_FROM')):
            drives.append(drive.upper() + ':')
    else:
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                if os.path.isfile(os.path.join(letter + ':\\', '.ytcataloger.json')):
                    drives.append(letter + ':')
            bitmask >>= 1
    print(drives)
    return render(request, 'index.html', {
        'drives': json.dumps(','.join(drives))
    })


def list_channels(request):
    if 'drives' not in request.GET:
        return HttpResponseBadRequest()
    drives = request.GET['drives']
    page = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 50))
    channels = ytvideodatapipe.list_channels(drives, page, count)
    return renderJSON({
        'channels': channels,
    })


def list_channels_by_term(request):
    if 'drives' not in request.GET or 'term' not in request.GET:
        return HttpResponseBadRequest()
    drives = request.GET['drives']
    term = request.GET['term']
    page = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 50))
    sort = request.GET.get('sort', 'default')
    channels = ytvideodatapipe.list_channels_by_term(drives, term, page, count, sort)
    return renderJSON({
        'channels': channels,
    })


def list_videos(request):
    if 'drives' not in request.GET:
        return HttpResponseBadRequest()
    drives = request.GET['drives']
    page = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 50))
    vinclude = request.GET.get('vinclude', 'all')
    quality_filter = request.GET.get('quality_filter', 'all')
    videos = getpipe(vinclude).list_videos(drives, page, count, quality_filter)
    return renderJSON({
        'videos': videos,
    })


def list_videos_by_term(request):
    if 'drives' not in request.GET or 'term' not in request.GET:
        return HttpResponseBadRequest()
    drives = request.GET['drives']
    term = request.GET['term']
    page = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 50))
    vinclude = request.GET.get('vinclude', 'all')
    quality_filter = request.GET.get('quality_filter', 'all')
    videos = getpipe(vinclude).list_videos_by_term(drives, term, page, count, quality_filter)
    return renderJSON({
        'videos': videos,
    })


def list_videos_by_channel(request):
    if 'drives' not in request.GET or 'channel_id' not in request.GET:
        return HttpResponseBadRequest()
    drives = request.GET['drives']
    channel_id = request.GET['channel_id']
    vchannelsort = request.GET['vchannelsort']
    page = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 50))
    vinclude = request.GET.get('vinclude', 'all')
    quality_filter = request.GET.get('quality_filter', 'all')
    videos = getpipe(vinclude).list_videos_by_channel(drives, channel_id, vchannelsort, page, count, quality_filter)
    return renderJSON({
        'videos': videos,
    })


def play(request):
    if 'video' not in request.GET:
        return HttpResponseBadRequest()
    video = request.GET.get('video')
    range_header = request.META.get('HTTP_RANGE', '').strip()
    range_match = range_re.match(range_header)
    size = os.path.getsize(video)
    content_type, encoding = mimetypes.guess_type(video)
    content_type = content_type or 'application/octet-stream'
    if range_match:
        first_byte, last_byte = range_match.groups()
        first_byte = int(first_byte) if first_byte else 0
        last_byte = int(last_byte) if last_byte else size - 1
        if last_byte >= size:
            last_byte = size - 1
        length = last_byte - first_byte + 1
        resp = StreamingHttpResponse(RangeFileWrapper(open(video, 'rb'), offset=first_byte, length=length), status=206,
                                     content_type=content_type)
        resp['Content-Length'] = str(length)
        resp['Content-Range'] = 'bytes %s-%s/%s' % (first_byte, last_byte, size)
    else:
        resp = StreamingHttpResponse(FileWrapper(open(video, 'rb')), content_type=content_type)
        resp['Content-Length'] = str(size)
    resp['Accept-Ranges'] = 'bytes'
    return resp


def subs(request):
    if 'sub' not in request.GET:
        return HttpResponseBadRequest()
    sub = request.GET.get('sub')
    if not os.path.exists(sub):
        return HttpResponseBadRequest()
    size = os.path.getsize(sub)
    resp = StreamingHttpResponse(FileWrapper(open(sub, 'rb')), content_type='text/vtt')
    resp['Content-Length'] = str(size)
    return resp