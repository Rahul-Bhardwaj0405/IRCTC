

function submitFormAndRedirect(event) {
    event.preventDefault(); // Prevent default behavior of the anchor link

    // Parse the valid combinations of bank details
    const validDetails = JSON.parse(document.getElementById('valid-bank-details').textContent);

    // Get selected input values from the form
    const selectedBankName = document.getElementById('id_bank_name').value.trim();
    const selectedBankId = document.getElementById('id_bank_id').value.trim();
    const selectedMerchantName = document.getElementById('id_merchant_name').value.trim();
    const selectedTransactionType = document.getElementById('id_transaction_type').value.trim();

    // Validate the selected combination
    const isValid = validDetails.some(detail =>
        detail.bank_name === selectedBankName &&
        detail.bank_id === selectedBankId &&
        detail.merchant_name === selectedMerchantName
    );

    // If validation fails, show an alert and stop further execution
    if (!isValid) {
        alert("Invalid combination of Bank Name, Bank ID, and Merchant Name. Please check your inputs.");
        return; // Stop form submission or redirection
    }

    // If the validation is successful, submit the form programmatically
    const form = document.getElementById('upload-form');
    const formData = new FormData(form);

    // Submit the form data using AJAX
    fetch(form.action, {
        method: 'POST',
        body: formData,
    })
    .then(response => {
        if (response.ok) {
            // On success, dynamically redirect to the logs page
            const bankName = selectedBankName;
            const transactionType = selectedTransactionType;

            // Redirect to the dynamic logs page
            window.location.href = `/logs/${bankName}/${transactionType}/?disable=true`;
        } else {
            // If the form submission fails, show an error message
            alert("Form submission failed. Check your inputs and try again.");
        }
    })
    .catch(error => {
        console.error("Error during form submission:", error);
        alert("An error occurred while processing your request.");
    });
}

// Diable all button and input lable after redirection

document.addEventListener("DOMContentLoaded", function() {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('disable') === 'true') {
        // Disable all input fields and buttons inside the card-body
        const cardBody = document.querySelector('.card-body');
        if (cardBody) {
            const elements = cardBody.querySelectorAll('input, button, select, a');
            elements.forEach(element => {
                element.disabled = true; // Disable the element
                element.classList.add('disabled'); // Optional for UI feedback
            });
        }
    }
});