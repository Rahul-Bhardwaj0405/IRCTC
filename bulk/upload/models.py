
from django.db import models
from django.contrib.postgres.fields import ArrayField  # Optional if you're using PostgreSQL
import json
import logging

logger = logging.getLogger(__name__)



class BankDetails(models.Model):
    bank_name = models.CharField(max_length=100)
    bank_id = models.CharField(max_length=20, unique=True)  # Make bank_id unique
    mid = models.CharField(max_length=50, unique=True)  # Make mid unique
    merchant_name = models.CharField(max_length=100)

    
    TRANSACTION_TYPES = [
        ('SALE', 'SALE'),
        ('REFUND', 'REFUND'),
        ('NET SETTLED', 'NET SETTLED'),
    ]
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    

    class Meta:
        unique_together = ('bank_id', 'mid')  # Unique together constraint to ensure combination is unique

    def __str__(self):
        return f"{self.bank_name} ({self.bank_id})"





class BankMapping(models.Model):
    bank_id = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=50)
    transaction_type = models.CharField(max_length=50)  # New field for transaction type
    headers = models.JSONField()  # Handles serialization/deserialization automatically
    validation_rules = models.JSONField()  # New field for validation rules
    bank_mapping_rule_name = models.CharField(max_length=50)

    # Ensure a unique combination of bank_name, transaction_type, and headers
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['bank_name', 'transaction_type', 'headers'], name='unique_bank_mapping')
        ]

    def set_headers(self, headers):
        """
        Preprocesses headers to ensure proper JSON structure for mapping.
        Example:
        Input: {"Transaction_Id": "FTNO", "MID": "MID"}
        Output: {"Transaction_Id": "FTNO", "MID": "MID"}
        """
        if isinstance(headers, str):
            headers = json.loads(headers)  # Convert JSON string to Python dictionary
        if not isinstance(headers, dict):
            raise ValueError("Headers must be a dictionary.")
        self.headers = headers

    def get_headers(self):
        """
        Returns headers as a dictionary.
        """
        if isinstance(self.headers, str):
            return json.loads(self.headers)  # Convert back if serialized accidentally
        return self.headers

    def set_validation_rules(self, rules):
        """
        Validates and sets the validation rules field.
        Example:
        {
            "Transaction_Id": {"required": true, "type": "string", "min_length": 10},
            "Gross_Amount": {"required": true, "type": "float", "min_value": 0.0},
            "Transaction_Date": {"required": true, "type": "date", "format": "YYYY-MM-DD"}
        }
        """
        if isinstance(rules, str):
            rules = json.loads(rules)  # Convert JSON string to Python dictionary
        if not isinstance(rules, dict):
            raise ValueError("Validation rules must be a dictionary.")
        self.validation_rules = rules

    def get_validation_rules(self):
        """
        Returns validation rules as a dictionary.
        """
        if isinstance(self.validation_rules, str):
            return json.loads(self.validation_rules)  # Convert back if serialized accidentally
        return self.validation_rules

    def save(self, *args, **kwargs):
        # Ensure headers and validation rules are set properly before saving
        if isinstance(self.headers, dict):  # If headers are passed as a dictionary
            self.set_headers(self.headers)
        if isinstance(self.validation_rules, dict):  # If validation rules are passed as a dictionary
            self.set_validation_rules(self.validation_rules)

      
        # Check for uniqueness constraint
        if BankMapping.objects.filter(
            transaction_type=self.transaction_type,
            headers=self.headers
        ).exclude(pk=self.pk).exists():
            raise ValueError(
                f"Mapping with transaction_type {self.transaction_type} and these headers already exists."
            )

        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.transaction_type}"





class Rail_Ticket_Sale(models.Model):
    Reservation_Id=models.CharField(max_length=50,unique=True)
    Booking_Date=models.DateField()
    Bank_Txn_Number=models.CharField(max_length=50)
    Sale_Amount=models.FloatField(blank=True)
    Bank_id=models.CharField(max_length=10)
    Bank_Name=models.CharField(max_length=25,blank=True)
    Sale_pg_id=models.CharField(max_length=125,blank=True,null=True)
    Actual_Credit_Date=models.DateField(blank=True,null=True)
    Sale_Recon_Status=models.CharField(max_length=25,blank=True,null=True)
    Credit_Amount=models.FloatField(blank=True,null=True)
    File_upload_Date=models.DateTimeField(blank=True,null=True)
    User_name=models.CharField(max_length=25,blank=True,null=True) 
    Db_Summary_Trans=models.CharField(max_length=10,blank=True,null=True) 
    Match_Summary_Trans=models.CharField(max_length=10,blank=True,null=True)  
    product_type=models.CharField(max_length=25,blank=True,null=True) 
    mpr_trans_status=models.CharField(max_length=25,blank=True,null=True)
    bank_extra_ref=models.CharField(max_length=50,blank=True,null=True)
    Entity_Code=models.CharField(max_length=10,blank=True,null=True)
    

    def __str__(self):
        return self.Reservation_Id



class Rail_Ticket_Refund(models.Model):

    Reservation_Id=models.CharField(max_length=50)
    Transaction_Date=models.DateField()
    Bank_Txn_Id=models.CharField(max_length=50,blank=True,null=True)
    Bank_Refund_Txn_Id=models.CharField(max_length=50,blank=True,null=True)
    Refund_Amount=models.FloatField(blank=True)
    Refund_Status=models.CharField(max_length=25,blank=True,null=True)
    Bank_Name=models.CharField(max_length=25,blank=True,null=True)
    Actual_Refund_Date=models.DateField(blank=True,null=True)
    Bank_id=models.CharField(max_length=25,blank=True,null=True)
    Cancellation_id=models.CharField(max_length=25,blank=True,null=True)
    Refund_pg_id=models.CharField(max_length=125,blank=True,null=True)
    Actual_Debit_Date=models.DateField(blank=True,null=True)
    Refund_Recon_Status=models.CharField(max_length=25,blank=True,null=True)
    Otp_Flag=models.CharField(max_length=25,blank=True,null=True)
    Reversal_Date1=models.DateField(blank=True,null=True)
    Reversal_Date2=models.DateField(blank=True,null=True)
    Reversal_Status=models.CharField(max_length=25,blank=True,null=True)
    Debit_Amount=models.FloatField(blank=True,null=True)
    Reversal_Amount=models.FloatField(blank=True,null=True)
    Reversal1_Amount=models.FloatField(blank=True,null=True)
    File_upload_Date=models.DateTimeField(blank=True,null=True)
    User_name=models.CharField(max_length=25,blank=True,null=True) 
    Db_Summary_Trans=models.CharField(max_length=25,blank=True,null=True) 
    Match_Summary_Trans=models.CharField(max_length=25,blank=True,null=True)  
    product_type=models.CharField(max_length=25,blank=True,null=True) 
    mpr_trans_status=models.CharField(max_length=25,blank=True,null=True)
    bank_extra_ref=models.CharField(max_length=50,blank=True,null=True)

    def __str__(self):
        return self.Reservation_Id




class Transaction(models.Model):
    # Fields for transaction data
    Merchant_Name = models.CharField(max_length=50, blank=True, null=True)
    MID = models.CharField(max_length=50, blank=True)
    Transaction_Id = models.CharField(max_length=50, blank=True, null=True)
    Order_Id = models.CharField(max_length=50, blank=True, null=True)
    Transaction_Date = models.DateField(blank=True, null=True)
    Settlement_Date = models.DateField(blank=True, null=True)
    Refund_Request_Date = models.DateField(blank=True, null=True)
    Transaction_type = models.CharField(max_length=50, blank=True)
    Gross_Amount = models.FloatField(blank=True, null=True)
    Aggregator_Com = models.FloatField(blank=True, null=True)
    Acquirer_Comm = models.FloatField(blank=True, null=True)
    Payable_Merchant = models.FloatField(blank=True)
    Payout_from_Nodal = models.FloatField(blank=True, null=True)
    BankName_Receive_Funds = models.CharField(max_length=50, blank=True, null=True)
    Nodal_Account_No = models.CharField(max_length=50, blank=True, null=True)
    Aggregator_Name = models.CharField(max_length=50, blank=True, null=True)
    Acquirer_Name = models.CharField(max_length=50, blank=True, null=True)
    Refund_Flag = models.CharField(max_length=10, blank=True, null=True)
    Payments_Type = models.CharField(max_length=50, blank=True, null=True)
    MOP_Type = models.CharField(max_length=50, blank=True, null=True)
    Credit_Debit_Date = models.DateField(blank=True, null=True)
    Bank_Name = models.CharField(max_length=15, blank=True, null=True)
    Refund_Order_Id = models.CharField(max_length=50, blank=True, null=True)
    Railticketsaler=models.ForeignKey(
       Rail_Ticket_Sale,null=True, on_delete=models.CASCADE,
            related_name='railticketsale')
    Railticketrefund=models.ForeignKey(
        Rail_Ticket_Refund,null=True, on_delete=models.CASCADE,
            related_name='railticketrefund')
    Acq_Id = models.CharField(max_length=125, blank=True, null=True)
    Approve_code = models.CharField(max_length=50, blank=True, null=True)
    Arn_No = models.CharField(max_length=150, blank=True, null=True)
    Card_No = models.CharField(max_length=150, blank=True, null=True)
    Tid = models.CharField(max_length=125, blank=True, null=True)
    Remarks = models.CharField(max_length=50, blank=True, null=True)
    Bank_Ref_id = models.CharField(max_length=125, blank=True, null=True)
    File_upload_Date = models.DateTimeField(blank=True, null=True)
    User_name = models.CharField(max_length=25, blank=True, null=True)
    Recon_Status = models.CharField(max_length=25, blank=True, null=True)
    Mpr_Summary_Trans = models.CharField(max_length=10, blank=True, null=True)
    Merchant_code = models.CharField(max_length=50, blank=True, null=True)
    Rec_Fmt = models.CharField(max_length=50, blank=True, null=True)
    Card_type = models.CharField(max_length=100, blank=True, null=True)
    Intl_Amount = models.FloatField(blank=True, null=True)
    Domestic_Amount = models.FloatField(blank=True, null=True)
    UDF1 = models.CharField(max_length=300, blank=True, null=True)
    UDF2 = models.CharField(max_length=300, blank=True, null=True)
    UDF3 = models.CharField(max_length=300, blank=True, null=True)
    UDF4 = models.CharField(max_length=300, blank=True, null=True)
    UDF5 = models.CharField(max_length=300, blank=True, null=True)
    UDF6 = models.CharField(max_length=300, blank=True, null=True)
    GST_Number = models.CharField(max_length=50, blank=True, null=True)
    Credit_Debit_Amount = models.CharField(max_length=6, blank=True, null=True) 


    class Meta:
        indexes = [
            models.Index(fields=['Order_Id', 'Transaction_Id']), 
            # Retain this index if it's useful for query performance but note it does not enforce uniqueness.
        ]

    def __str__(self):
        return self.Order_Id

    def clean(self):
        # Add your validation logic if needed
        pass

    @classmethod
    def bulk_create_transactions(cls, transactions):
        # Previous duplicate checking and exclusion logic based on Order_Id is removed.
        
        if transactions:
            batch_size = 1000
            try:
                for i in range(0, len(transactions), batch_size):
                    cls.objects.bulk_create(
                        [cls(**transaction) for transaction in transactions[i:i + batch_size]],
                        batch_size=batch_size,
                        ignore_conflicts=True
                    )
            except Exception as ex:
                logger.error(f"Error during bulk create: {str(ex)}")
                raise

        return len(transactions)





# from django.db import models, transaction
# import logging

# logger = logging.getLogger(__name__)

# class Transaction(models.Model):
#     # New fields replacing the common and specific fields
#     Merchant_Name = models.CharField(max_length=50, blank=True, null=True)
#     MID = models.CharField(max_length=50, blank=True)
#     Transaction_Id = models.CharField(max_length=50, blank=True, null=True)
#     Order_Id = models.CharField(max_length=50, blank=True, null=True)
#     Transaction_Date = models.DateField(blank=True, null=True)
#     Settlement_Date = models.DateField()
#     Refund_Request_Date = models.DateField(blank=True, null=True)
#     Transaction_type = models.CharField(max_length=50, blank=True)
#     Gross_Amount = models.FloatField(blank=True, null=True)
#     Aggregator_Com = models.FloatField(blank=True, null=True)
#     Acquirer_Comm = models.FloatField(blank=True, null=True)
#     Payable_Merchant = models.FloatField(blank=True)
#     Payout_from_Nodal = models.FloatField(blank=True, null=True)
#     BankName_Receive_Funds = models.CharField(max_length=50, blank=True, null=True)
#     Nodal_Account_No = models.CharField(max_length=50, blank=True, null=True)
#     Aggregator_Name = models.CharField(max_length=50, blank=True, null=True)
#     Acquirer_Name = models.CharField(max_length=50, blank=True, null=True)
#     Refund_Flag = models.CharField(max_length=10, blank=True, null=True)
#     Payments_Type = models.CharField(max_length=50, blank=True, null=True)
#     MOP_Type = models.CharField(max_length=50, blank=True, null=True)
#     Credit_Debit_Date = models.DateField(blank=True, null=True)
#     Bank_Name = models.CharField(max_length=15, blank=True, null=True)
#     Refund_Order_Id = models.CharField(max_length=50, blank=True, null=True) #cancellation id
#     Acq_Id = models.CharField(max_length=125, blank=True, null=True)
#     Approve_code = models.CharField(max_length=50, blank=True, null=True)
#     Arn_No = models.CharField(max_length=150, blank=True, null=True)
#     Card_No = models.CharField(max_length=150, blank=True, null=True)
#     Tid = models.CharField(max_length=125, blank=True, null=True)
#     Remarks = models.CharField(max_length=50, blank=True, null=True)
#     Bank_Ref_id = models.CharField(max_length=125, blank=True, null=True) #Extra data given by some banks
#     File_upload_Date = models.DateTimeField(blank=True, null=True)
#     User_name = models.CharField(max_length=25, blank=True, null=True)
#     Recon_Status = models.CharField(max_length=25, blank=True, null=True)
#     Mpr_Summary_Trans = models.CharField(max_length=10, blank=True, null=True)
#     Merchant_code = models.CharField(max_length=50, blank=True, null=True)
#     Rec_Fmt = models.CharField(max_length=50, blank=True, null=True)
#     Card_type = models.CharField(max_length=100, blank=True, null=True)
#     Intl_Amount = models.FloatField(blank=True, null=True)
#     Domestic_Amount = models.FloatField(blank=True, null=True)
#     UDF1 = models.CharField(max_length=300, blank=True, null=True)
#     UDF2= models.CharField(max_length=300, blank=True, null=True)
#     UDF3 = models.CharField(max_length=300, blank=True, null=True)
#     UDF4 = models.CharField(max_length=300, blank=True, null=True)
#     UDF5 = models.CharField(max_length=300, blank=True, null=True)
#     UDF6 = models.CharField(max_length=300, blank=True, null=True)
#     GST_Number = models.CharField(max_length=50, blank=True, null=True)
#     Credit_Debit_Amount = models.CharField(max_length=6, blank=True, null=True)  # Adjust max_length if needed


#     class Meta:
#         indexes = [
#             models.Index(fields=['Order_Id', 'Transaction_Id']),
#         ]

#     def __str__(self):
#         return self.Order_Id

#     def clean(self):
#         # Add your validation logic if needed
#         pass

#     @classmethod
#     def bulk_create_transactions(cls, transactions):
#         existing_orders = set(cls.objects.filter(
#             Order_Id__in={tx['Order_Id'] for tx in transactions if 'Order_Id' in tx}
#         ).values_list('Order_Id', flat=True))

#         new_transactions = [tx for tx in transactions if tx.get('Order_Id') not in existing_orders]

#         if new_transactions:
#             batch_size = 500
#             for i in range(0, len(new_transactions), batch_size):
#                 try:
#                     # bulk_create without transaction.atomic()
#                     cls.objects.bulk_create(
#                         [cls(**transaction) for transaction in new_transactions[i:i + batch_size]],
#                         batch_size=batch_size,
#                         ignore_conflicts=True
#                     )
#                 except Exception as ex:
#                     logger.error(f"Error during bulk create: {str(ex)}")
#                     raise

#             return len(new_transactions)
#         return 0

