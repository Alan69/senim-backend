from django import forms
from test_logic.models import Test

class ImportQuestionsForm(forms.Form):
    json_file = forms.FileField(label='Select JSON file')
    # Ensure that you're selecting Test by its ID (which is typically UUID)
    test = forms.ModelChoiceField(queryset=Test.objects.all(), label='Select Test', to_field_name='id')
