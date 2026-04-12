from django.shortcuts import render

def simulation(request):
    return render(request, "handover/simulation.html")
