from django import forms
from .models import LogFile

class LogFileUploadForm(forms.ModelForm):
    """Form for uploading log files"""
    class Meta:
        model = LogFile
        fields = ['file']
        
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file extension
            ext = file.name.split('.')[-1].lower()
            if ext != 'txt':
                raise forms.ValidationError("Only .txt files are allowed.")
            
            # Check file size (10MB limit)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 10MB.")
                
        return file


class LogFilterForm(forms.Form):
    """Form for filtering log entries"""
    ip_address = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    method = forms.ChoiceField(
        required=False, 
        choices=[('', 'All'), ('GET', 'GET'), ('POST', 'POST'), ('PUT', 'PUT'), ('DELETE', 'DELETE')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status_code = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    path = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    start_date = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    query_param = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parameter name'})
    )
    query_value = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parameter value'})
    )