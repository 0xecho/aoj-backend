from django import forms
from competitive.models import Submit

class SubmitAnswer(forms.ModelForm):

    class Meta:
        model = Submit
        fields = ['problem', 'language', 'submit_file']


class SubmitSpecificProblem(forms.ModelForm):
    specific_problem = forms.CharField(
        label="Problem",
        widget=forms.TextInput(attrs={'readonly': True}),
    )
    class Meta:
        model = Submit
        fields = [ 'specific_problem', 'language', 'submit_file']


class SubmitSpecificProblemWithEditor(forms.Form):
    
    source = forms.CharField(widget=forms.Textarea) 
    specific_problem = forms.CharField(
        label="Problem",
        widget=forms.TextInput(attrs={'readonly': True}),
    )
    language =  forms.ChoiceField(widget=forms.Select)


class SubmitWithEditor(forms.Form):
    source = forms.CharField(widget=forms.Textarea) 
    problem = forms.ChoiceField(widget=forms.Select)
    language =  forms.ChoiceField(widget=forms.Select)
