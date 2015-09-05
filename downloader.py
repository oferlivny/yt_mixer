#!/usr/local/bin/python

# depenedancies:
# pip install pafy moviepy pyyaml

import pafy
import moviepy.editor as mp
import os
import yaml
import hashlib

try:
    # included in standard lib from Python 2.7
    from collections import OrderedDict
except ImportError:
    # try importing the backported drop-in replacement
    # it's available on PyPI
    from ordereddict import OrderedDict

class OrderedDictYAMLLoader(yaml.Loader):
    """
    A YAML loader that loads mappings into ordered dictionaries.
    """

    def __init__(self, *args, **kwargs):
        yaml.Loader.__init__(self, *args, **kwargs)

        self.add_constructor(u'tag:yaml.org,2002:map', type(self).construct_yaml_map)
        self.add_constructor(u'tag:yaml.org,2002:omap', type(self).construct_yaml_map)

    def construct_yaml_map(self, node):
        data = OrderedDict()
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_mapping(self, node, deep=False):
        if isinstance(node, yaml.MappingNode):
            self.flatten_mapping(node)
        else:
            raise yaml.constructor.ConstructorError(None, None,
                'expected a mapping node, but found %s' % node.id, node.start_mark)

        mapping = OrderedDict()
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError, exc:
                raise yaml.constructor.ConstructorError('while constructing a mapping',
                    node.start_mark, 'found unacceptable key (%s)' % exc, key_node.start_mark)
            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
        return mapping


def omap_constructor(loader, node):
    return loader.construct_pairs(node)

yaml.add_constructor(u'!omap', omap_constructor)

class PafyCache:
    def __init__(self):
        self.cache_path="/tmp/pafy_cache/"
        self.cache_index=self.cache_path + "/" + "index.yaml"
        try:
            os.mkdir(self.cache_path)
        except:
            print "cannot mkdir "+self.cache_path
            #do nothing

        if (not os.path.isfile(self.cache_index)):
            print "Not index file. Using empty dictionary"
            self.index = {'emptyurl':'emptyurl'}
        else:
            with open(self.cache_index, 'r') as stream:
                self.index = yaml.load(stream)


    def saveIndex(self):
        with open(self.cache_index, 'w') as outfile:
            outfile.write( yaml.dump(self.index, default_flow_style=True) )

    def loadVideo(self, url):
        video = pafy.new(url)
        best = video.getbest()
        key=hashlib.sha1(url).hexdigest()
        fn="{base_path}/{key}.{ext}".format(base_path=self.cache_path,key=key,ext=best.extension)
        res = best.download(fn)
        return res

    def getVideo(self,url, tag = None):
        entry = self.index.get(url)
        if (entry is not None):
            if (os.path.isfile(self.index[url])):
                print "Found cached: {0}".format(tag)
                return self.index[url]
            else:
                print "Cache entry found for {0}, but file does not exists."
        print "downloading {0}".format(tag)
        filename=self.loadVideo(url)
        self.index[url]=filename
        self.saveIndex()
        return filename

def extract_all_videos(video_list):
    cache = PafyCache()
    for v in video_list:
        video = video_list[v]
        filename=cache.getVideo(video['url'],v)
        video['path']=filename


def gen_clip(output_path):
    def get_subclip( fn , offset, duration ):
        clip = mp.VideoFileClip(fn)
        # print clip.size

        start = int(offset)
        end = int(offset)+int(duration)

        print "extracting from {0} to {1}".format(start,end)
        newclip = clip.subclip(start,end).resize(width = 640, height = 480)

        # newaudio = clip.audio.subclip(start,end)
        # print "newaudio duration: {0}".format(newaudio.duration)
        #newclip.write_videofile("/tmp/before.mp4")
        # newclip.set_audio(newaudio)
        # print "audio duration: {0}".format(newclip.audio.duration)
        #newclip.write_videofile("/tmp/after.mp4")
        return newclip

    clips = [ get_subclip(video_list[video]["path"], video_list[video]["offset"], video_list[video]["duration"])
          for video in video_list ]

    # audioclips = [video.audio for video in clips]
    # concat_audio_clip = mp.concatenate_audioclips(audioclips)
    concat_clip = mp.concatenate_videoclips(clips,method="compose")
    concat_clip.set_fps = 30
    # concat_clip.set_audio(concat_audio_clip)
    concat_clip.write_videofile(output_path, fps=30)

def load_video_list(path):
    print "loading " + path
    with open(path, 'r') as stream:
        return yaml.load(stream,OrderedDictYAMLLoader)

video_list = load_video_list('videolist.yaml')

temppath="/tmp/"
outpath="/Users/ofer/tmp//"
outfile="ofer.mp4"

extract_all_videos(video_list)
# video_list[0]["path"]="/tmp/0.webm"

output_video = "{tmppath}/{outfile}".format(tmppath=outpath,outfile=outfile)

gen_clip(output_video)
# clips = []
# clips[clipcount] = mp.TextClip("Test", fontsize=270, color='green')
# clipcount = clipcount + 1

