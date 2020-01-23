from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('list', views.list_videos, name='list'),
    path('list_by_term', views.list_videos_by_term, name='list_term'),
    path('list_by_channel', views.list_videos_by_channel, name='list_channel'),
    path('channels', views.list_channels, name='channels'),
    path('channels_by_term', views.list_channels_by_term, name='channels_term'),
    path('play', views.play, name='play'),
    path('subs', views.subs, name='subs'),
]