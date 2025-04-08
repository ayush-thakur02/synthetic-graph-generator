$(document).ready(function() {
    // Store generated charts
    let generatedCharts = [];

    // Update error probability display
    $('#error_probability').on('input', function() {
        $('#error_probability_value').text($(this).val());
    });
    
    // Toggle custom names section based on naming type
    $('#naming_type').on('change', function() {
        const namingType = $(this).val();
        if (namingType === 'custom') {
            $('#customNamesSection').slideDown(300);
        } else {
            $('#customNamesSection').slideUp(300);
        }
    });

    // Handle form submission with loading indicator
    $('#generateForm').on('submit', function(e) {
        e.preventDefault();
        
        // Get form data
        const formData = new FormData(this);
        formData.set('include_grid', $('#include_grid').is(':checked').toString());
        
        // Show loading indicator
        const loadingHtml = `
            <div class="col-12 text-center py-5" id="loading-indicator">
                <div class="spinner-border text-primary" role="status">
                    <span class="sr-only">Loading...</span>
                </div>
                <p class="mt-2">Generating chart...</p>
            </div>
        `;
        if ($('#generatedCharts').children().length === 0) {
            $('#generatedCharts').html(loadingHtml);
        } else {
            $('#generatedCharts').prepend(loadingHtml);
        }
        
        // Send API request
        $.ajax({
            url: '/generate',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                // Remove loading indicator
                $('#loading-indicator').remove();
                
                // Add to generated charts
                const chartId = 'chart-' + Date.now();
                generatedCharts.unshift({
                    id: chartId,
                    image: response.image,
                    data: response.data
                });
                
                // Add to the UI with animation at the beginning of the container
                const chartHtml = `
                    <div class="col-md-6 generated-chart-container" id="${chartId}" style="opacity: 0;">
                        <div class="card">
                            <div class="card-body p-0">
                                <img src="${response.image}" alt="Generated Chart" class="img-fluid">
                                <div class="chart-actions">
                                    <button class="btn btn-sm btn-danger remove-chart" data-id="${chartId}">
                                        <i class="fas fa-trash-alt"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                $('#generatedCharts').prepend(chartHtml);
                $(`#${chartId}`).animate({opacity: 1}, 300);
                
                // Enable download button
                $('#downloadBtn').prop('disabled', false);
                
                // Scroll to the top of the charts section
                $('html, body').animate({
                    scrollTop: $('#generatedCharts').offset().top - 20
                }, 500);
            },
            error: function() {
                // Remove loading indicator
                $('#loading-indicator').remove();
                
                // Show error message
                const errorHtml = `
                    <div class="col-12 text-center py-3 alert alert-danger">
                        <i class="fas fa-exclamation-circle mr-2"></i>
                        Error generating chart. Please try again.
                    </div>
                `;
                $('#generatedCharts').prepend(errorHtml);
                
                // Auto-remove the error message after 5 seconds
                setTimeout(function() {
                    $('.alert-danger').fadeOut(300, function() {
                        $(this).remove();
                    });
                }, 5000);
            }
        });
    });
    
    // Fix for batch generate button - completely rewritten approach
    $('#batchGenerateBtn').on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        // Use Bootstrap's native events to properly handle modal effects
        $('#batchModal').off('shown.bs.modal').off('show.bs.modal');
        
        // Prevent any hover/animation interactions while modal is visible
        $('#batchModal').on('show.bs.modal', function() {
            // Add a class to the body that we'll use to prevent animations
            $('body').addClass('modal-open-no-animations');
        });
        
        // Clean up when modal is closed
        $('#batchModal').on('hidden.bs.modal', function() {
            $('body').removeClass('modal-open-no-animations');
        });
        
        // Show the modal with reduced motion options
        $('#batchModal').modal({
            backdrop: 'static',
            keyboard: false
        });
    });
    
    // Fix the start batch generation handler
    $('#startBatchBtn').on('click', function(e) {
        e.preventDefault();
        
        // Store form data before hiding modal to avoid any state issues
        const baseFormData = new FormData($('#generateForm')[0]);
        baseFormData.set('include_grid', $('#include_grid').is(':checked').toString());
        
        // Get batch parameters before closing modal
        const batchParams = {
            min_categories: $('#min_categories').val(),
            max_categories: $('#max_categories').val(),
            min_subcategories: $('#min_subcategories').val(),
            max_subcategories: $('#max_subcategories').val(),
            count: $('#count').val()
        };
        
        // Hide modal first before any heavy processing
        $('#batchModal').modal('hide');
        
        setTimeout(function() {
            // Create batch request data
            const batchFormData = new FormData();
            batchFormData.append('params', JSON.stringify(Object.fromEntries(baseFormData.entries())));
            batchFormData.append('count', batchParams.count);
            
            // Add other batch params
            batchFormData.append('min_categories', batchParams.min_categories);
            batchFormData.append('max_categories', batchParams.max_categories);
            batchFormData.append('min_subcategories', batchParams.min_subcategories);
            batchFormData.append('max_subcategories', batchParams.max_subcategories);
            
            // Show loading indicator
            const loadingHtml = `
                <div class="col-12 text-center py-5" id="batch-loading-indicator">
                    <div class="spinner-border text-primary" role="status">
                        <span class="sr-only">Loading...</span>
                    </div>
                    <p class="mt-2">Generating ${$('#count').val()} charts...</p>
                </div>
            `;
            if ($('#generatedCharts').children().length === 0) {
                $('#generatedCharts').html(loadingHtml);
            } else {
                $('#generatedCharts').prepend(loadingHtml);
            }
            
            // Send API request
            $.ajax({
                url: '/batch_generate',
                type: 'POST',
                data: batchFormData,
                processData: false,
                contentType: false,
                success: function(response) {
                    // Remove loading indicator
                    $('#batch-loading-indicator').remove();
                    
                    if (response.length === 0) {
                        // Show message if no charts were generated
                        const noChartsHtml = `
                            <div class="col-12 text-center py-3 alert alert-warning">
                                <i class="fas fa-exclamation-triangle mr-2"></i>
                                No charts were generated
                            </div>
                        `;
                        $('#generatedCharts').prepend(noChartsHtml);
                        return;
                    }
                    
                    // Create a temporary container for batch charts
                    const batchContainer = $('<div>');
                    
                    // Add all charts to the generated list with staggered animation
                    response.forEach(function(chart, index) {
                        const chartId = 'chart-' + Date.now() + Math.floor(Math.random() * 1000);
                        
                        // Add to beginning of generatedCharts array
                        generatedCharts.unshift({
                            id: chartId,
                            image: chart.image,
                            data: chart.data,
                            params: chart.params
                        });
                        
                        const chartHtml = `
                            <div class="col-md-6 generated-chart-container" id="${chartId}" style="opacity: 0;">
                                <div class="card">
                                    <div class="card-body p-0">
                                        <img src="${chart.image}" alt="Generated Chart" class="img-fluid">
                                        <div class="chart-actions">
                                            <button class="btn btn-sm btn-danger remove-chart" data-id="${chartId}">
                                                <i class="fas fa-trash-alt"></i>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `;
                        batchContainer.prepend(chartHtml);
                    });
                    
                    // Prepend all charts at once to minimize DOM operations
                    $('#generatedCharts').prepend(batchContainer.children());
                    
                    // Animate them with a staggered delay
                    $('.generated-chart-container[style*="opacity: 0"]').each(function(index) {
                        const $this = $(this);
                        setTimeout(function() {
                            $this.animate({opacity: 1}, 300);
                        }, index * 100);
                    });
                    
                    // Enable download button
                    $('#downloadBtn').prop('disabled', false);
                    
                    // Scroll to the top of the charts section
                    $('html, body').animate({
                        scrollTop: $('#generatedCharts').offset().top - 20
                    }, 500);
                    
                    // Show success toast
                    const successHtml = `
                        <div class="position-fixed bottom-0 right-0 p-3" style="z-index: 5; right: 0; bottom: 0;">
                            <div class="toast bg-success text-white" role="alert" aria-live="assertive" aria-atomic="true" data-delay="3000">
                                <div class="toast-body">
                                    <i class="fas fa-check-circle mr-2"></i>
                                    Successfully generated ${response.length} charts
                                </div>
                            </div>
                        </div>
                    `;
                    $('body').append(successHtml);
                    $('.toast').toast('show');
                    setTimeout(function() {
                        $('.toast').remove();
                    }, 3500);
                },
                error: function() {
                    // Remove loading indicator
                    $('#batch-loading-indicator').remove();
                    
                    // Show error message
                    const errorHtml = `
                        <div class="col-12 text-center py-3 alert alert-danger">
                            <i class="fas fa-exclamation-circle mr-2"></i>
                            Error generating batch of charts
                        </div>
                    `;
                    $('#generatedCharts').prepend(errorHtml);
                }
            });
        }, 300); // Small delay to ensure modal is closed properly
    });
    
    // Remove chart button click (using event delegation)
    $('#generatedCharts').on('click', '.remove-chart', function() {
        const chartId = $(this).data('id');
        
        // Remove from UI with animation
        $(`#${chartId}`).fadeOut(300, function() {
            $(this).remove();
            
            // Remove from array
            generatedCharts = generatedCharts.filter(chart => chart.id !== chartId);
            
            // Disable download button if no charts left
            if (generatedCharts.length === 0) {
                $('#downloadBtn').prop('disabled', true);
            }
        });
    });
    
    // Download all charts
    $('#downloadBtn').on('click', function() {
        if (generatedCharts.length === 0) {
            return;
        }
        
        // Change button to loading state
        const originalBtnHtml = $('#downloadBtn').html();
        $('#downloadBtn').html('<i class="fas fa-spinner fa-spin mr-1"></i> Processing...').prop('disabled', true);
        
        // Prepare data for download
        const downloadData = {
            images: generatedCharts.map(chart => ({
                image: chart.image,
                data: chart.data,
                params: chart.params || {}
            }))
        };
        
        // Send download request
        $.ajax({
            url: '/download',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(downloadData),
            success: function(response) {
                // Reset button
                $('#downloadBtn').html(originalBtnHtml).prop('disabled', false);
                
                if (response.status === 'success') {
                    // Create a custom modal to show success and links
                    const modalHtml = `
                        <div class="modal fade" id="downloadSuccessModal" tabindex="-1" role="dialog" aria-hidden="true">
                            <div class="modal-dialog" role="document">
                                <div class="modal-content">
                                    <div class="modal-header bg-success text-white">
                                        <h5 class="modal-title">
                                            <i class="fas fa-check-circle mr-2"></i>Download Successful
                                        </h5>
                                        <button type="button" class="close text-white" data-dismiss="modal" aria-label="Close">
                                            <span aria-hidden="true">&times;</span>
                                        </button>
                                    </div>
                                    <div class="modal-body">
                                        <p>Successfully saved ${response.image_count} images.</p>
                                        <div class="list-group mt-3">
                                            ${response.batch_json_url ? 
                                                `<a href="${response.batch_json_url}" class="list-group-item list-group-item-action" target="_blank">
                                                    <i class="fas fa-file-code mr-2"></i> Download Batch JSON
                                                </a>` : ''}
                                            ${response.master_json_url ? 
                                                `<a href="${response.master_json_url}" class="list-group-item list-group-item-action" target="_blank">
                                                    <i class="fas fa-file-alt mr-2"></i> Download Master JSON
                                                </a>` : ''}
                                        </div>
                                    </div>
                                    <div class="modal-footer">
                                        <button type="button" class="btn btn-success" data-dismiss="modal" id="refreshPageBtn">
                                            <i class="fas fa-sync-alt mr-1"></i> Refresh Page
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                    
                    $('body').append(modalHtml);
                    $('#downloadSuccessModal').modal('show');
                    $('#refreshPageBtn').on('click', function() {
                        window.location.reload();
                    });
                    
                } else if (response.status === 'partial_success') {
                    alert(`Partial success: ${response.message}`);
                    window.location.reload();
                } else {
                    alert(`Error: ${response.message || 'Unknown error'}`);
                    window.location.reload();
                }
            },
            error: function(xhr) {
                // Reset button
                $('#downloadBtn').html(originalBtnHtml).prop('disabled', false);
                
                let errorMsg = 'Error downloading charts';
                try {
                    const response = JSON.parse(xhr.responseText);
                    if (response.message) {
                        errorMsg = response.message;
                    }
                } catch (e) {}
                alert(errorMsg);
                window.location.reload();
            }
        });
    });
    
    // Add tooltip initializations
    $(function () {
        $('[data-toggle="tooltip"]').tooltip();
    });
});
