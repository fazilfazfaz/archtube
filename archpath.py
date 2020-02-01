"""
Archpath
Supplies hacky wrappers of sorts to a list of function from python's os.path module
To make sure archTUBE works on windows and *nix systems
Additionally 2 methods were created to keep changes in archtube minimal
"""

import os
import platform

class archpath:

    # wrapper for os.path.join()
    # @param string, string
    def join(path, file):
        return os.path.join(path, file)


    # wrapper for os.path.isdir()
    # @param string
    # @return boolean
    def isdir(path):
        return os.path.isdir(path)


    # wrapper for os.path.ismount()
    # @param string
    # @return boolean
    def ismount(path):
        if platform.uname()[0] == 'Windows':
            return os.path.ismount(path)
        # The idea to only allow mounted drives doesn't fit *nix
        # let's just make sure it's a folder and be done with it
        return os.path.isdir(path)


    # wrapper for os.path.isfile()
    # @param string
    # @return boolean
    def isfile(path):
        return os.path.isfile(path)


    # wrapper for os.path.basename()
    # @param string
    # @return ...
    def basename(path):
        return os.path.basename(path)


    # wrapper for os.path.getsize()
    # @param string
    # @return ...
    def getsize(path):
        # should be fine, right?
        return os.path.getsize(path)


    # use string.split() but make sure you don't mess up paths
    # i.e. make it work with win and *nix paths
    # @param string, string
    # @return ...
    def split(path):
        if platform.uname()[0] == 'Windows':
            return path.split('\\')
        # remove escessive slashes to avoid empty list elements
        return path.lstrip('/').rstrip('/').split('/')


    # Make sure adding :\\ to a path makes sense
    def format_mount_point(path):
        # for windows:
        if platform.uname()[0] == 'Windows':
            return  path + ':\\'
        # for *nix:
        return path


    # Replacing windll.kernel32.GetLogicalDrives()
    def get_drives():
        # for windows:
        if platform.uname()[0] == 'Windows':
            return windll.kernel32.GetLogicalDrives()
        # for *nix:
        media = []
        for m in os.listdir('/media'):
            if os.path.isdir(m):
                media.append(m)
        return media
