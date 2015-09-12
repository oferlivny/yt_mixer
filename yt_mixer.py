#!/usr/local/bin/python

# depenedancies:
# pip install pafy moviepy pyyaml

import pafy
import moviepy.editor as mp
import os
import yaml
import hashlib

import moviepy.config as cf
cf.change_settings({"FFMPEG_BINARY": "/usr/local/bin/ffmpeg"})
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



class PafyCache:
    def __init__(self, tempdir):
        self.cache_path= tempdir + "/pafy_cache/"
        self.cache_index= self.cache_path + "/" + "index.yaml"
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


class YtMixer:
    def __init__(self,configfile = "yt_mixer_config.yaml" ):
        self.cfg = self.load_config('yt_mixer_config.yaml')
        self.video_list = self.cfg['videos']
        self.cfg = self.cfg['config']

    def load_config(self, path):
        print "loading " + path
        with open(path, 'r') as stream:
            cfg = yaml.load(stream,OrderedDictYAMLLoader)
            if cfg.get('tempdir') is None:
                cfg['tempdir']="/tmp/"
            if cfg.get('output') is None:
                cfg['output'] = "/tmp/yt_mixer_out.mp4"
            if cfg.get('concat') is None:
                cfg['concat'] = True
            return cfg

    def extract_all_videos(self):
        self.cache = PafyCache(self.cfg['tempdir'])
        for v in self.video_list:
            video = self.video_list[v]
            filename= self.cache.getVideo(video['url'],v)
            video['path']=filename

    def gen_clip(self):
        def get_subclip( fn , offset, duration ):
            clip = mp.VideoFileClip(fn)
            # print clip.size

            start = int(offset)
            end = int(offset)+int(duration)

            print "extracting frames {0} to {1}".format(start,end)
            newclip = clip.subclip(start,end).resize(width = self.cfg['video_params']['width'], height = self.cfg['video_params']['height'])
            return newclip

        clips = [ get_subclip(self.video_list[video]["path"], self.video_list[video]["offset"], self.video_list[video]["duration"])
              for video in self.video_list ]

        if (self.cfg['concat']):
            concat_clip = mp.concatenate_videoclips(clips,method="compose")
            concat_clip.set_fps = self.cfg['video_params']['fps']

            # concat_clip.set_audio(concat_audio_clip)
            concat_clip.write_videofile(output_path, fps=self.cfg['video_params']['fps'], codec=self.cfg['video_params']['vcodec'],audio_codec=self.cfg['video_params']['acodec'] , bitrate="2000k")
            concat_clip.audio.write_audiofile(output_path+".mp3")
        else:
            count = 0
            (a,b) = os.path.splitext(self.cfg['output'])
            for clip, video in zip(clips, self.video_list):
                output = "{}_{}{}".format(a,video,b)
                print ("Writing {}".format(output))
                # try:
                vparam=[]
                if self.cfg['video_params']['imovie_support']:
                    vparam=['-pix_fmt','yuv420p']
                clip.write_videofile(output,
                                     fps=self.cfg['video_params']['fps'],
                                     codec=self.cfg['video_params']['vcodec'],
                                     audio_codec=self.cfg['video_params']['acodec'] ,
                                     bitrate=self.cfg['video_params']['bitrate'],
                                     ffmpeg_params=vparam)
                if self.cfg['store_audio']:
                    clip.audio.write_audiofile(output+"."+self.cfg['audio_extension'])
                # except:
                #     print "Failed saving {}. Skipping...".format(video)



def main():

    mixer = YtMixer()
    mixer.extract_all_videos()
    mixer.gen_clip()

if __name__ == "__main__":
    main()
