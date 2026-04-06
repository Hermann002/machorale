from django.shortcuts import render

def home(request, slug=None):
    return render(request, 'landing/pages/home.html', {"slug": slug})