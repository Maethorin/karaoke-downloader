#!/usr/bin/env python
# -*- coding: utf-8 -*-]

import os
from time import sleep
import gspread
from oauth2client.service_account import ServiceAccountCredentials

import pytube
from progress import bar
from pytube import exceptions
from slugify import slugify

FORMATS_THAT_I_LIKE = ['mp4', 'flv']
RESOLUTIONS_THAT_I_COULD_LIVE_WITH = ['1080p', '720p', '480p', '360p']
OH_SHEET_COLUNM_MAP = {'song': 0, 'singer': 1, 'category': 2, 'url': 3, 'is_downloaded': 4, 'is_karaoke': 5, 'result': 6}
LOOPS = 0
INTERVAL=int(os.environ.get('INTERVAL', 60))
KEYFILE = os.environ['KEYFILE']
DOWNLOADED_PATH = os.environ['DOWNLOADED_PATH']


class Video(object):
    def __init__(self, linha_planilha):
        self.song = linha_planilha[OH_SHEET_COLUNM_MAP['song']]
        self.singer = linha_planilha[OH_SHEET_COLUNM_MAP['singer']]
        self.url = linha_planilha[OH_SHEET_COLUNM_MAP['url']]
        self.category = linha_planilha[OH_SHEET_COLUNM_MAP['category']]
        self.is_downloaded = linha_planilha[OH_SHEET_COLUNM_MAP['is_downloaded']] == 'S'
        self.is_karaoke = linha_planilha[OH_SHEET_COLUNM_MAP['is_karaoke']] == 'S'
        self.pretty_file_name = slugify(self.song)
        self.file_path = os.path.join(slugify(self.category), slugify(self.singer))
        if self.is_karaoke:
            self.file_path = os.path.join('karaoke', self.file_path)
        else:
            self.file_path = os.path.join('zona', self.file_path)


def gs_credentials():
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    return ServiceAccountCredentials.from_json_keyfile_name(KEYFILE, scope)


def main():
    print('Loging In')
    gc = gspread.authorize(gs_credentials())
    print('Loading Sheet')
    oh_sheet = gc.open('Youtloader').sheet1
    videos_list = oh_sheet.get_all_values()
    progress_bar = bar.Bar('Reading oh_sheet', max=(len(videos_list) - 1))
    results = []
    for index, dados_video in enumerate(videos_list[1:]):
        progress_bar.next()
        video = Video(dados_video)
        if video.is_downloaded:
            continue
        if not video.url:
            results.append(u'"{}" doesnt have a URL. Why?'.format(video.song))
            continue
        try:
            youtube = pytube.YouTube(video.url)
        except exceptions.RegexMatchError as ex:
            oh_sheet.update_acell('G{}'.format(index + 2), 'VSF: REGEX Error... REGEX is always an ERROR!')
            results.append('VSF: REGEX ERROR {}'.format(video.url))
            continue
        videos = youtube.streams.filter(progressive=True).all()
        if not videos:
            results.append('No video found in {}. Are you OK?'.format(video.url))
            continue
        for _format in FORMATS_THAT_I_LIKE:
            for resolution in RESOLUTIONS_THAT_I_COULD_LIVE_WITH:
                if video.is_downloaded:
                    continue
                for video_youtube in videos:
                    if video_youtube.subtype == _format and video_youtube.resolution == resolution:
                        download_folder = os.path.join(DOWNLOADED_PATH, video.file_path)
                        if not os.path.exists(download_folder):
                            os.makedirs(download_folder)
                        print('')
                        video_youtube.download(download_folder)
                        results.append(
                            u'Downloaded "{}" with {} format and {} resolution. Congratulations! Now, get out!'.format(
                                video.song,
                                _format,
                                resolution
                            )
                        )
                        oh_sheet.update_acell('E{}'.format(index + 2), 'S')
                        oh_sheet.update_acell('G{}'.format(index + 2), '{}/{}'.format(_format, resolution))
                        video.is_downloaded = True
    progress_bar.finish()

    if not results:
        print('Looks like nothing to do right now. Great hopes for the next time!')

    for result in results:
        print(u'\t{}'.format(result))


if __name__ == '__main__':
    while True:
        LOOPS += 1
        if LOOPS == 1:
            print('HI!! How are you? Lets Start Download ALL THE WORLD!'.format(LOOPS))
        if LOOPS > 1:
            print('Im already running for {} times'.format(LOOPS))
        if LOOPS > 1 and LOOPS % 10 == 0:
            print('Can we have a break? pleeeeeazeee?!?!')
        main()
        progress_seconds = bar.Bar('Next run in ', width=100, fill='-', max=INTERVAL, suffix='%(remaining)d seconds')
        for segundo in reversed(range(1, INTERVAL + 1)):
            progress_seconds.next()
            sleep(1)
        progress_seconds.finish()
