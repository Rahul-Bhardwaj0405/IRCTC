import pandas as pd
import logging
from celery import shared_task
from .models import Transaction
from io import BytesIO
import csv
import re
from django.core.cache import cache
import os
from .db_operations import get_transaction_data_in_chunks
from .models import Rail_Ticket_Sale, Rail_Ticket_Refund, BankMapping
from datetime import datetime
from django.utils.dateparse import parse_datetime
from django.utils import timezone
import json
from django.db import transaction, connection
from django.utils.timezone import now



# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format=(
        '%(asctime)s - %(levelname)s - %(name)s - %(module)s - '
        '%(funcName)s - line:%(lineno)d - %(process)d - '
        '%(threadName)s - %(message)s'
    ),
    handlers=(
        logging.StreamHandler(),
    )
)

logger = logging.getLogger(__name__)

# BANK_CODE_MAPPING = {
#     'HDFC': 101,
#     'ICICI': 115,
#     'KARUR VYSYA': 40,
# }

# # BANK_MAPPINGS = {
# #     'karur_vysya': {
# #         'booking': {
# #             'columns': ['TXN DATE', 'IRCTC ORDER NO.', 'BANK BOOKING REF.NO.', 'BOOKING AMOUNT', 'CREDITED ON'],
# #             'column_mapping': {
# #                 'IRCTCORDERNO': 'Order_Id',
# #                 'BANKBOOKINGREFNO': 'Bank_Ref_id',
# #                 'BOOKINGAMOUNT': 'Payable_Merchant',
# #                 'TXNDATE': 'Transaction_Date',
# #                 'CREDITEDON': 'Settlement_Date'
# #             }
# #         },
# #         'refund': {
# #             'columns': ['REFUND DATE', 'IRCTC ORDER NO.', 'BANK BOOKING REF.NO.', 'BANK REFUND REF.NO.', 'REFUND AMOUNT', 'DEBITED ON'],
# #             'column_mapping': {
# #                 'IRCTCORDERNO': 'Order_Id',
# #                 'REFUNDAMOUNT': 'Payable_Merchant',
# #                 'DEBITEDON': 'Settlement_Date',
# #                 'REFUNDDATE': 'Transaction_Date',
# #                 'BANKBOOKINGREFNO': 'Bank_Ref_id',
# #                 'BANKREFUNDREFNO': 'Refund_Order_Id'
# #             }
# #         }
# #     },
# #     'icici': {
# #         'NET SETTLED': {
# #             'columns': ['POST DATE', 'FT NO.', 'SESSION ID [ASPD]', 'ARN NO', 'MID', 'TRANSACTION DATE',  'NET AMT', 'CARD NUMBER', 'CARD TYPE', 'TID'],
# #             'column_mapping': {
# #                 'TRANSACTIONDATE': 'Transaction_Date',
# #                 'SESSIONID': 'Order_Id',
# #                 'FTNO': 'Transaction_Id',
# #                 'ARNNO': 'Arn_No',
# #                 'MID': 'MID',
# #                 'POSTDATE': 'Settlement_Date',
# #                 'NETAMT': 'Payable_Merchant',
# #                 'CARDNUMBER': 'Card_No',
# #                 'CARDTYPE': 'Card_type',
# #                 'TID': 'Tid'
# #             }
# #         }
# #     },
# # }

# # # # Precompile regex pattern for performance
# column_cleaning_regex = re.compile(r'\[.*?\]')

# def clean_column_name(column_name):
#     logger.debug(f"Cleaning column name: '{column_name}'")
#     cleaned_name = column_cleaning_regex.sub('', column_name)
#     cleaned_name = ''.join(part for part in cleaned_name.split() if part)
#     cleaned_name = ''.join(char for char in cleaned_name if char not in ['.', '_']).strip()
#     logger.debug(f"Cleaned column name: '{cleaned_name}'")
#     return cleaned_name




# def get_column_mapping_from_bank(bank_name, transaction_type):
#     try:
#         bank_mapping = BankMapping.objects.get(bank_name=bank_name)
#         headers = bank_mapping.get_headers()
#         logger.debug(f"Headers: '{headers}'")
        
#         if transaction_type in headers:
#             return headers[transaction_type]
#         else:
#             logger.error(f"No mapping found for transaction type {transaction_type} for bank {bank_name}.")
#             return None
#     except BankMapping.DoesNotExist:
#         logger.error(f"Bank mapping not found for bank {bank_name}.")
#         return None




# def convert_payable_to_float(df, column_name):
#     logger.debug(f"Converting column '{column_name}' to float.")
#     df[column_name] = pd.to_numeric(df[column_name].str.replace(',', ''), errors='coerce')
#     return df

# def convert_column_to_datetime(df, column_name):
#     logger.debug(f"Converting column '{column_name}' to datetime.")
#     df[column_name] = pd.to_datetime(df[column_name], errors='coerce')
    
#     # Log details of rows where datetime parsing resulted in NaT
#     unsuccessful_dates = df[df[column_name].isna()]
#     if not unsuccessful_dates.empty:
#         logger.warning(f"Could not parse dates in column '{column_name}'; rows affected: {unsuccessful_dates.index.tolist()}")
#         df[column_name].fillna(value=None, inplace=True)  # or specify default date here
#     return df

# def handle_nat_in_datetime_fields(transaction_data):
#     # List all the datetime fields expected in transaction_data
#     datetime_fields = ['Transaction_Date', 'Settlement_Date', 'Refund_Request_Date', 'Credit_Debit_Date', 'File_upload_Date']
    
#     for field in datetime_fields:
#         if transaction_data[field] is pd.NaT:
#             # Log the NaT issue with specific data point reference
#             logger.warning(f"Encountered NaT in {field}, setting to None or default for transaction ID: {transaction_data.get('Transaction_Id', 'Unknown')}")
#             # Assign None or a specific default date as necessary
#             transaction_data[field] = None

# @shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 5, 'countdown': 60})
# def process_uploaded_files(self, file_paths, bank_name, transaction_type, file_formats, merchant_name):
#     logger.info(f"Starting process_uploaded_files with bank_name: {bank_name}, transaction_type: {transaction_type}, file_formats: {file_formats}, merchant_name: {merchant_name}")
    
#     try:
#         total_files = len(file_paths)
#         logger.info(f"Total number of files to process: {total_files}")

#         for file_index, file_path in enumerate(file_paths):
#             file_name = os.path.basename(file_path)
#             file_extension = os.path.splitext(file_name)[-1].lower()  # Get file extension
            
#             logger.info(f"Processing file: {file_name} of type {transaction_type}")
#             df_chunks = []

#             try:
#                 # Determine the file format
#                 file_format = file_formats[file_index]
#                 if file_format == 'excel':
#                     # Ensure file extension is valid
#                     if file_extension in ('.xlsx', '.xls', '.ods'):
#                         # Proceed with processing the Excel file
#                         if file_extension == '.xlsx':
#                             df = pd.read_excel(file_path, dtype=str, engine='openpyxl')
#                         elif file_extension == '.xls':
#                             df = pd.read_excel(file_path, dtype=str, engine='xlrd')
#                         elif file_extension == '.ods':
#                             df = pd.read_excel(file_path, dtype=str, engine='odf')
#                         df_chunks = [df]  # For consistency in chunked processing
#                     else:
#                         logger.error(f"Unsupported Excel format for file: {file_name}, extension: {file_extension}")
#                         continue

#                 elif file_format == 'csv':
#                     df_chunks = pd.read_csv(file_path, dtype=str, quotechar='"', quoting=csv.QUOTE_MINIMAL, chunksize=50000)
#                     logger.info(f"Successfully read CSV file {file_name} in chunks.")
#                 else:
#                     logger.error(f"Unsupported file format: {file_format} for file: {file_name}")
#                     continue

#                 # Process each chunk
#                 for chunk_index, df_chunk in enumerate(df_chunks):
#                     process_dataframe_chunk(df_chunk, bank_name, transaction_type, merchant_name)

#             except Exception as e:
#                 logger.error(f"Error processing chunk from file: {file_name}. Exception: {e}", exc_info=True)
#                 continue
#             finally:
#                 if os.path.exists(file_path):
#                     os.remove(file_path)  # Ensure file is deleted after processing
#                     logger.info(f"Deleted temporary file: {file_path}")
#                 else:
#                     logger.warning(f"File not found for deletion: {file_path}")
#                 # os.remove(file_path)  # Ensure file is deleted after processing
#                 # logger.info(f"Deleted temporary file: {file_path}")

#             logger.info(f"File processing completed for {file_name}")

#         logger.info("All files have been processed.")

#     except Exception as e:
#         logger.error(f"Error in processing files. Exception: {e}", exc_info=True)
#         raise







# def process_dataframe_chunk(df_chunk, bank_name, transaction_type, merchant_name):
#     logger.info(f"Processing dataframe chunk for bank: {bank_name}, transaction type: {transaction_type}, merchant_name: {merchant_name}")

#     # Clean column names (but do not rename the columns)
#     cleaned_columns = [clean_column_name(col) for col in df_chunk.columns]
#     df_chunk.columns = cleaned_columns  # This still cleans but does not rename as per mapping

#     # Get column mapping from the BankMapping model
#     column_mapping = get_column_mapping_from_bank(bank_name, transaction_type)
#     if not column_mapping:
#         return

#     expected_columns = [clean_column_name(col) for col in column_mapping.keys()]

#     if all(col in df_chunk.columns for col in expected_columns):
#         # Do not rename columns, but process data based on expected column names
#         # Instead of renaming, you can now use the cleaned column names and process the data accordingly
#         if 'Transaction_Date' in df_chunk.columns:
#             df_chunk = convert_column_to_datetime(df_chunk, 'Transaction_Date')
#         if 'Settlement_Date' in df_chunk.columns:
#             df_chunk = convert_column_to_datetime(df_chunk, 'Settlement_Date')
#         if 'Payable_Merchant' in df_chunk.columns:
#             df_chunk = convert_payable_to_float(df_chunk, 'Payable_Merchant')
            
#             if bank_name == 'ICICI':
#                 df_chunk['Payable_Merchant'] = df_chunk['Payable_Merchant'].fillna(0)  # Assuming 0 is a neutral value for your logic
#                 df_chunk['CREDIT_DEBIT_AMOUNT'] = df_chunk['Payable_Merchant'].apply(
#                     lambda x: 'CREDIT' if x > 0 else 'DEBIT' if x < 0 else None
#                 )

#         process_transactions(df_chunk, bank_name, transaction_type, merchant_name)
#     else:
#         missing_cols = set(expected_columns) - set(df_chunk.columns)
#         logger.error(f"Missing expected columns: {missing_cols} for bank: {bank_name}, type: {transaction_type}")



# def process_dataframe_chunk(df_chunk, bank_name, transaction_type, merchant_name):
#     logger.info(f"Processing dataframe chunk for bank: {bank_name}, transaction type: {transaction_type}, merchant_name: {merchant_name}")
#     cleaned_columns = [clean_column_name(col) for col in df_chunk.columns]
#     df_chunk.columns = cleaned_columns
#     # logger.debug(f"Cleaned DataFrame columns: {df_chunk.columns.tolist()}")

#     bank_mapping = BANK_MAPPINGS.get(bank_name, {})

#     if transaction_type in bank_mapping:
#         columns_mapping = bank_mapping[transaction_type]
#     elif 'NET SETTLED' in bank_mapping:
#         columns_mapping = bank_mapping['NET SETTLED']
#     else:
#         logger.error(f"No valid mapping found for bank: {bank_name} and transaction type: {transaction_type}")
#         return

#     column_mapping = columns_mapping.get('column_mapping', {})
#     expected_columns = [clean_column_name(col) for col in columns_mapping.get('columns', [])]

#     if all(col in df_chunk.columns for col in expected_columns):
#         df_chunk.rename(columns=column_mapping, inplace=True)
#         # logger.debug(f"Renamed columns: {df_chunk.columns.tolist()}")

#         if 'Transaction_Date' in df_chunk.columns:
#             df_chunk = convert_column_to_datetime(df_chunk, 'Transaction_Date')
#         if 'Settlement_Date' in df_chunk.columns:
#             df_chunk = convert_column_to_datetime(df_chunk, 'Settlement_Date')
#         if 'Payable_Merchant' in df_chunk.columns:
#             df_chunk = convert_payable_to_float(df_chunk, 'Payable_Merchant')
            
#             if bank_name == 'ICICI':
#                 df_chunk['Payable_Merchant'] = df_chunk['Payable_Merchant'].fillna(0)  # Assuming 0 is a neutral value for your logic
#                 df_chunk['CREDIT_DEBIT_AMOUNT'] = df_chunk['Payable_Merchant'].apply(
#                     lambda x: 'CREDIT' if x > 0 else 'DEBIT' if x < 0 else None
#                 )
#                 # logger.debug(f"Populated CREDIT/DEBIT AMOUNT column: {df_chunk[['Payable_Merchant', 'CREDIT_DEBIT_AMOUNT']]}")

#         process_transactions(df_chunk, bank_name, transaction_type, merchant_name)
#     else:
#         missing_cols = set(expected_columns) - set(df_chunk.columns)
#         logger.error(f"Missing expected columns: {missing_cols} for bank: {bank_name}, type: {transaction_type}")

# def process_transactions(df_chunk, bank_name, transaction_type, merchant_name):
#     logger.info(f"Started processing transactions for bank: {bank_name}, type: {transaction_type}, merchant_name: {merchant_name}")
#     bulk_data_transactions = []
#     seen_orders = set()
#     bank_id = BANK_CODE_MAPPING.get(bank_name, None)

#     if bank_id is None:
#         logger.error(f"No bank ID found for bank: {bank_name}")
#         return
    
#     banks_with_mid_override = ['HDFC', 'ICICI', 'INDUS']

#     success_count = 0
#     fail_count = 0

#     for index, row in df_chunk.iterrows():
        
#         if transaction_type not in ['SALE', 'REFUND', 'NET SETTLED']:
#             logger.error(f"Unexpected transaction type: {transaction_type}. Skipping.")
#             fail_count += 1
#             continue

#         transaction_data = {
#             'Transaction_type': transaction_type,
#             'Merchant_Name': merchant_name,
#             'MID': row.get('MID') if bank_name in banks_with_mid_override else bank_id,
#             'Transaction_Id': row.get('Transaction_Id'),
#             'Order_Id': row.get('Order_Id'),
#             'Transaction_Date': row.get('Transaction_Date'),
#             'Settlement_Date': row.get('Settlement_Date'),
#             'Refund_Request_Date': convert_column_to_datetime(df_chunk, 'Refund_Request_Date') if 'Refund_Request_Date' in df_chunk else None,
#             'Gross_Amount': convert_payable_to_float(df_chunk, 'Gross_Amount') if 'Gross_Amount' in df_chunk else None,
#             'Aggregator_Com': convert_payable_to_float(df_chunk, 'Aggregator_Com') if 'Aggregator_Com' in df_chunk else None,
#             'Acquirer_Comm': convert_payable_to_float(df_chunk, 'Acquirer_Comm') if 'Acquirer_Comm' in df_chunk else None,
#             'Payable_Merchant': row.get('Payable_Merchant', 0),
#             'Payout_from_Nodal': convert_payable_to_float(df_chunk, 'Payout_from_Nodal') if 'Payout_from_Nodal' in df_chunk else None,
#             'BankName_Receive_Funds': row.get('BankName_Receive_Funds'),
#             'Nodal_Account_No': row.get('Nodal_Account_No'),
#             'Aggregator_Name': row.get('Aggregator_Name'),
#             'Acquirer_Name': row.get('Acquirer_Name'),
#             'Refund_Flag': row.get('Refund_Flag'),
#             'Payments_Type': row.get('Payments_Type'),
#             'MOP_Type': row.get('MOP_Type'),
#             'Credit_Debit_Date': convert_column_to_datetime(df_chunk, 'Credit_Debit_Date') if 'Credit_Debit_Date' in df_chunk else None,
#             'Bank_Name': bank_name,
#             'Refund_Order_Id': row.get('Refund_Order_Id'),
#             'Acq_Id': row.get('Acq_Id'),
#             'Approve_code': row.get('Approve_code'),
#             'Arn_No': row.get('Arn_No'),
#             'Card_No': row.get('Card_No'),
#             'Tid': row.get('Tid'),
#             'Remarks': row.get('Remarks'),
#             'Bank_Ref_id': row.get('Bank_Ref_id'),
#             'File_upload_Date': timezone.now(),
#             'User_name': row.get('User_name'),
#             'Recon_Status': row.get('Recon_Status'),
#             'Mpr_Summary_Trans': row.get('Mpr_Summary_Trans'),
#             'Merchant_code': row.get('Merchant_code'),
#             'Rec_Fmt': row.get('Rec_Fmt'),
#             'Card_type': row.get('Card_type'),
#             'Intl_Amount': convert_payable_to_float(df_chunk, 'Intl_Amount') if 'Intl_Amount' in df_chunk else None,
#             'Domestic_Amount': convert_payable_to_float(df_chunk, 'Domestic_Amount') if 'Domestic_Amount' in df_chunk else None,
#             'UDF1': None,
#             'UDF2': None,
#             'UDF3': None,
#             'UDF4': None,
#             'UDF5': None,
#             'UDF6': None,
#             'GST_Number': row.get('GST_Number'),
#             'Credit_Debit_Amount': row.get('CREDIT_DEBIT_AMOUNT'),
#         }

#         handle_nat_in_datetime_fields(transaction_data)


#         bulk_data_transactions.append(transaction_data)
#         success_count += 1


#     try:
#         with transaction.atomic():
#             Transaction.bulk_create_transactions(bulk_data_transactions)
#             logger.info(f"Processed {len(bulk_data_transactions)} transactions successfully.")
#         # except ValueError as ve:
#         #     logger.error(f"ValueError during bulk creation, possibly due to NaT issues: {ve}")
#     except Exception as e:
#         logger.error(f"Transaction failed: {e}", exc_info=True)
#             # logger.error(f"Transaction failed: {e}. Problematic Data: {bulk_data_transactions}", exc_info=True)
#         fail_count += len(bulk_data_transactions)

#     logger.debug(f"Batch processing complete. Successful: {success_count}, Failed: {fail_count}")


    # # Cache the results for later retrieval
    # results = {
    #     "total_successful": success_count,
    #     "total_failed": fail_count,
    # }
    # cache.set('latest_transaction_results', results, timeout=3600) 

    # return results



# Cache timeout in seconds
CACHE_TIMEOUT = 600

############LOG ERRORS OR SUCCESS PAGE #########################

def save_log_to_cache(bank_name, transaction_type, log_type, message):
    cache_key = f"file_processing_log_{bank_name}_{transaction_type}"
    log_entry = {
        'log_type': log_type,
        'message': message,
        'timestamp': timezone.now().isoformat()
    }

    logger.debug(f"Saving log to cache with key: {cache_key}, Log entry: {log_entry}")

    # Fetch existing logs from cache, if any
    cached_logs = cache.get(cache_key)
    if cached_logs:
        try:
            logs = json.loads(cached_logs)  # Deserialize cached logs
            logger.debug(f"Existing logs: {logs}")
        except json.JSONDecodeError as e:
            logs = []  # Initialize as an empty list if deserialization fails
            logger.error(f"Failed to deserialize logs for {cache_key}: {e}", exc_info=True)
    else:
        logs = []  # If no logs in cache, start with an empty list

    logs.append(log_entry)  # Add new log entry
    logger.debug(f"Logs to be saved: {logs}")

    # Serialize logs and save back to cache
    try:
        serialized_logs = json.dumps(logs)
        cache.set(cache_key, serialized_logs, timeout=CACHE_TIMEOUT)  # Ensure CACHE_TIMEOUT is defined
        logger.info(f"Logs saved for {cache_key}: {logs}")
    except Exception as e:
        logger.error(f"Failed to serialize and save logs for {cache_key}: {e}", exc_info=True)
        print(f"Error saving to cache: {e}")




# #################################################################################

def fetch_mapping_and_rules(bank_name, transaction_type):
    cache_key = f"mapping_rules_{bank_name}_{transaction_type}"
    # logger.debug(f"Fetching mapping and rules for cache key: {cache_key}")  # Log the cache key being used
    cached_data = cache.get(cache_key)
    if cached_data:
        # logger.info(f"Using cached mapping and rules for {bank_name}, {transaction_type}")
        return cached_data

    query = """
        SELECT headers, validation_rules
        FROM upload_bankmapping
        WHERE bank_name = %s AND transaction_type = %s
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [bank_name, transaction_type])
        result = cursor.fetchone()

    if result:
        header_mapping = json.loads(result[0])
        validation_rules = json.loads(result[1])
        cache.set(cache_key, (header_mapping, validation_rules), timeout=CACHE_TIMEOUT)
        # logger.info(f"Saved mapping and rules to cache for {cache_key}")
        return header_mapping, validation_rules

    logger.error(f"No mapping found for bank: {bank_name}, transaction type: {transaction_type}")
    return None, None



def clean_column_name(column_name):
    column_cleaning_regex = re.compile(r'\[.*?\]')
    cleaned_name = column_cleaning_regex.sub('', column_name)
    cleaned_name = ''.join(part for part in cleaned_name.split() if part)
    cleaned_name = ''.join(char for char in cleaned_name if char not in ['.', '_']).strip()
    return cleaned_name


def convert_column_to_datetime(df, column_name):
    df[column_name] = pd.to_datetime(df[column_name], errors='coerce')
    unsuccessful_dates = df[df[column_name].isna()]
    if not unsuccessful_dates.empty:
        logger.warning(f"Could not parse dates in column '{column_name}'; rows affected: {unsuccessful_dates.index.tolist()}")
    return df

def convert_payable_to_float(df, column_name):
    df[column_name] = pd.to_numeric(df[column_name].str.replace(',', ''), errors='coerce')
    return df


def process_dataframe_chunk(df_chunk, header_mapping, validation_rules, bank_name, transaction_type, merchant_name, bank_id):
    logger.info(f"Processing DataFrame chunk for bank: {bank_name}, transaction_type: {transaction_type}")
    # save_log_to_cache(bank_name, transaction_type, 'info', f"Started processing DataFrame chunk for bank: {bank_name}, transaction_type: {transaction_type}")


    # Clean column names
    df_chunk.columns = [clean_column_name(col) for col in df_chunk.columns]

    # Validate required columns and apply mappings
    for column, rules in validation_rules.items():
        if "required" in rules and rules["required"] and column not in df_chunk.columns:
            logger.error(f"Missing required column '{column}' in file for bank: {bank_name}, transaction_type: {transaction_type}")
            return
        if "index" in rules:
            expected_index = rules["index"]
            actual_index = list(df_chunk.columns).index(column) if column in df_chunk.columns else None
            if actual_index != expected_index:
                logger.error(f"Column '{column}' is not at expected index {expected_index}. Found: {actual_index}")
                error_message = f"Column '{column}' is  expected to be at  this index {expected_index}. Found at: {actual_index}"
                save_log_to_cache(bank_name, transaction_type, 'error', error_message)
                return

    # Rename columns based on mapping
    df_chunk.rename(columns=header_mapping, inplace=True)

    # Apply data type conversions
    if 'Transaction_Date' in df_chunk.columns:
        df_chunk = convert_column_to_datetime(df_chunk, 'Transaction_Date')
    if 'Settlement_Date' in df_chunk.columns:
        df_chunk = convert_column_to_datetime(df_chunk, 'Settlement_Date')
    if 'Payable_Merchant' in df_chunk.columns:
        df_chunk = convert_payable_to_float(df_chunk, 'Payable_Merchant')

    # Apply bank-specific logic
    if bank_name == 'ICICI':
        df_chunk['Payable_Merchant'] = df_chunk['Payable_Merchant'].fillna(0)
        df_chunk['Credit_Debit_Amount'] = df_chunk['Payable_Merchant'].apply(
            lambda x: 'CREDIT' if x > 0 else 'DEBIT' if x < 0 else None
        )
        # logger.debug(f"ICICI-specific CREDIT/DEBIT logic applied: {df_chunk[['Payable_Merchant', 'Credit_Debit_Amount']].head()}")

    # Process transactions in the chunk
    process_transactions(df_chunk, bank_name, transaction_type, merchant_name, bank_id)
    save_log_to_cache(bank_name, transaction_type, 'success', f"Successfully processed chunk of size {len(df_chunk)}.")


def process_transactions(df_chunk, bank_name, transaction_type, merchant_name, bank_id):
    logger.info(f"Started processing transactions for bank: {bank_name}, transaction_type: {transaction_type}, merchant_name: {merchant_name}")
    bulk_data_transactions = []
    bank_id = bank_id

    if not bank_id:
        logger.error(f"No bank ID found for bank: {bank_name}")
        return

    for _, row in df_chunk.iterrows():
        transaction_data = {
            'Transaction_type': transaction_type,
            'Merchant_Name': merchant_name,
            'MID': row.get('MID') or bank_id,
            'Transaction_Id': row.get('Transaction_Id'),
            'Order_Id': row.get('Order_Id'),
            'Transaction_Date': row.get('Transaction_Date'),
            'Settlement_Date': row.get('Settlement_Date'),
            'Payable_Merchant': row.get('Payable_Merchant'),
            'Bank_Name': bank_name,
            'Refund_Request_Date': convert_column_to_datetime(df_chunk, 'Refund_Request_Date') if 'Refund_Request_Date' in df_chunk else None,
            'Gross_Amount': convert_payable_to_float(df_chunk, 'Gross_Amount') if 'Gross_Amount' in df_chunk else None,
            'Aggregator_Com': convert_payable_to_float(df_chunk, 'Aggregator_Com') if 'Aggregator_Com' in df_chunk else None,
            'Acquirer_Comm': convert_payable_to_float(df_chunk, 'Acquirer_Comm') if 'Acquirer_Comm' in df_chunk else None,
            'Payout_from_Nodal': convert_payable_to_float(df_chunk, 'Payout_from_Nodal') if 'Payout_from_Nodal' in df_chunk else None,
            'BankName_Receive_Funds': row.get('BankName_Receive_Funds'),
            'Nodal_Account_No': row.get('Nodal_Account_No'),
            'Aggregator_Name': row.get('Aggregator_Name'),
            'Acquirer_Name': row.get('Acquirer_Name'),
            'Refund_Flag': row.get('Refund_Flag'),
            'Payments_Type': row.get('Payments_Type'),
            'MOP_Type': row.get('MOP_Type'),
            'Credit_Debit_Date': convert_column_to_datetime(df_chunk, 'Credit_Debit_Date') if 'Credit_Debit_Date' in df_chunk else None,
            'Refund_Order_Id': row.get('Refund_Order_Id'),
            'Acq_Id': row.get('Acq_Id'),
            'Approve_code': row.get('Approve_code'),
            'Arn_No': row.get('Arn_No'),
            'Card_No': row.get('Card_No'),
            'Tid': row.get('Tid'),
            'Remarks': row.get('Remarks'),
            'Bank_Ref_id': row.get('Bank_Ref_id'),
            'File_upload_Date': timezone.now(),
            'User_name': row.get('User_name'),
            'Recon_Status': row.get('Recon_Status'),
            'Mpr_Summary_Trans': row.get('Mpr_Summary_Trans'),
            'Merchant_code': row.get('Merchant_code'),
            'Rec_Fmt': row.get('Rec_Fmt'),
            'Card_type': row.get('Card_type'),
            'Intl_Amount': convert_payable_to_float(df_chunk, 'Intl_Amount') if 'Intl_Amount' in df_chunk else None,
            'Domestic_Amount': convert_payable_to_float(df_chunk, 'Domestic_Amount') if 'Domestic_Amount' in df_chunk else None,
            'UDF1': None,
            'UDF2': None,
            'UDF3': None,
            'UDF4': None,
            'UDF5': None,
            'UDF6': None,
            'GST_Number': row.get('GST_Number'),
            'Credit_Debit_Amount': row.get('Credit_Debit_Amount')
        }

        bulk_data_transactions.append(transaction_data)

    if bulk_data_transactions:
        try:
            with transaction.atomic():
                Transaction.bulk_create_transactions(bulk_data_transactions)
            logger.info(f"Processed {len(bulk_data_transactions)} transactions successfully.")

        except Exception as e:
            logger.error(f"Failed to save transactions to the database: {e}", exc_info=True)
            error_message = f"Failed to save transactions to the database: {bank_name}, {transaction_type} and {e}"
            save_log_to_cache(bank_name, transaction_type, 'error', error_message)




@shared_task
def process_uploaded_files(file_paths, bank_name, transaction_type, file_formats, merchant_name, bank_id):
    # logger.info(f"Starting file processing for bank: {bank_name}, transaction_type: {transaction_type}")
    save_log_to_cache(bank_name, transaction_type, 'info', f"Starting file processing for bank: {bank_name}, transaction_type: {transaction_type}")

    try:
        header_mapping, validation_rules = fetch_mapping_and_rules(bank_name, transaction_type)
        if not header_mapping or not validation_rules:
            logger.error(f"Cannot proceed without mappings or validation rules for {bank_name}, {transaction_type}")
            error_message = f"Cannot proceed without mappings or validation rules for {bank_name}, {transaction_type}"
            save_log_to_cache(bank_name, transaction_type, 'error', error_message)
            return

        for file_index, file_path in enumerate(file_paths):

            file_name = os.path.basename(file_path)  # Extract the original file name
            logger.info(f"Processing file: {file_name} at {file_path}")
            save_log_to_cache(bank_name, transaction_type, 'info', f"Processing file: {file_name}")


            try:
                # Read the file content
                with open(file_path, 'rb') as file:
                    file_content = file.read()

                file_name = file_path.split(os.sep)[-1]  # Extract file name from the path

                # Process file based on format
                if file_formats[file_index] == 'excel':
                    # Determine the file format by checking the extension
                    if file_name.endswith('.xlsx'):
                        df = pd.read_excel(BytesIO(file_content), dtype=str, engine='openpyxl')
                    elif file_name.endswith('.xls'):
                        df = pd.read_excel(BytesIO(file_content), dtype=str, engine='xlrd')
                    else:
                        raise ValueError(f"Unsupported Excel file format: {file_name}")
                    
                    df_chunks = [df]
                elif file_formats[file_index] == 'csv':
                    df_chunks = pd.read_csv(BytesIO(file_content), dtype=str, chunksize=50000)

                # Process each chunk
                for df_chunk in df_chunks:
                    process_dataframe_chunk(df_chunk, header_mapping, validation_rules, bank_name, transaction_type, merchant_name, bank_id)

            except Exception as e:
                logger.error(f"Error processing file: {file_name}. Exception: {e}", exc_info=True)
                save_log_to_cache(bank_name, transaction_type, 'error', f"Error in processing files: {e}")


            # Optional cleanup: Delete the temporary file after processing
            try:
                os.remove(file_path)
                logger.info(f"Deleted temporary file: {file_path}")
                # save_log_to_cache(bank_name, transaction_type, 'info', f"Deleted processed file: {file_path}")

            except OSError as e:
                logger.warning(f"Failed to delete temp file {file_path}: {e}")


    except Exception as e:
        logger.error(f"Error during file processing. Exception: {e}", exc_info=True)
        raise



#############DB UPLOAD#############################

@shared_task
def upload_transactions_to_db(start_date, end_date, bank, txn_type):
    num_inserted = 0
    model_mapping = {
        'SALE': Rail_Ticket_Sale,
        'REFUND': Rail_Ticket_Refund
        # 'SOFT': Rail_Ticket_Soft,
        # 'IRDS': Rail_Ticket_Irds
    }


    required_length_mapping = {
        'SALE': 17,
        'REFUND': 27,
        'IDRS': 20,  # Example length
        'SOFT': 22,  # Example length
    }



    model = model_mapping.get(txn_type)
    if not model:
        raise ValueError(f"Unsupported transaction type: {txn_type}")
    

    required_length = required_length_mapping.get(txn_type, 17)

   

    try:
        for chunk in get_transaction_data_in_chunks(start_date, end_date, bank, txn_type, chunk_size=50000):
            objects_to_insert = []

            for order in chunk:
                order = list(order)

                # Pad the order to the required length
                while len(order) < required_length:
                    order.append(None)


                # Now 'order' is guaranteed to have 17 elements
                actual_credit_date = order[7]  # No date validation, directly assign

                # If actual_credit_date is not None and is not a valid date, set it to None
                try:
                    if actual_credit_date and datetime.strptime(actual_credit_date, '%d-%b-%Y'):
                        actual_credit_date = datetime.strptime(actual_credit_date, '%d-%b-%Y')
                    else:
                        actual_credit_date = None
                except (ValueError, TypeError):
                    actual_credit_date = None

                ##########################################################################
                actual_refund_date = order[7]

                try:
                    actual_refund_date = datetime.strptime(str(order[7]), '%d-%b-%Y') if order[7] else None
                except (ValueError, TypeError) as e:
                    actual_refund_date = None  # Or log the error for debugging
                    



                if txn_type == 'SALE':
                    rail_ticket = model(
                        Reservation_Id=order[0],
                        Booking_Date=datetime.strptime(order[1], '%d-%b-%Y') if order[1] else None,
                        Bank_Txn_Number=order[2],
                        Sale_Amount=order[3],
                        Bank_id=order[4],
                        Bank_Name=order[5],
                        product_type=order[6],
                        bank_extra_ref=order[7],
                        Entity_Code=order[8],
                        File_upload_Date=timezone.now(),
                        Sale_pg_id=order[10] if len(order) > 10 else None,
                        Actual_Credit_Date=actual_credit_date,
                        Sale_Recon_Status=order[12] if len(order) > 12 else None,
                        Credit_Amount=order[13] if isinstance(order[13], (int, float)) else None,
                        User_name=order[14] if len(order) > 14 else None,
                        Db_Summary_Trans=order[15] if len(order) > 15 else None,
                        Match_Summary_Trans=order[16] if len(order) > 16 else None,
                        mpr_trans_status=order[17] if len(order) > 17 else None,
                    )
                elif txn_type == 'REFUND':
                    rail_ticket = model(
                        Reservation_Id=order[0],
                        Transaction_Date=datetime.strptime(order[1], '%d-%b-%Y') if order[1] else None,
                        Bank_Txn_Id=order[2],
                        Bank_Refund_Txn_Id=order[3],
                        Refund_Amount=order[4],
                        Refund_Status=order[5],
                        Bank_Name=order[6],
                        Actual_Refund_Date=actual_refund_date,
                        Bank_id=order[8],
                        Cancellation_id=order[9],
                        Otp_Flag=order[10] if len(order) > 10 else None,
                        product_type=order[11] if len(order) > 11 else None,
                        bank_extra_ref=order[12] if len(order) > 12 else None,
                        File_upload_Date=timezone.now(),
                        Refund_pg_id=order[14] if len(order) > 14 else None,
                        Actual_Debit_Date=datetime.strptime(order[15], '%d-%b-%Y') if order[15] else None,
                        Refund_Recon_Status=order[16] if len(order) > 16 else None,
                        Reversal_Date1=datetime.strptime(order[17], '%d-%b-%Y') if order[17] else None,
                        Reversal_Date2=datetime.strptime(order[18], '%d-%b-%Y') if order[18] else None,
                        Reversal_Status=order[19] if len(order) > 19 else None,
                        Debit_Amount=order[20] if len(order) > 20 else None,
                        Reversal_Amount=order[21] if len(order) > 21 else None,
                        Reversal1_Amount=order[22] if len(order) > 22 else None,
                        User_name=order[23] if len(order) > 23 else None,
                        Db_Summary_Trans=order[24] if len(order) > 24 else None,
                        Match_Summary_Trans=order[25] if len(order) > 25 else None, 
                        mpr_trans_status=order[26] if len(order) > 26 else None,
                    )
                # Similar logic for 'SOFT' and 'IRDS' transaction types

                objects_to_insert.append(rail_ticket)

            if objects_to_insert:
                model.objects.bulk_create(objects_to_insert)
                num_inserted += len(objects_to_insert)
                logger.info(f"Inserted {num_inserted} records so far.")

    except Exception as e:
        logger.error(f"Error during upload: {e}")
        raise e

    logger.info(f"Task complete: {num_inserted} records inserted.")
    return num_inserted


