// <!-- Updated JavaScript -->

    let lockedMappings = []; // Store locked mappings

    function lockMapping() {
        const fileColumn = document.getElementById('file_column').value;
        const mprColumn = document.getElementById('mpr_column').value;
        const validationRules = document.getElementById('validation_rules').value;

        if (!fileColumn || !mprColumn) {
            alert("Both File Column and MPR Column must be selected.");
            return;
        }

        try {
            // Ensure validation rules are valid JSON
            const parsedRules = validationRules ? JSON.parse(validationRules) : {};

            // Avoid duplicates
            lockedMappings = lockedMappings.filter(mapping => mapping.fileColumn !== fileColumn);

            // Add the new mapping
            lockedMappings.push({
                fileColumn,  // File-specific column name
                mprColumn,   // Standardized column name
                validationRules: parsedRules  // Validation rules
            });

            updateLockedMappingsTable();
        } catch (error) {
            alert("Invalid JSON format for validation rules.");
        }
    }



    function updateLockedMappingsTable() {
            const tableBody = document.getElementById('lockedMappingsTable').querySelector('tbody');
            tableBody.innerHTML = '';

            lockedMappings.forEach((mapping, index) => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${index + 1}</td>
                    <td>${mapping.fileColumn}</td>  <!-- File column name -->
                    <td>${mapping.mprColumn}</td>  <!-- Standardized column name -->
                    <td><pre>${JSON.stringify(mapping.validationRules, null, 2)}</pre></td>
                    <td>
                        <button class="btn btn-danger btn-sm" onclick="deleteMapping(${index})">Delete</button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        }



    function deleteMapping(index) {
        lockedMappings.splice(index, 1);
        updateLockedMappingsTable();
    }

    function showPreviewModal() {
        const previewList = document.getElementById('previewMappingList');
        previewList.innerHTML = '';

        lockedMappings.forEach((mapping, index) => {
            const listItem = document.createElement('li');
            listItem.classList.add('list-group-item');
            listItem.innerHTML = `
                <strong>File Column:</strong> ${mapping.fileColumn}, 
                <strong>MPR Column:</strong> ${mapping.mprColumn}
                <button class="btn btn-warning btn-sm float-end" onclick="editMapping(${index})">Edit</button>
            `;
            previewList.appendChild(listItem);
        });

        const modal = new bootstrap.Modal(document.getElementById('previewModal'));
        modal.show();
    }

    function editMapping(index) {
        const mapping = lockedMappings[index];
        document.getElementById('file_column').value = mapping.fileColumn;
        document.getElementById('mpr_column').value = mapping.mprColumn;
        deleteMapping(index);
        const modal = bootstrap.Modal.getInstance(document.getElementById('previewModal'));
        modal.hide();
    }
    
    function saveMappings() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const bankId = document.getElementById('bank_id').value;
        const bankName = document.getElementById('bank_name').selectedOptions[0]?.text || '';
        const transactionType = document.getElementById('transaction_type').value;  // Get transaction type

        // Log lockedMappings to ensure validation_rules are included
        console.log({
            mappings: lockedMappings,
            bank_id: bankId,
            bank_name: bankName,
            transaction_type: transactionType  // Include transaction type
        });

        fetch('/save-mappings/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({
                mappings: lockedMappings,
                bank_id: bankId,
                bank_name: bankName,
                transaction_type: transactionType  // Send transaction type to the backend
            }),
        }).then(response => {
            if (response.ok) {
                alert('Mappings saved successfully!');
                window.location.href = '/bank_details_list/';  // Redirect after successful save

            } else {
                response.json().then(data => alert(data.error || 'Failed to save mappings.'));
            }
        }).catch(error => {
            console.error('Error:', error);
            alert('An error occurred while saving mappings.');
        });
    }

