from django.shortcuts import render
from django.views.generic import TemplateView

class DashboardView(TemplateView):
    template_name = "pages/dashboard.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, context={"page_title": "Tableau de bord"})