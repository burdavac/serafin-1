from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^$', 'content.views.design_test', name='design_test'),
    url(r'page-test^$', 'content.views.page_test', name='page_test'),
)