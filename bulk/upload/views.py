
# Create your views here.
from django.shortcuts import render, redirect
from django.http import JsonResponse
from .forms import UploadFileForm
from .tasks import process_uploaded_files
import logging
from django.shortcuts import render
from django.core.cache import cache
import oracledb
import tempfile
import os
import logging
import datetime
from django.db import connection
from .tasks import upload_transactions_to_db
from datetime import datetime
from django.http import HttpResponse
from .forms import BankDetailsForm
from .models import BankDetails
import pandas as pd
import json
from .models import BankMapping  # Ensure this model exists
import re
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
import pickle
  # Preprocess logs to attach relevant info messages to error logs
from collections import defaultdict
from datetime import datetime
from django.core.serializers.json import DjangoJSONEncoder




# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)



# Precompile regex patterns for performance
column_cleaning_regex = re.compile(r'\[.*?\]')  # Matches brackets and content within
artifact_regex = re.compile(r'x000D')          # Matches the 'x000D' artifact

def clean_column_name(column_name):
    """
    Cleans column names by removing unwanted characters, artifacts, 
    and formatting issues, including spaces.
    """
    # Remove content inside brackets along with the brackets
    cleaned_name = column_cleaning_regex.sub('', column_name)
    
    # Remove specific artifacts like 'x000D'
    cleaned_name = artifact_regex.sub('', cleaned_name)
    
    # Remove all remaining spaces, periods (.), and underscores (_)
    cleaned_name = ''.join(char for char in cleaned_name if char not in ['.', '_']).replace(' ', '')
    
    # Strip any leading or trailing whitespace
    return cleaned_name.strip()


##### ADDING NEW BANK MAPPING CODE####################################################


def add_bank_details(request):
    if request.method == 'POST':
        form = BankDetailsForm(request.POST)
        if form.is_valid():
            bank_details = form.save(commit=False)
            bank_details.bank_rule_mapping = None  # Initially null
            bank_details.save()
            return redirect('bank_details_list')  # Redirect to a list view or a success page
    else:
        form = BankDetailsForm()
    
    return render(request, 'add_bank_details.html', {'form': form})




def bank_details_list(request):
    bank_details = BankDetails.objects.all()
    bank_names = BankDetails.objects.values_list('bank_name', flat=True).distinct()
    bank_ids = BankDetails.objects.values_list('bank_id', flat=True).distinct()
    transaction_types = BankDetails.objects.values_list('transaction_type', flat=True).distinct()

    column_names = cache.get('column_names')
    total_columns = cache.get('column_total', 0)

    # Initialize selected values
    selected_bank_name = None
    selected_bank_id = None
    selected_transaction_type = None

    if request.method == 'POST':
        selected_bank_name = request.POST.get('bank_name', None)
        selected_bank_id = request.POST.get('bank_id', None)
        selected_transaction_type = request.POST.get('transaction_type', None)

        if 'uploaded_file' in request.FILES:
            uploaded_file = request.FILES['uploaded_file']
            try:
                file_extension = uploaded_file.name.split('.')[-1].lower()
                if file_extension == 'csv':
                    df = pd.read_csv(uploaded_file)
                elif file_extension in ['xls', 'xlsx', 'ods']:
                    df = pd.read_excel(uploaded_file, engine='openpyxl' if file_extension == 'xlsx' else None)
                else:
                    raise ValueError(f"Unsupported file format: {file_extension}")

                cleaned_columns = [clean_column_name(col) for col in df.columns]
                df.columns = cleaned_columns

                column_names = df.columns.tolist()
                total_columns = len(column_names)

                cache.set('column_names', column_names, timeout=120)
                cache.set('column_total', total_columns, timeout=120)
            except Exception as e:
                column_names = [f"Error reading file: {e}"]
                total_columns = 0

    return render(request, 'bank_details_list.html', {
        'bank_details': bank_details,
        'column_names': column_names,
        'total_columns': total_columns,
        'bank_names': bank_names,
        'bank_ids': bank_ids,
        'transaction_types': transaction_types,
        'selected_bank_name': selected_bank_name,
        'selected_bank_id': selected_bank_id,
        'selected_transaction_type': selected_transaction_type,
    })



@csrf_exempt
def save_mappings(request):
    if request.method == "POST":
        try:
            # Parse the incoming JSON data
            data = json.loads(request.body)

            # Extract bank_name, transaction_type, and mappings from request data
            bank_name = data.get('bank_name')
            transaction_type = data.get('transaction_type')
            bank_id = data.get('bank_id')
            mappings = data.get('mappings')
           


            # Build reversed headers mapping: file column → standardized column
            headers = {mapping['fileColumn']: mapping['mprColumn'] for mapping in mappings}

            # Modify the validation rules to use fileColumn as key
            validation_rules = {}
            for mapping in mappings:
                file_column = mapping['fileColumn']
                mpr_column = mapping['mprColumn']
                if 'validationRules' in mapping:
                    # Use the file column as the key
                    validation_rules[file_column] = mapping['validationRules']

            # Save or update the configuration in BankMapping
            BankMapping.objects.update_or_create(
                bank_name=bank_name,
                bank_id = bank_id,
                transaction_type=transaction_type,
                defaults={
                    'headers': headers,
                    'validation_rules': validation_rules  # Store the validation rules with file columns as the key
                }
            )

            return JsonResponse({"message": "Mappings saved successfully!"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request method"}, status=405)


####UPLOAD MPR ##################################


def upload_files(request):
    # Retrieve the unique bank names, IDs, and transaction types
    bank_names = BankMapping.objects.values_list('bank_name', flat=True).distinct()
    bank_id = list(BankMapping.objects.values_list('bank_id', flat=True).distinct())
    transaction_type = BankMapping.objects.values_list('transaction_type', flat=True).distinct()
    bank_details = list(BankDetails.objects.values('bank_name', 'bank_id', 'merchant_name'))

 


    # Initialize logs to pass to the template
    logs = []

    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES, bank_names=bank_names, transaction_types=transaction_type, bank_ids=bank_id)
        if form.is_valid():
            bank_name = form.cleaned_data['bank_name']
            bank_id = form.cleaned_data['bank_id']
            transaction_type = form.cleaned_data['transaction_type']
            merchant_name = form.cleaned_data['merchant_name']



            # Check if the combination of bank_name, bank_id, and merchant_name already exists
            if not BankDetails.objects.filter(bank_name=bank_name, bank_id=bank_id, merchant_name=merchant_name).exists():
                # Raise an error if the combination is invalid
                return JsonResponse({
                    'error': f"The combination of Bank Name: {bank_name}, Bank ID: {bank_id}, and Merchant Name: {merchant_name} is not valid. Please ensure it's correctly configured in the Bank Details model."
                }, status=400)



            # Fetch logs from cache
            cache_key = f"file_processing_log_{bank_name}_{transaction_type}"
            cached_logs = cache.get(cache_key, None)
            if cached_logs:
                try:
                    logs = pickle.loads(cached_logs)
                except Exception as e:
                    logger.error(f"Failed to deserialize logs for {cache_key}: {e}", exc_info=True)
            
            # Process file upload logic (same as your existing code)
            files = request.FILES.getlist('file')
            temp_file_paths = []
            file_formats = []
            for file in files:
                if file.size == 0:
                    logger.error(f"File {file.name} is empty.")
                    return JsonResponse({'message': f'File {file.name} is empty.'}, status=400)
                temp_dir = tempfile.gettempdir()
                original_file_name = file.name
                temp_file_path = os.path.join(temp_dir, original_file_name)
                with open(temp_file_path, 'wb') as temp_file:
                    for chunk in file.chunks():
                        temp_file.write(chunk)
                file_extension = original_file_name.lower().split('.')[-1]
                if file_extension in ['xlsx', 'xls', 'ods']:
                    file_formats.append('excel')
                else:
                    file_formats.append('csv')
                temp_file_paths.append(temp_file_path)
            process_uploaded_files.delay(temp_file_paths, bank_name, transaction_type, file_formats, merchant_name, bank_id)
            # Redirect to the dynamic logs page
            return redirect('show_logs', bank_name=bank_name, transaction_type=transaction_type)
    else:
        form = UploadFileForm(bank_names=bank_names, transaction_types=transaction_type, bank_ids=bank_id)

    return render(request, 'upload.html', {
        'form': form,
        'bank_names': bank_names,
        'bank_ids': bank_id,
        'transaction_types': transaction_type,
        'logs': logs,
        'bank_details': json.dumps(bank_details, cls=DjangoJSONEncoder),  # Pass valid combinations
    })

#####################################LOGS########################################################

def show_logs(request, bank_name, transaction_type):
    cache_key = f"file_processing_log_{bank_name}_{transaction_type}"
    cached_logs = cache.get(cache_key, None)

    logs = []
    if cached_logs:
        try:
            logs = json.loads(cached_logs)  # Deserialize using JSON
        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize logs for {cache_key}: {e}", exc_info=True)

    # Track the most recently processed file
    current_file = None

    for log in logs:
        # Convert timestamp to datetime object
        try:
            log['timestamp'] = datetime.fromisoformat(log['timestamp'])
        except ValueError:
            logger.error(f"Invalid timestamp format: {log['timestamp']}")
            log['timestamp'] = None  # Set to None if invalid

        # If it's an 'info' log, update the current file being processed
        if log['log_type'] == 'info' and 'Processing file:' in log['message']:
            current_file = log['message'].split('Processing file:')[-1].strip()

        # If it's an 'error' log, attach the current file (if available)
        if log['log_type'] == 'error':
            log['file_name'] = current_file if current_file else "N/A"
    
     # Provide the form if needed for the same page
    bank_names = BankMapping.objects.values_list('bank_name', flat=True).distinct()
    transaction_types = BankMapping.objects.values_list('transaction_type', flat=True).distinct()
    form = UploadFileForm(bank_names=bank_names, transaction_types=transaction_types)


    return render(request, 'upload.html', {
        'logs': logs,  # Pass logs to the template
        'bank_name': bank_name,
        'transaction_type': transaction_type,
        'form': form,  # No upload form on the logs page
    })


###############################################################

def transaction_results_view(request):
    # Retrieve the results from the cache
    results = cache.get('latest_transaction_results')
    if results is None:
        logger.error("No cached results found.")
        results = {
            "total_successful": 0,
            "total_failed": 0,
        }
    else:
        logger.debug(f"Retrieved results from cache: {results}")

    context = {
        'total_successful': results['total_successful'],
        'total_failed': results['total_failed'],
    }

    return render(request, 'transaction_results.html', context)





###DB UPLOAD########################


def nget_db_upload(request):
    template = "success.html"
    form_template = "ngetdb.html"

    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        bank = request.POST.get('Bank')
        txn_type = request.POST.get('txn_type')

        try:
            # Updated to use '%d-%b-%Y' format (abbreviated month)
            start_date_oracle = datetime.strptime(start_date, '%Y-%m-%d').strftime('%d-%b-%Y')
            end_date_oracle = datetime.strptime(end_date, '%Y-%m-%d').strftime('%d-%b-%Y')

            if txn_type in ['SALE', 'REFUND', 'SOFT', 'IRDS']:
                task = upload_transactions_to_db.delay(start_date_oracle, end_date_oracle, bank, txn_type)
                context = {'msg': f"Data upload task for {txn_type} has started. Please check back later."}
                return render(request, template, context)

        except ValueError as e:
            context = {'msg': f"Error parsing dates: {e}"}
            return render(request, template, context)

    return render(request, form_template)




#######################################  UPDATE  MPR ACTUAL CREDIT DEBIT DATE ########################################################

def  Mpractual_Credit_Date(request):
    return render(request, "mprcredit.html", {})




