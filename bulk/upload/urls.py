from django.urls import path
from .views import  upload_files, transaction_results_view, nget_db_upload,  Mpractual_Credit_Date, add_bank_details, bank_details_list, save_mappings, show_logs

urlpatterns = [

# --------------------ADD BANKS MAPPING-------------------------------------------------

    path('add_bank_details/', add_bank_details, name='add_bank_details'),
    path('bank_details_list/', bank_details_list, name='bank_details_list'),
    path('save-mappings/', save_mappings, name='save_mappings'),

# -------------------------LOGS---------------------------------------------------------

    path('logs/<str:bank_name>/<str:transaction_type>/', show_logs, name='show_logs'),
    



#  ----------Upload MPR ---------------------------------------------------------------
    path('mpr_upload/', upload_files, name='upload'),
    path('transaction-results/', transaction_results_view, name='transaction_results'),


    
# -------------NGET DB RECORD --------------------------------------------
   
    path('dbupload/', nget_db_upload, name='dbupload'), 
   
#--------------MERCHANT URL ------------------------------
    path('mprcredit/',  Mpractual_Credit_Date, name='mprcredit')


]