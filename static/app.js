window.archtubes = [];
faz = new Vue({
    el: '#app',
    data: {
        videos: [],
        channels: [],
        page: 1,
        channel_page: 1,
        count: 50,
        vinclude: 'all',
        drives: 't',
        mode: 'videos',
        video_listing_method: 'plain',
        channel_listing_method: 'plain',
        filter_term: '',
        current_video: null,
        current_video_index: 0,
        lastScrollTop: null,
        controlsShown: true,
        channelSelectedId: null,
        playerButtonsShown: true,
        playerButtonsShownTimer: null,
        vchannelsort: 'oldest',
        vchannellistsort: 'updated',
        quality_filter: 'all',
    },
    watch: {
        quality_filter: function() {
            this.listVideos();
        },
        'vchannelsort': function() {
            this.retriggerChannelSearch();
        }
    },
    methods: {
        // common tools
        saveInstanceInfo: function(data) {
            history.pushState({}, document.title, window.location.href);
            window.archtubes.push($.extend(true, {}, data));
        },
        restoreInstanceInfo: function() {
            this.stopVideo();
            var d = window.archtubes.pop();
            for(var k in d) {
                if(d[k] instanceof Array) {
                    this[k].splice(0, this[k].length);
                    this[k].push.apply(this[k], d[k]);
                } else if(d[k] instanceof Object) {
                    $.extend(true, this[k], d[k]);
                } else {
                    this[k] = d[k];
                }
            }
        },
        switchToVideos: function() {
            if(this.mode == 'channels') {
                this.saveInstanceInfo(this._data);
                this.mode = 'videos';
                this.resetScrollTop();
                this.resetPagination();
                this.listVideos();
            }
        },
        startPlayerButtonsTimer: function() {
            clearTimeout(this.playerButtonsShownTimer);
            this.playerButtonsShown = true;
            var self = this;
            this.playerButtonsShownTimer = setTimeout(function() {
                self.playerButtonsShown = false;
            }, 4000);
        },
        toggleControls: function() {
            this.controlsShown = !this.controlsShown;
            this.$refs.video.controls = this.controlsShown;
        },
        resetScrollTop: function() {
            this.lastScrollTop = 0;
            document.documentElement.scrollTop = 0;
        },
        stopVideo: function() {
            if(this.current_video == null) {
                return;
            }
            this.$refs.video.pause();
            this.$refs.video.removeAttribute('src');
            this.$refs.video.load();
            this.current_video = null;
            this.current_video_index = 0;
//            if(this.lastScrollTop != null) {
//                var self = this;
//                this.$nextTick(function() {
//                    document.documentElement.scrollTop = self.lastScrollTop;
//                    self.lastScrollTop = null;
//                });
//            }
        },
        playVideoAndSavePos: function(index) {
            this.lastScrollTop = document.documentElement.scrollTop;
            this.playVideo(index);
        },
        playVideo: function(index) {
            var freshPlayer = this.current_video == null;
            var self = this;
            this.current_video = this.videos[index];
            this.$nextTick(function() {
                self.$refs.video.src = self.getVideoUrl(self.current_video);
            });
            this.current_video_index = index;
            var self = this;
            this.$nextTick(function() {
                if(self.$refs.video) {
                    self.$refs.video.controls = self.controlsShown;
                }
                self.startPlayerButtonsTimer();
                if(freshPlayer) {
                    var func = function() {
                        var plbtnshown = self.playerButtonsShown;
                        self.startPlayerButtonsTimer();
                        if(plbtnshown == false) {
                            window.event.preventDefault();
                            return;
                        }
                        if(self.controlsShown == false) {
                            if(self.$refs.video.paused) {
                                self.$refs.video.play();
                            } else {
                                self.$refs.video.pause();
                            }
                        }
                    };
                    self.$refs.video.addEventListener('click', func);
                    self.$refs.video.addEventListener('touchend', func);
                }
            });
        },
        nextVideo: function() {
            var nextIndex = this.current_video_index + 1;
            if(this.videos[nextIndex] != undefined) {
                this.playVideo(nextIndex)
            } else {
                this.loadNextVideos({
                    after: function() {
                        this.playVideo(0);
                    },
                    after_this: this
                });
            }
        },
        prevVideo: function() {
            var nextIndex = this.current_video_index - 1;
            if(this.videos[nextIndex] != undefined) {
                this.playVideo(nextIndex)
            } else {
                this.loadPrevVideos({
                    after: function() {
                        this.playVideo(this.videos.length - 1);
                    },
                    after_this: this
                });
            }
        },
        fullscreenVideo: function() {
            document.body.requestFullscreen();
        },
        rotateVideo: function() {
            window.screen.orientation.lock.call(window.screen.orientation, 'landscape').catch(function(v) {
                alert(v);
            });
        },
        getVideoUrl: function(video) {
            return 'play?video=' + encodeURIComponent(video.path);
        },
        getSubUrl: function(video) {
            var lastin = video.path.lastIndexOf('.');
            if(lastin == -1) {
                return 'subs?sub=' + encodeURIComponent(video.path + '.vtt');
            }
            var name_part = video.path.substr(0, lastin);
            var ext_part = video.path.substr(lastin + 1);
            return 'subs?sub=' + encodeURIComponent(name_part + '.en.vtt');
        },
        getAltThumbUrl: function(video) {
            t = video.alt_thumb.replace(/\\/g, '/').replace(/\(/g, '\\(').replace(/\)/g, '\\)');
            return '"/' + t + '"';
        },
        getThumbUrl: function(video) {
            if(video.info.snippet.thumbnails.maxres) {
                return video.info.snippet.thumbnails.maxres.url;
            }
            if(video.info.snippet.thumbnails.high) {
                return video.info.snippet.thumbnails.high.url;
            }
            if(video.info.snippet.thumbnails.default) {
                return video.info.snippet.thumbnails.default.url;
            }
            return '';
        },
        resetPagination: function() {
            this.page = 1;
        },
        getVideoListingUrl: function() {
            switch(this.video_listing_method) {
                case 'plain':
                    return 'list';
                case 'term_filter':
                    return 'list_by_term';
                case 'channel_filter':
                    return 'list_by_channel';
            }
        },
        getVideoListingData: function() {
            var data = {
                page: this.page,
                count: this.count,
                drives: this.drives,
                vinclude: this.vinclude,
                quality_filter: this.quality_filter,
            };
            switch(this.video_listing_method) {
                case 'term_filter':
                    data['term'] = this.filter_term;
                    break;
                case 'channel_filter':
                    data['channel_id'] = this.channelSelectedId;
                    data['vchannelsort'] = this.vchannelsort;
                    break;
            }
            return data;
        },
        triggerTermSearch: function() {
            this.saveInstanceInfo(this._data);
            switch(this.mode) {
                case 'videos':
                    this.video_listing_method = 'term_filter';
                    this.resetPagination();
                    this.resetScrollTop();
                    this.listVideos();
                    break;
                case 'channels':
                    this.channel_listing_method = 'term_filter';
                    this.resetPagination();
                    this.resetScrollTop();
                    this.listChannels();
                    break;
            }
        },
        listVideos: function(options) {
            options = options || {};
            var data = this.getVideoListingData();
            $.extend(data, options.data || {});
            var self = this;
            $.ajax({
                url: this.getVideoListingUrl(),
                data: data,
                success: function(data) {
                    self.videos.splice(0, self.videos.length);
                    self.videos.push.apply(self.videos, data.videos);
                    if(options.after) {
                        options.after.call(options.after_this || window);
                    }
                    self.mode = 'videos';
                }
            });
        },
        loadNextVideos: function(options) {
            options = options || {};
            if(options.skip === undefined) {
                this.page++;
            } else {
                this.page += options.skip;
            }
            this.stopVideo();
            this.resetScrollTop();
            this.listVideos({
                after: options.after,
                after_this: options.after_this
            });
        },
        loadPrevVideos: function(options) {
            if(this.page < 2) {
                return;
            }
            options = options || {};
            if(options.skip === undefined) {
                this.page--;
            } else {
                var newpage = this.page -= options.skip;
                if(newpage < 1) {
                    this.page = 1;
                } else {
                    this.page = newpage;
                }
            }
            this.stopVideo();
            this.resetScrollTop();
            this.listVideos({
                after: options.after,
                after_this: options.after_this
            });
        },
        openYoutubePage: function() {
            window.open('http://youtu.be/' + this.current_video.video_id)
        },
        // channel related stuff here
        searchCurrentChannel: function() {
            if(!this.current_video.info) {
                return;
            }
            this.saveInstanceInfo(this._data);
            this.video_listing_method = 'channel_filter';
            this.channelSelectedId = this.current_video.info.snippet.channelId;
            this.resetPagination();
            this.resetScrollTop();
            this.listVideos();
            this.stopVideo();
        },
        switchToChannels: function() {
            if(this.mode == 'videos') {
                this.saveInstanceInfo(this._data);
                this.mode = 'channels';
                this.resetScrollTop();
                this.resetChannelPagination();
                this.listChannels();
            }
        },
        retriggerChannelSearch: function() {
            if(this.mode != 'videos' || this.video_listing_method != 'channel_filter') {
                return;
            }
            this.saveInstanceInfo(this._data);
            this.resetPagination();
            this.resetScrollTop();
            this.listVideos();
        },
        triggerChannelSearch: function(index) {
            this.saveInstanceInfo(this._data);
            this.video_listing_method = 'channel_filter';
            this.channelSelectedId = this.channels[index].id;
            this.resetPagination();
            this.resetScrollTop();
            this.listVideos();
        },
        resetChannelPagination: function() {
            this.channel_page = 1;
        },
        getChannelListingUrl: function() {
            switch(this.channel_listing_method) {
                case 'plain':
                    return 'channels';
                case 'term_filter':
                    return 'channels_by_term';
            }
        },
        getChannelsListingData: function() {
            var data = {
                page: this.channel_page,
                count: this.count,
                drives: this.drives,
                sort: this.vchannellistsort,
            };
            switch(this.channel_listing_method) {
                case 'term_filter':
                    data['term'] = this.filter_term;
                    break;
            }
            return data;
        },
        listChannels: function(options) {
            options = options || {};
            var data = this.getChannelsListingData();
            $.extend(data, options.data || {});
            var self = this;
            $.ajax({
                url: this.getChannelListingUrl(),
                data: data,
                success: function(data) {
                    self.channels.splice(0, self.channels.length);
                    self.channels.push.apply(self.channels, data.channels);
                    if(options.after) {
                        options.after.call(options.after_this || window);
                    }
                    self.mode = 'channels';
                }
            });
        },
        loadNextChannels: function(options) {
            options = options || {};
            if(options.skip === undefined) {
                this.channel_page++;
            } else {
                this.channel_page += options.skip;
            }
            this.resetScrollTop();
            this.listChannels({
                after: options.after,
                after_this: options.after_this
            });
        },
        loadPrevChannels: function(options) {
            if(this.channel_page < 2) {
                return;
            }
            options = options || {};
            if(options.skip === undefined) {
                this.channel_page--;
            } else {
                var newpage = this.channel_page -= options.skip;
                if(newpage < 1) {
                    this.channel_page = 1;
                } else {
                    this.channel_page = newpage;
                }
            }
            this.resetScrollTop();
            this.listChannels({
                after: options.after,
                after_this: options.after_this
            });
        },
        openChannelPage(channel) {
            window.event.stopPropagation();
            window.open('https://youtube.com/channel/' + channel['id'] + '/videos');
        },
    },
    mounted: function() {
        var drives = archtube_drives;
        window.localStorage.setItem('drives', drives);
        this.drives = drives;
        this.listVideos();
        var self = this;
        window.addEventListener('popstate', function(ev) {
            ev.preventDefault();
            self.restoreInstanceInfo();
        });
    }
});