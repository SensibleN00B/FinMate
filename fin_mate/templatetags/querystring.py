from django import template

register = template.Library()


@register.simple_tag
def url_replace(request, **kwargs):
    query = request.GET.copy()
    for k, v in kwargs.items():
        query[k] = v
    return query.urlencode()
