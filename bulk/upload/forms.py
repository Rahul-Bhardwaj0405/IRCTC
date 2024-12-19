from django import forms
from .models import BankDetails

class BankDetailsForm(forms.ModelForm):
    MERCHANT_NAME_CHOICES = [
        ('', 'Select'),
        ('IRCTC WEB', 'IRCTC WEB'),
        ('IRCTC APP', 'IRCTC APP'),
        ('IRCTC AIR TICKET', 'IRCTC AIR TICKET'),
        ('IRCTC TOURISM', 'IRCTC TOURISM'),
        ('ALL', 'ALL'),
    ]

    # TRANSACTION_TYPE_CHOICES = [
    #     ('', 'Select'),
    #     ('SALE', 'SALE'),
    #     ('REFUND', 'REFUND'),
    #     ('NET SETTLED', 'NET SETTLED'),
    # ]

    merchant_name = forms.ChoiceField(
        choices=MERCHANT_NAME_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    # transaction_type = forms.ChoiceField(
    #     choices=TRANSACTION_TYPE_CHOICES,
    #     widget=forms.Select(attrs={'class': 'form-select'}),
    # )

    class Meta:
        model = BankDetails
        fields = ['bank_name', 'bank_id', 'mid', 'merchant_name']
        widgets = {
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_id': forms.TextInput(attrs={'class': 'form-control'}),
            'mid': forms.TextInput(attrs={'class': 'form-control'}),
        }






class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result
    



class UploadFileForm(forms.Form):
    bank_name = forms.ChoiceField(choices=[])
    merchant_name = forms.ChoiceField(choices=[
        ('', 'Select'),
        ('IRCTC WEB', 'IRCTC WEB'),
        ('IRCTC APP', 'IRCTC APP'),
        ('IRCTC AIR', 'IRCTC AIR'),
        ('IRCTC TOURISM', 'IRCTC TOURISM'),
    ])
    bank_id = forms.ChoiceField(choices=[])
    transaction_type = forms.ChoiceField(choices=[])
    file = MultipleFileField()

    def __init__(self, *args, **kwargs):
        # Get dynamic choices from kwargs and set them
        bank_names = kwargs.pop('bank_names', [])
        bank_ids = kwargs.pop('bank_ids', [])
        transaction_types = kwargs.pop('transaction_types', [])
        
        super().__init__(*args, **kwargs)
        
        # Set dynamic choices
        self.fields['bank_name'].choices = [(bank, bank) for bank in bank_names]
        self.fields['bank_id'].choices = [(bank_id, bank_id) for bank_id in bank_ids]
        self.fields['transaction_type'].choices = [(transaction, transaction) for transaction in transaction_types]

    def clean(self):
        cleaned_data = super().clean()
        bank_name = cleaned_data.get('bank_name')
        merchant_name = cleaned_data.get('merchant_name')
        bank_id = cleaned_data.get('bank_id')

        # Validate if the combination exists in BankDetails
        if not BankDetails.objects.filter(
                bank_name=bank_name, bank_id=bank_id, merchant_name=merchant_name).exists():
            raise forms.ValidationError(
                f"The combination of Bank Name: '{bank_name}', Bank ID: '{bank_id}', and Merchant Name: '{merchant_name}' does not exist."
            )

        return cleaned_data


# class MultipleFileInput(forms.ClearableFileInput):
#     allow_multiple_selected = True

# class MultipleFileField(forms.FileField):
#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault("widget", MultipleFileInput())
#         super().__init__(*args, **kwargs)

#     def clean(self, data, initial=None):
#         single_file_clean = super().clean
#         if isinstance(data, (list, tuple)):
#             result = [single_file_clean(d, initial) for d in data]
#         else:
#             result = single_file_clean(data, initial)
#         return result
    



# class UploadFileForm(forms.Form):
#     bank_name = forms.ChoiceField(choices=[])
#     merchant_name = forms.ChoiceField(choices=[
#         ('', 'Select'),
#         ('IRCTC WEB', 'IRCTC WEB'),
#         ('IRCTC APP', 'IRCTC APP'),
#         ('IRCTC AIR', 'IRCTC AIR'),
#         ('IRCTC TOURISM', 'IRCTC TOURISM'),
#     ])
#     bank_id = forms.ChoiceField(choices=[])
#     transaction_type = forms.ChoiceField(choices=[])
#     file = MultipleFileField()

#     def __init__(self, *args, **kwargs):
#         # Get dynamic choices from kwargs and set them
#         bank_names = kwargs.pop('bank_names', [])
#         bank_ids = kwargs.pop('bank_ids', [])
#         transaction_types = kwargs.pop('transaction_types', [])
        
#         super().__init__(*args, **kwargs)
        
#         # Set dynamic choices
#         self.fields['bank_name'].choices = [(bank, bank) for bank in bank_names]
#         self.fields['bank_id'].choices = [(bank_id, bank_id) for bank_id in bank_ids]
#         self.fields['transaction_type'].choices = [(transaction, transaction) for transaction in transaction_types]
