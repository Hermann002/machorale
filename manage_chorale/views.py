from django.shortcuts import render
from django.views.generic import TemplateView
from .forms import CreateChoraleForm
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect
from formtools.wizard.views import SessionWizardView
from .forms import CreateChoraleForm, ConfChoraleForm
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os

class DashboardView(TemplateView):
    template_name = "pages/dashboard.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, context={"page_title": "Tableau de bord"})
    

FORMS = [
    ("create", CreateChoraleForm),
    ("conf", ConfChoraleForm),
]

TEMPLATES = {
    "create": "pages/create_chorale.html",
    "conf": "pages/conf_chorale.html",
}


    
class CreateChoraleView(SessionWizardView):
    form_list = FORMS
    template_name = "pages/create_chorale.html"
    file_storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, "temp"))

    def get_template_names(self):
        return TEMPLATES[self.steps.current]

    def get(self, request, *args, **kwargs):
        try:
            if request.user.is_verify is False:
                print(request.user.is_verify)
                messages.error(request, "You need to verify your email before creating a chorale.")
                return HttpResponseRedirect(reverse('dashboard'))
        except AttributeError as e:
            print(f"AttributeError: {e}")
            messages.error(request, "You need to be logged in to create a chorale.")
            return HttpResponseRedirect(reverse('dashboard'))
        return super().get(request, *args, **kwargs)

    def done(self, form_list, **kwargs):
        form_data = self.get_all_cleaned_data()
        print("ici")
        return render(self.request, "pages/done.html", context={"form_data": form_data})
    
    # def post(self, request, *args, **kwargs):
    #     form = CreateChoraleForm(request.POST)
        
    #     if form.is_valid():
    #         chorale = form.save(commit=False)
    #         chorale.admin = request.user
    #         chorale.save()
    #         return render(request, "pages/dashboard.html", context={"page_title": "Tableau de bord", "success_message": "Chorale créée avec succès."})
    #     return render(request, self.template_name, context={"page_title": "Créer une chorale", "form": form})
    
