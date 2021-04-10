from django import forms
from .models import Submit, Language
from problem.models import Problem
# from django_ace import AceWidget


class SubmitAnswer(forms.ModelForm):
    class Meta:
        model = Submit
        fields = ['problem', 'language', 'submit_file']

class SubmitWithEditor(forms.Form):
    source = forms.CharField(widget=forms.Textarea) 
    problem = forms.ChoiceField(widget=forms.Select)
    language =  forms.ChoiceField(widget=forms.Select)

