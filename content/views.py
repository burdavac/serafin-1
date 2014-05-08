from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render
from filer.models import File, Image
from serafin.utils import JSONResponse
from system.models import Part, Page
from system.engine import Engine
import json


@login_required
def get_part(request):

    if request.is_ajax():
        return get_page(request)

    # admin preview support
    part_id = request.GET.get('part_id')
    if request.user.is_staff and part_id:
        request.user.data['current_part'] = part_id
        request.user.data['current_node'] = 0
        request.user.save()

    part_id = request.user.data['current_part']
    part = Part.objects.get(id=part_id)

    context = {
        'program': part.program,
        'api': reverse('content_api'),
    }

    return render(request, 'part.html', context)


@login_required
def get_page(request):

    context = {}

    if request.method == 'POST':
        post_data = json.loads(request.body)
        post_data = {item.get('key'): item.get('value') for item in post_data}
        context.update(post_data)

    next = request.GET.get('next', None)
    engine = Engine(request.user, context)
    page = engine.run(next)

    # admin preview support
    page_id = request.GET.get('page_id')
    if request.user.is_staff and page_id:
        page = Page.objects.get(id=page_id)
        page.update_html(request.user)
        page.dead_end = True

    response = {
        'title': page.title,
        'data': page.data,
        'dead_end': page.dead_end,
    }

    return JSONResponse(response)


@staff_member_required
def api_filer_file(request, content_type=None, file_id=None):

    if content_type == 'image':
        filer_file = get_object_or_404(Image, id=file_id)
    else:
        filer_file = get_object_or_404(File, id=file_id)

    response = {
        'id': filer_file.id,
        'url': filer_file.url,
        'thumbnail': filer_file.icons['48'],
        'description': filer_file.original_filename,
    }

    return JSONResponse(response)
