from django.views.generic.base import TemplateView


class PageAuthor(TemplateView):
    template_name = 'about/page_author.html'


class PageTech(TemplateView):
    template_name = 'about/page_tech.html'
