from django.shortcuts import render
from django.views.generic import TemplateView
from forms import CreateChoraleForm

class DashboardView(TemplateView):
    template_name = "pages/dashboard.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, context={"page_title": "Tableau de bord"})
    
class CreateChoraleView(TemplateView):
    template_name = "pages/create_chorale.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, context={"page_title": "Créer une chorale"})